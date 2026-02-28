# Architecture

## Overview

SCR Platform is a multi-tenant SaaS application built as a monorepo. The system separates user-facing features (Next.js), business logic (FastAPI), and AI inference (AI Gateway) into three independently deployable services, backed by PostgreSQL, Redis, ElasticSearch, and S3.

```
Browser
  │
  ▼
┌─────────────────────────────┐
│   Next.js 14 (App Router)   │  apps/web/
│   TypeScript · Tailwind     │  Port 3000
└────────────┬────────────────┘
             │ REST + SSE (Axios / fetch)
             ▼
┌─────────────────────────────┐
│   FastAPI (Python 3.12)     │  apps/api/
│   SQLAlchemy 2.0 async      │  Port 8000
│   25+ feature modules       │
└──────┬──────────┬───────────┘
       │          │ Internal service call
       │          ▼
       │  ┌──────────────────────┐
       │  │   AI Gateway         │  services/ai-gateway/
       │  │   litellm router     │  Port 8001
       │  │   RAG + rate limit   │
       │  └──────────────────────┘
       │          │ LLM API calls
       │          ▼
       │  ┌──────────────────────────────────────┐
       │  │  Anthropic (Claude Sonnet 4)          │
       │  │  OpenAI (GPT-4o vision fallback)      │
       │  └──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│  PostgreSQL 16  │  Redis 7  │  ElasticSearch  │
│  S3 / MinIO     │           │                 │
└──────────────────────────────────────────────┘
```

---

## Service Boundaries

### Frontend — `apps/web/`

- **Next.js 14 App Router** with full TypeScript strict mode
- **React Query** for all server state — automatic caching, background refetch, optimistic updates
- **Zustand** for client-only UI state (sidebar open, Ralph panel, active filters)
- Clerk's `<ClerkProvider>` wraps the root; auth tokens injected into every Axios request via an interceptor
- All API calls go through `apps/web/src/lib/api.ts` (Axios instance pointing at `NEXT_PUBLIC_API_URL`)
- SSE streaming (Ralph AI) uses `fetch` + `ReadableStream` rather than `EventSource` (required for POST with auth header)

### API — `apps/api/`

- **FastAPI** with async `uvicorn` (4 workers in production)
- **SQLAlchemy 2.0** async ORM — `AsyncSession` via `get_db()` dependency injection
- Every request passes through the middleware stack (see [Security](security.md))
- Each feature is a self-contained module: `router.py`, `service.py`, `schemas.py`, optional `tasks.py`
- Background tasks via **Celery** + Redis broker for long-running operations (score calculation, report generation)
- Database migrations via **Alembic** (synchronous connection, run as one-off ECS task in CI/CD)

### AI Gateway — `services/ai-gateway/`

- Thin FastAPI proxy authenticated with a shared `AI_GATEWAY_API_KEY`
- Routes each task type to the correct LLM via **litellm** (model-agnostic)
- **Rate limits** enforced per organisation tier (Redis sliding window)
- **Vector store** for RAG (configurable: Pinecone in production, in-memory locally)
- External data feeds: FRED (macroeconomics), World Bank, NOAA (climate), Regulations.gov

---

## Multi-Tenancy

Every database row owned by an organisation carries an `org_id` column. The `TenantMiddleware` sets `request.state.org_id` from the verified JWT, and the `tenant_filter()` helper adds `.where(Model.org_id == request.state.org_id)` to every query.

```python
# Pattern used throughout service layer
stmt = select(Project).where(
    tenant_filter(Project, request.state.org_id),
    Project.is_deleted.is_(False),
)
```

The middleware is **outermost** in the stack — it runs before route handlers and audit logging.

---

## Data Model

### Core Entities

```
Organization (org_id)
  ├── User (user_id, org_id)
  ├── Project (org_id)           ← Ally-owned
  │   ├── Milestone
  │   ├── BudgetItem
  │   └── SignalScore
  ├── Portfolio (org_id)         ← Investor-owned
  │   ├── Fund
  │   └── Holding → Project
  ├── AIConversation (org_id, user_id)
  │   └── AIMessage
  └── AuditLog (org_id)         ← Immutable
```

### Organisation Types

| Type | Description |
|------|-------------|
| `ALLY` | Impact project developers — create and manage projects |
| `INVESTOR` | Investment funds — manage portfolios, match with projects |
| `ADMIN` | SCR platform administrators — cross-org visibility |

### Subscription Tiers

| Tier | AI Rate Limit | Description |
|------|--------------|-------------|
| `foundation` | 100 req/hr, 500K tokens/day | Early access |
| `professional` | 500 req/hr, 2M tokens/day | Full access |
| `enterprise` | 2000 req/hr, 10M tokens/day | Unlimited support |

---

## Authentication Flow

```
1. User signs in via Clerk (browser)
2. Clerk issues RS256 JWT (sub = clerk_user_id)
3. Frontend stores token, sends as Authorization: Bearer <token>
4. FastAPI get_current_user() dependency:
   a. Fetches JWKS from Clerk (cached 1 hour)
   b. Verifies RS256 signature + expiry + issuer
   c. Looks up User by external_auth_id = jwt.sub
   d. Returns CurrentUser(user_id, org_id, role, email)
5. require_role() / require_permission() restrict specific endpoints
```

Clerk also sends webhook events (user.created/updated/deleted) to `/auth/webhooks` — verified with Svix HMAC to keep the SCR User table in sync.

---

## Request Lifecycle

```
Request
  ↓
SecurityHeadersMiddleware   — adds security headers to response
  ↓
RateLimitMiddleware         — Redis sliding window, IP-based (300/min default)
  ↓
RequestBodySizeLimitMiddleware — rejects bodies > 50 MB with 413
  ↓
TenantMiddleware            — initialises request.state.org_id / user_id
  ↓
AuditMiddleware             — registers post-response hook for writes
  ↓
CORSMiddleware              — enforces origin + method allowlist
  ↓
Route handler
  ├── get_current_user()    — Clerk JWT validation
  ├── require_role()        — RBAC enforcement
  ├── get_db()              — AsyncSession injection
  └── business logic
  ↓
Response
  ↓
AuditMiddleware             — writes AuditLog row (fire-and-forget task)
  ↓
SecurityHeadersMiddleware   — appends X-Content-Type-Options, X-Frame-Options, etc.
```

---

## AI Architecture

### Ralph AI (Conversational Agent)

Ralph is a tool-using agent backed by `claude-sonnet-4-20250514`. It runs an agentic loop with up to 10 iterations per message:

```
User message
  ↓
Build context (conversation history + RAG retrieval)
  ↓
Loop:
  POST /v1/completions (AI Gateway, with tools)
  ├── stop_reason = "tool_use"
  │   ├── Execute tool (direct DB query or service call)
  │   └── Append tool_result → continue loop
  └── stop_reason = "end_turn"
      ↓
      Store user + assistant messages
      ↓
Return response (or stream tokens via SSE)
```

### AI Gateway Routing

Each task type maps to a specific model and token budget:

| Task category | Model | Max tokens |
|--------------|-------|-----------|
| `chat_with_tools` (Ralph) | claude-sonnet-4 | 8192 |
| `document_analysis` | claude-sonnet-4 | 4096 |
| `financial_analysis` | claude-sonnet-4 | 4096 |
| `vision` tasks | gpt-4o | 4096 |
| `embeddings` | text-embedding-3-large | — |
| `budget` tasks | claude-haiku-4 | 2048 |

---

## Caching Strategy

| Layer | Mechanism | TTL |
|-------|-----------|-----|
| Clerk JWKS | In-process dict | 3600s |
| AI completions | Redis (input hash key) | Task-specific |
| Rate limit windows | Redis sorted set | window + 1s |
| React Query | In-memory (browser) | 5 min stale, 10 min GC |

---

## Background Jobs (Celery)

Long-running operations are dispatched as Celery tasks to avoid blocking HTTP requests:

| Task | Trigger | Queue |
|------|---------|-------|
| Signal score calculation | User action | `scoring` |
| Report generation | User action | `reporting` |
| Document text extraction | File upload | `documents` |
| AI task execution | Various endpoints | `ai` |
| Notification dispatch | Events | `notifications` |

---

## File Storage

Documents are stored in S3 (MinIO locally). The API generates pre-signed URLs for direct browser download — the file content never passes through the API server.

```
Upload:   Client → API (metadata) → API returns pre-signed PUT URL → Client → S3
Download: Client → API (auth) → API returns pre-signed GET URL → Client → S3
```

---

## Design Decisions

### Deterministic Financial Calculations

Valuations, equity scenarios, tax credit calculations, and capital efficiency metrics are computed using pure Python arithmetic (`numpy-financial`, `decimal`). LLMs are only used for narrative text generation and document analysis — never for numbers that investors rely on.

### Event Sourcing for Audit

`AuditLog` is append-only with no `updated_at` and no soft delete. Every write operation (POST/PUT/PATCH/DELETE returning 2xx) triggers a fire-and-forget task that writes to `audit_logs` using a dedicated DB session separate from the request session. This prevents audit log failures from rolling back business transactions.

### Sync vs Async DB Connections

SQLAlchemy uses two connection strings: `DATABASE_URL` (asyncpg, for all application queries) and `DATABASE_URL_SYNC` (psycopg2, for Alembic migrations only — Alembic does not support async). The two strings point to the same database.
