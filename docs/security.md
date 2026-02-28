# Security

## Overview

SCR Platform is a multi-tenant SaaS application handling sensitive financial and investment data. Security is enforced at multiple layers: authentication (Clerk JWT), authorisation (RBAC), multi-tenancy (org_id scoping), transport (TLS + security headers), rate limiting (Redis sliding window), and audit logging (immutable append-only).

---

## Authentication

### Clerk JWT

All API requests must include a valid RS256 JWT issued by Clerk:

```
Authorization: Bearer <clerk_jwt>
```

The `get_current_user()` dependency runs on every protected endpoint:

```
1. Extract Bearer token from Authorization header
2. Fetch JWKS from Clerk (cached in-process for 3600s)
3. Verify RS256 signature, expiry (exp), and issuer (iss)
4. Look up User by external_auth_id = jwt.sub
5. Return CurrentUser(user_id, org_id, role, org_type, email)
```

If verification fails, `401 Unauthorized` is returned immediately.

### Token Caching

JWKS keys are cached in an in-process dict with a 1-hour TTL. This avoids a Clerk round-trip on every request while ensuring key rotation is picked up within the hour.

### Webhook Sync

Clerk sends `user.created`, `user.updated`, and `user.deleted` webhook events to `POST /auth/webhooks`. Each payload is verified with Svix HMAC using `CLERK_WEBHOOK_SECRET` before the SCR `users` table is updated. Unverified webhooks are rejected with `400`.

---

## Authorisation (RBAC)

### Role Hierarchy

Roles are cumulative — each role inherits all permissions from lower roles:

```
viewer < analyst < manager < admin
```

| Level | Value |
|-------|-------|
| `viewer` | 0 |
| `analyst` | 1 |
| `manager` | 2 |
| `admin` | 3 |

### Permission Matrix

| Permission | viewer | analyst | manager | admin |
|-----------|--------|---------|---------|-------|
| view:project | ✓ | ✓ | ✓ | ✓ |
| view:portfolio | ✓ | ✓ | ✓ | ✓ |
| view:document | ✓ | ✓ | ✓ | ✓ |
| view:report | ✓ | ✓ | ✓ | ✓ |
| view:analysis | ✓ | ✓ | ✓ | ✓ |
| view:match | ✓ | ✓ | ✓ | ✓ |
| view:listing | ✓ | ✓ | ✓ | ✓ |
| view:conversation | ✓ | ✓ | ✓ | ✓ |
| view:comment | ✓ | ✓ | ✓ | ✓ |
| download:document | ✓ | ✓ | ✓ | ✓ |
| download:report | ✓ | ✓ | ✓ | ✓ |
| edit:project | | ✓ | ✓ | ✓ |
| edit:portfolio | | ✓ | ✓ | ✓ |
| edit:document | | ✓ | ✓ | ✓ |
| upload:document | | ✓ | ✓ | ✓ |
| create:report | | ✓ | ✓ | ✓ |
| run_analysis:analysis | | ✓ | ✓ | ✓ |
| create:conversation | | ✓ | ✓ | ✓ |
| create:comment | | ✓ | ✓ | ✓ |
| export:report | | ✓ | ✓ | ✓ |
| create:project | | | ✓ | ✓ |
| create:portfolio | | | ✓ | ✓ |
| delete:document | | | ✓ | ✓ |
| manage_team:team | | | ✓ | ✓ |
| create:match | | | ✓ | ✓ |
| create:listing | | | ✓ | ✓ |
| edit:listing | | | ✓ | ✓ |
| delete:project | | | | ✓ |
| delete:portfolio | | | | ✓ |
| delete:report | | | | ✓ |
| delete:listing | | | | ✓ |
| delete:comment | | | | ✓ |
| manage_settings:settings | | | | ✓ |
| manage_billing:billing | | | | ✓ |
| view:audit_log | | | | ✓ |

### Using RBAC in Endpoints

```python
from app.auth.dependencies import get_current_user, require_role
from app.models.enums import UserRole

# Require minimum role
@router.post("/projects")
async def create_project(
    body: ProjectCreate,
    current_user: CurrentUser = Depends(require_role([UserRole.MANAGER, UserRole.ADMIN])),
):
    ...

# Check permission in service layer
from app.auth.rbac import check_permission, Action, Resource

if not check_permission(current_user.role, Action.DELETE, Resource.PROJECT):
    raise HTTPException(status_code=403, detail="Insufficient permissions")
```

### Platform Admin

A separate access level exists for SCR platform administrators (`OrgType.ADMIN`). Regular org admins (`UserRole.ADMIN` within a non-admin org) cannot access platform admin endpoints.

```python
async def _require_platform_admin(current_user, db) -> CurrentUser:
    org = await db.get(Organization, current_user.org_id)
    if org is None or org.type != OrgType.ADMIN:
        raise HTTPException(status_code=403)
    return current_user
```

All `/admin/*` endpoints use this dependency.

---

## Multi-Tenancy

Every database table owned by an organisation has an `org_id` column. The `TenantMiddleware` extracts `org_id` from the verified JWT and sets `request.state.org_id`. All service-layer queries use `tenant_filter()`:

```python
from app.middleware.tenant import tenant_filter

stmt = (
    select(Project)
    .where(tenant_filter(Project, org_id))
    .where(Project.is_deleted.is_(False))
)
```

`tenant_filter(Model, org_id)` expands to `.where(Model.org_id == org_id)`. This pattern is enforced by code review — raw queries without `org_id` filtering are rejected.

Cross-org data leakage is structurally prevented: even if a request bypasses RBAC, it can only see rows scoped to its own `org_id`.

---

## HTTP Security Headers

Added by `SecurityHeadersMiddleware` (pure ASGI, applied to every response):

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `0` (disables broken IE filter) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=(), payment=()` |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` (production only) |
| `Server` | `SCR` (fingerprint removed) |

### Frontend CSP

Next.js adds a strict `Content-Security-Policy` to all responses:

```
default-src 'self';
script-src 'self' 'unsafe-eval' 'unsafe-inline' https://clerk.com https://*.clerk.accounts.dev;
style-src 'self' 'unsafe-inline';
img-src 'self' blob: data: https:;
font-src 'self';
connect-src 'self' https://api.clerk.com https://*.clerk.accounts.dev;
frame-src https://accounts.clerk.dev https://*.clerk.accounts.dev;
frame-ancestors 'none';
```

`X-Powered-By: Next.js` is also removed (`poweredByHeader: false`).

---

## Rate Limiting

IP-based sliding window rate limiting implemented in `RateLimitMiddleware` (pure ASGI, Redis-backed).

### Rules

| Path prefix | Limit | Window |
|-------------|-------|--------|
| `/auth/` | 20 req | 60s |
| `/webhooks/` | 200 req | 60s |
| `/ralph/` | 60 req | 60s |
| `/investor-signal-score/calculate` | 10 req | 60s |
| All other paths | 300 req | 60s |

Paths `/health`, `/docs`, `/redoc`, `/openapi.json`, `/favicon.ico` are excluded.

### Behaviour

- Requests that exceed the limit receive `429 Too Many Requests` with a `Retry-After` header
- All passing responses include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Window` headers
- If Redis is unavailable, the middleware **fails open** — requests are never blocked due to Redis downtime
- Client IP is resolved from `X-Forwarded-For` (first entry, set by the ALB) with direct `REMOTE_ADDR` as fallback

### AI Gateway Rate Limits

Per-organisation token budgets are enforced separately in the AI Gateway using Redis sliding windows:

| Tier | Request limit | Token limit |
|------|--------------|------------|
| `foundation` | 100 req/hr | 500K tokens/day |
| `professional` | 500 req/hr | 2M tokens/day |
| `enterprise` | 2000 req/hr | 10M tokens/day |

---

## Request Body Size Limit

`RequestBodySizeLimitMiddleware` rejects any request where `Content-Length` exceeds 50 MB with `413 Request Entity Too Large`. This prevents memory exhaustion from large uploads hitting the API process — file uploads go directly to S3 via pre-signed URL and never pass through the API body.

---

## CORS

```python
CORSMiddleware(
    allow_origins=settings.CORS_ORIGINS,   # explicit list, no wildcard in prod
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
```

`settings.CORS_ORIGINS` is set via environment variable. In production this is the exact frontend domain only.

---

## Request Middleware Stack

Requests pass through middleware in this order (outermost first):

```
SecurityHeadersMiddleware   — adds/strips security headers on response
  ↓
RateLimitMiddleware         — IP-based sliding window, Redis-backed
  ↓
RequestBodySizeLimitMiddleware — 50 MB hard limit on Content-Length
  ↓
TenantMiddleware            — sets request.state.org_id and user_id
  ↓
AuditMiddleware             — registers post-response hook for writes
  ↓
CORSMiddleware              — CORS pre-flight + origin enforcement
  ↓
Route handler
  └── get_current_user()    — Clerk JWT verification
      require_role()        — RBAC enforcement
      get_db()              — AsyncSession injection
      business logic
```

All middleware is implemented as pure ASGI classes (not `BaseHTTPMiddleware`) to avoid response buffering, which would break SSE streaming for Ralph AI.

---

## Audit Log

Every write operation (POST/PUT/PATCH/DELETE returning 2xx) produces an immutable audit log row:

```
AuditLog
  id          UUID
  org_id      UUID
  user_id     UUID
  action      VARCHAR  (e.g. "project.create", "document.delete")
  resource    VARCHAR  (e.g. "projects")
  resource_id VARCHAR
  changes     JSONB    (before/after snapshot)
  ip_address  VARCHAR
  user_agent  VARCHAR
  created_at  TIMESTAMP  — no updated_at, no soft delete
```

The `AuditMiddleware` registers a background task that writes the log row using a dedicated DB session (separate from the request session). This means audit log failures never roll back business transactions, and business transaction failures still produce audit entries for attempted operations.

Audit logs are queryable by admins via `GET /admin/audit-logs` (requires `OrgType.ADMIN`).

---

## SQL Injection Prevention

SQLAlchemy ORM with parameterized queries is used exclusively — no raw SQL strings. The `tenant_filter()` pattern ensures all queries are scoped correctly. String interpolation into SQL is prohibited by code convention and caught in code review.

---

## Document Security

- All uploads go to S3 via pre-signed `PUT` URLs — file bytes never pass through the API
- Downloads use pre-signed `GET` URLs (time-limited, scoped to the org)
- SHA-256 integrity is verified after upload
- File type whitelist: `pdf, docx, xlsx, pptx, csv, jpg, png`
- 100 MB per-document size limit enforced at the S3 pre-signed URL level
- Per-document access log tracks view/download/share/print events

---

## Secret Management

| Environment | Secret storage |
|------------|---------------|
| Local dev | `.env` file (gitignored) |
| Staging / Production | AWS Secrets Manager (injected at ECS task start) |

Required secrets:
- `SECRET_KEY` — session signing key (min 32 chars, must be changed from default)
- `CLERK_SECRET_KEY` — Clerk backend API key
- `CLERK_WEBHOOK_SECRET` — Svix HMAC secret
- `ANTHROPIC_API_KEY` — Claude API key
- `AI_GATEWAY_API_KEY` — internal shared secret between API and AI Gateway
- `DATABASE_URL` / `DATABASE_URL_SYNC` — PostgreSQL connection strings
- `REDIS_URL` — Redis connection string

The API process validates at startup in production (`APP_ENV=production`) that `SECRET_KEY` is not the default value and that `CLERK_SECRET_KEY` is present — if not, the process exits with code 1 before accepting any connections.

---

## Production Checklist

- [ ] `APP_ENV=production` set
- [ ] `SECRET_KEY` set to a random 64-character string
- [ ] `CLERK_SECRET_KEY` and `CLERK_WEBHOOK_SECRET` set
- [ ] `CORS_ORIGINS` set to exact frontend domain
- [ ] `RATE_LIMIT_ENABLED=true`
- [ ] OpenAPI docs disabled (automatic when `APP_ENV=production`)
- [ ] HSTS header enabled (automatic when `APP_ENV=production`)
- [ ] All secrets in AWS Secrets Manager, not in environment files
- [ ] TLS certificate valid and HTTPS enforced at ALB
- [ ] S3 bucket private (no public access), pre-signed URLs only
