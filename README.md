# SCR Platform

> Investment intelligence platform connecting impact project developers (**Allies**) with professional investors (**Investors**).

SCR Platform is a full-stack SaaS application with 25+ AI-powered modules covering deal origination, due diligence, portfolio management, risk analysis, compliance, and conversational AI.

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Architecture](docs/architecture.md) | System design, data flows, design decisions |
| [Development Guide](docs/development.md) | Local setup, coding standards, testing |
| [API Reference](docs/api-reference.md) | All 29 API modules with endpoints |
| [Modules](docs/modules.md) | Feature-by-feature breakdown |
| [Ralph AI](docs/ralph-ai.md) | Conversational AI agent architecture |
| [Security](docs/security.md) | Auth, RBAC, rate limiting, headers |
| [Deployment](docs/deployment.md) | CI/CD pipeline, AWS infrastructure |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, React Query, Zustand |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Celery |
| Database | PostgreSQL 16, Redis 7, ElasticSearch 8 |
| AI | Claude Sonnet 4 (primary), GPT-4o (vision), litellm unified routing |
| Storage | AWS S3 (MinIO locally) |
| Auth | Clerk (JWKS RS256) |
| Monorepo | Turborepo, pnpm workspaces |
| Infrastructure | AWS ECS Fargate, RDS, ElastiCache, ECR via Terraform |

---

## Repository Structure

```
scr-platform/
├── apps/
│   ├── web/                     # Next.js 14 frontend (App Router)
│   │   └── src/
│   │       ├── app/(dashboard)/ # 25+ feature pages
│   │       ├── components/      # Shared UI components
│   │       └── lib/             # API hooks, stores, utils
│   └── api/                     # FastAPI backend
│       └── app/
│           ├── modules/         # 25+ feature modules
│           ├── models/          # SQLAlchemy models + enums
│           ├── middleware/      # Security, audit, tenant, rate-limit
│           └── auth/            # Clerk JWT + RBAC
├── packages/
│   ├── ui/                      # @scr/ui — shared React component library
│   ├── types/                   # @scr/types — shared TypeScript types
│   └── config/                  # @scr/config — ESLint, Tailwind, TS configs
├── services/
│   └── ai-gateway/              # LLM router + rate limiter + RAG microservice
├── infrastructure/
│   ├── docker/                  # Production Dockerfiles
│   ├── terraform/               # AWS IaC (VPC, RDS, ECS, ECR, S3)
│   └── scripts/                 # setup.sh automated bootstrap
├── .github/
│   └── workflows/               # CI (lint/test/build) + CD (staging/production)
└── docs/                        # Comprehensive documentation
```

---

## Quick Start

### Prerequisites

- **Node.js** >= 20, **pnpm** >= 9
- **Python** 3.12+, **Poetry** >= 1.8
- **Docker** & Docker Compose

### Automated Setup

```bash
chmod +x infrastructure/scripts/setup.sh
./infrastructure/scripts/setup.sh
```

### Manual Setup

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY, CLERK keys, etc.

# 2. Start infrastructure (PostgreSQL, Redis, ElasticSearch, MinIO)
docker compose up -d

# 3. Install dependencies
pnpm install
cd apps/api       && poetry install && cd ../..
cd services/ai-gateway && poetry install && cd ../..

# 4. Apply database migrations
cd apps/api && poetry run alembic upgrade head && cd ../..
```

### Start Development Servers

```bash
make start
# — or individually —
cd apps/api       && poetry run uvicorn app.main:app --reload --port 8000
cd services/ai-gateway && poetry run uvicorn app.main:app --reload --port 8001
cd apps/web       && pnpm dev
```

### Local Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Next.js app |
| API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/docs | Swagger UI (dev only) |
| AI Gateway | http://localhost:8001 | LLM routing service |
| MinIO Console | http://localhost:9001 | S3 file browser |
| MailHog | http://localhost:8025 | Email testing UI |

---

## Common Commands

```bash
make setup          # First-time dependency install
make start          # Start all services
make stop           # Stop all services
make test           # Run full test suite (API + frontend)
make lint           # Lint all code (ruff + eslint)
make db-migrate     # Run Alembic migrations
make db-reset       # Drop + recreate database
make reset          # Reset everything (deletes all data)
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Multi-tenant by default** | Every DB query scoped to `org_id` via `TenantMiddleware` — impossible to leak cross-org data |
| **Hierarchical RBAC** | `viewer < analyst < manager < admin` — cumulative permissions, O(1) lookup |
| **Immutable audit log** | All writes logged to `audit_logs` in fire-and-forget tasks with separate DB session |
| **AI Gateway microservice** | Single routing point for all LLM calls — rate limiting, cost tracking, model fallback |
| **Deterministic financials** | Valuations, equity calc, tax credits use pure Python math, never LLM generation |
| **No raw SQL** | SQLAlchemy ORM exclusively — parameterized queries eliminate SQL injection risk |
| **Streaming SSE for Ralph AI** | `StreamingResponse` on POST endpoints for low-latency conversational AI |

---

## CI/CD

Every push triggers GitHub Actions CI (lint + type-check + tests). Merges to `main` auto-deploy to **staging**. Production deploys require manual confirmation or a `v*.*.*` tag.

See [Deployment Guide](docs/deployment.md) for full pipeline documentation.
