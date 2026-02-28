# Development Guide

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Node.js | >= 20 | https://nodejs.org or `nvm install 20` |
| pnpm | >= 9 | `npm install -g pnpm` |
| Python | 3.12+ | https://python.org or `pyenv install 3.12` |
| Poetry | >= 1.8 | `pip install poetry` |
| Docker | >= 24 | https://docker.com |
| Docker Compose | >= 2.20 | Bundled with Docker Desktop |

---

## First-Time Setup

### Automated (recommended)

```bash
chmod +x infrastructure/scripts/setup.sh
./infrastructure/scripts/setup.sh
```

This script checks prerequisites, creates `.env` from `.env.example`, starts Docker services, and installs all dependencies.

### Manual

```bash
# 1. Clone and configure
git clone <repo-url>
cd scr-platform
cp .env.example .env
# → Edit .env and add: ANTHROPIC_API_KEY, CLERK_SECRET_KEY, CLERK_WEBHOOK_SECRET

# 2. Start infrastructure
docker compose up -d
# Wait for all services to be healthy: docker compose ps

# 3. Install Node dependencies (all workspaces)
pnpm install

# 4. Install Python dependencies
cd apps/api          && poetry install && cd ../..
cd services/ai-gateway && poetry install && cd ../..

# 5. Create database schema
cd apps/api && poetry run alembic upgrade head && cd ../..
```

---

## Daily Development Workflow

### Start Everything

```bash
make start
```

This starts Docker services (if not running) and launches all three servers in the background. Alternatively:

```bash
# Terminal 1 — API
cd apps/api && poetry run uvicorn app.main:app --reload --port 8000

# Terminal 2 — AI Gateway
cd services/ai-gateway && poetry run uvicorn app.main:app --reload --port 8001

# Terminal 3 — Frontend
cd apps/web && pnpm dev
```

### Stop Everything

```bash
make stop
```

### Database Migrations

```bash
# Apply pending migrations
make db-migrate

# Create a new migration (after changing models)
cd apps/api
poetry run alembic revision --autogenerate -m "add xyz column"
poetry run alembic upgrade head

# Rollback one step
poetry run alembic downgrade -1

# Hard reset (drops all data)
make db-reset
```

---

## Project Conventions

### Backend (Python)

**Module structure** — every feature module follows the same pattern:

```
apps/api/app/modules/<feature>/
├── __init__.py      # empty
├── router.py        # FastAPI APIRouter, endpoint handlers
├── service.py       # async business logic (no HTTP concerns)
├── schemas.py       # Pydantic v2 request/response models
└── tasks.py         # Celery tasks (optional, for async work)
```

**Naming:**

```python
# Router prefix: lowercase, hyphens
router = APIRouter(prefix="/investor-signal-score", tags=["investor-signal-score"])

# Service functions: snake_case, async
async def calculate_score(db: AsyncSession, org_id: UUID) -> InvestorSignalScore: ...

# Schemas: PascalCase, descriptive
class SignalScoreCalculationRequest(BaseModel): ...
class SignalScoreResponse(BaseModel): ...
```

**Database queries — always scope to org_id:**

```python
from app.middleware.tenant import tenant_filter

stmt = (
    select(Project)
    .where(tenant_filter(Project, org_id))
    .where(Project.is_deleted.is_(False))
    .order_by(Project.created_at.desc())
)
```

**Never call `db.commit()` in service functions** — sessions are committed at the router layer or rolled back on exception. Service functions use `db.flush()` to write without committing:

```python
db.add(new_entity)
await db.flush()  # assigns ID, writes to transaction — not yet committed
return new_entity
```

**Always `await db.refresh(obj)` after `flush()` before reading server-set columns** — accessing columns like `updated_at` (set by the DB trigger) after a flush without a refresh causes `MissingGreenlet` in asyncio SQLAlchemy:

```python
db.add(entity)
await db.flush()
await db.refresh(entity)  # required before accessing server-set fields
return SomeResponse(updated_at=entity.updated_at)
```

**`datetime.utcnow()` for TIMESTAMP WITHOUT TIME ZONE columns** — asyncpg rejects timezone-aware datetimes for `TIMESTAMP WITHOUT TIME ZONE` columns. Use `datetime.utcnow()`, not `datetime.now(timezone.utc)`:

```python
# ✅ Correct
from datetime import datetime
last_updated = datetime.utcnow()

# ❌ asyncpg will raise DataError
from datetime import datetime, timezone
last_updated = datetime.now(timezone.utc)
```

**PostgreSQL native enum columns and SQLAlchemy** — Core models (projects, portfolios) use uppercase PostgreSQL enum values matching Python `.name`. Advisory module models use lowercase PostgreSQL enum values matching Python `.value`. When a table was migrated with lowercase enum labels, use `values_callable` to force SQLAlchemy to bind by value:

```python
from sqlalchemy import Enum as SAEnum

def _lc_enum(enum_cls, type_name: str, **kw):
    """Create a mapped_column using lowercase enum values (matching the DB)."""
    return mapped_column(
        SAEnum(
            enum_cls,
            values_callable=lambda x: [e.value for e in x],
            name=type_name,
            create_type=False,
        ),
        **kw,
    )

# Usage:
availability_status: Mapped[AdvisorAvailabilityStatus] = _lc_enum(
    AdvisorAvailabilityStatus, "advisoravailabilitystatus",
    nullable=False, default=AdvisorAvailabilityStatus.AVAILABLE,
)
```

This pattern is used throughout `apps/api/app/models/advisory.py` for all advisory-specific enums.

**Pydantic v2 models:**

```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: ProjectType
    target_raise: Decimal | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()
```

**Logging** — always use `structlog`, never `print`:

```python
import structlog
logger = structlog.get_logger()

logger.info("signal_score.calculated", org_id=str(org_id), score=result.overall_score)
logger.warning("auth.user_not_found", clerk_id=clerk_user_id)
logger.error("celery.task_failed", task=task_name, error=str(exc))
```

### Frontend (TypeScript)

**File structure:**

```
apps/web/src/
├── app/(dashboard)/       # Feature pages (one directory per module)
│   └── <feature>/
│       └── page.tsx       # "use client" React component
├── components/            # Shared layout components (Sidebar, Topbar, etc.)
├── lib/                   # Per-module hooks + types + helpers
│   └── <feature>.ts       # useFeatureData(), useCreateFeature(), types
└── lib/
    ├── api.ts             # Axios instance
    ├── auth.tsx           # useSCRUser(), usePermission()
    └── store.ts           # Zustand stores
```

**React Query pattern** — every module has a key factory and typed hooks:

```typescript
// lib/projects.ts
export const projectKeys = {
  all: ["projects"] as const,
  list: (filters?: Filters) => [...projectKeys.all, "list", filters] as const,
  detail: (id: string) => [...projectKeys.all, "detail", id] as const,
};

export function useProjects(filters?: Filters) {
  return useQuery({
    queryKey: projectKeys.list(filters),
    queryFn: () => api.get<ProjectPage>("/projects", { params: filters }).then(r => r.data),
    retry: false,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProjectCreate) =>
      api.post<Project>("/projects", body).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: projectKeys.all }),
  });
}
```

**Auth-gated components:**

```typescript
"use client";
import { useSCRUser, usePermission } from "@/lib/auth";

export default function ProjectsPage() {
  const { user } = useSCRUser();
  const canCreate = usePermission("create", "project");

  if (!user) return null; // loading state
  // ...
}
```

**Component imports:**

```typescript
// UI components from @scr/ui package
import { Button, Card, CardContent, Badge, EmptyState } from "@scr/ui";

// Icons from lucide-react
import { Plus, RefreshCw, TrendingUp } from "lucide-react";
```

---

## Testing

### Backend

```bash
cd apps/api

# Run all tests
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=app --cov-report=term-missing

# Run a specific file
poetry run pytest tests/test_ai_integration.py -v

# Run a specific test
poetry run pytest tests/test_ai_integration.py::TestRalphAIConversation::test_conversation_creation -v
```

**Test patterns** — tests use real PostgreSQL (rolled back after each test):

```python
# conftest.py already provides: db, client, sample_org, sample_user, sample_current_user
# Use dependency overrides for auth:

async def test_create_project(db: AsyncSession, sample_current_user: CurrentUser):
    app.dependency_overrides[get_current_user] = lambda: sample_current_user
    app.dependency_overrides[get_db] = lambda: db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/projects", json={"name": "Test Project", "type": "solar"})
        assert resp.status_code == 201
    finally:
        app.dependency_overrides.clear()
```

**Important:** Never use `db.commit()` in tests — the `db` fixture rolls back after each test automatically.

**Decimal column comparison in tests** — `Numeric(19, 4)` columns serialize as `"10000000.0000"`, not `"10000000"`. Always use `float()` when asserting numeric values from API responses:

```python
# ✅ Correct
assert float(data["total_invested"]) == 10_000_000

# ❌ Will fail due to trailing zeros
assert data["total_invested"] == "10000000"
```

**Relationship reload in tests** — SQLAlchemy's identity map caches object state within a session. If you load an object, then add related rows in the same session, the cached collection won't reflect the new rows. Add `.execution_options(populate_existing=True)` to force a fresh load:

```python
stmt = (
    select(AIConversation)
    .where(AIConversation.id == conv_id)
    .options(selectinload(AIConversation.messages))
    .execution_options(populate_existing=True)  # forces messages reload
)
```

**Pydantic model completeness** — Pydantic v2 strict validation requires all non-optional fields when constructing models. When seeding test data that goes through Pydantic validation at the API layer, always provide the full schema — partial objects will cause 422 validation errors that can be hard to trace.

### Frontend

```bash
cd apps/web

# Type check
pnpm exec tsc --noEmit

# Lint
pnpm lint

# Build (catches import/config errors)
pnpm build
```

---

## Linting & Formatting

### Backend

```bash
cd apps/api

# Lint
poetry run ruff check .

# Format
poetry run ruff format .

# Type check
poetry run mypy app/ --ignore-missing-imports
```

Ruff config is in `pyproject.toml`. Rules include: `E, F, I, N, W, UP, B, SIM, RUF`. Line length 100.

### Frontend

```bash
# Lint (runs ESLint via Next.js)
pnpm --filter @scr/web lint

# Format (if Prettier configured)
pnpm format
```

---

## Adding a New Module

### 1. Backend

```bash
mkdir apps/api/app/modules/my_feature
touch apps/api/app/modules/my_feature/__init__.py
```

Create `schemas.py`, `service.py`, `router.py` following the existing pattern. Then register in `apps/api/app/main.py`:

```python
from app.modules.my_feature.router import router as my_feature_router
# ...
app.include_router(my_feature_router)
```

### 2. Database Model (if needed)

```bash
cd apps/api

# Add model to apps/api/app/models/
# Import it in apps/api/app/models/__init__.py

# Generate migration
poetry run alembic revision --autogenerate -m "add my_feature table"
poetry run alembic upgrade head
```

### 3. Frontend

```bash
mkdir "apps/web/src/app/(dashboard)/my-feature"
touch "apps/web/src/app/(dashboard)/my-feature/page.tsx"
touch apps/web/src/lib/my-feature.ts
```

Add to sidebar nav in `apps/web/src/components/sidebar.tsx` for appropriate org types.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...localhost` | Async DB connection |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Redis for cache + rate limits |
| `CLERK_SECRET_KEY` | Yes | — | Clerk backend API key |
| `CLERK_WEBHOOK_SECRET` | Yes | — | Clerk webhook HMAC secret |
| `CLERK_ISSUER_URL` | Yes | — | `https://your-app.clerk.accounts.dev` |
| `ANTHROPIC_API_KEY` | Yes | — | Claude API key |
| `OPENAI_API_KEY` | No | — | GPT-4o fallback / vision |
| `AI_GATEWAY_API_KEY` | Yes | `internal-dev-key-...` | Shared secret between API + Gateway |
| `SECRET_KEY` | Yes | ⚠️ change in prod | Session signing key |
| `APP_ENV` | No | `development` | `development` \| `staging` \| `production` |
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000` | API base URL (frontend) |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Yes | — | Clerk frontend key |

See `.env.example` for the complete list including S3, ElasticSearch, and email settings.

---

## Debugging Tips

**API not starting:**

```bash
cd apps/api && poetry run python -c "from app.main import app; print('OK')"
# Shows import errors clearly
```

**Database connection issues:**

```bash
docker compose ps  # Check postgres is healthy
docker compose logs db  # Check for init errors
```

**Alembic migration conflicts:**

```bash
cd apps/api
poetry run alembic history  # See applied migrations
poetry run alembic current  # See current head
poetry run alembic heads    # See all head revisions (branching)
```

**Redis not connecting:**

```bash
redis-cli ping  # Should return PONG
docker compose logs redis
```

**Next.js build failing:**

```bash
cd apps/web && pnpm exec tsc --noEmit  # TypeScript errors
pnpm --filter @scr/ui build            # Ensure packages are built first
```
