# SCR Platform API — Developer Guide

## Prerequisites
- Python 3.12+
- Poetry 1.8+
- Docker + Docker Compose
- Node.js 20+ (for frontend)

## Local Setup
1. Clone the repo
2. Install Python deps: `cd apps/api && poetry install --with dev,blockchain`
3. Start services: `docker compose up -d` (starts PostgreSQL 16, Redis 7, MinIO, Elasticsearch 8)
4. Apply migrations: `poetry run alembic upgrade head`
5. Start API: `poetry run uvicorn app.main:app --reload` (port 8000)
6. Start frontend: `cd apps/web && pnpm dev` (port 3000)
7. Open API docs: http://localhost:8000/docs

## Project Structure
```
apps/api/
├── app/
│   ├── auth/           # Clerk JWT verification, RBAC
│   ├── core/           # Config, database, Redis, ES, circuit breaker
│   ├── middleware/     # Tenant, audit, rate limit, security headers
│   ├── models/         # SQLAlchemy 2.0 ORM models
│   ├── modules/        # Feature modules (auto-discovered)
│   ├── schemas/        # Shared Pydantic schemas
│   ├── services/       # Cross-cutting services (AI budget, token budget)
│   └── tasks/          # Background Celery tasks
├── alembic/            # DB migrations
└── tests/              # pytest test suite
```

## Adding a New Module
1. Create `apps/api/app/modules/{name}/`
2. Add: `__init__.py`, `router.py`, `schemas.py`, `service.py`
3. The module is **auto-discovered** — no `main.py` edit needed
4. Add tests in `tests/test_{name}.py`
5. If adding models, generate a migration:
   `poetry run alembic revision --autogenerate -m "add {name} tables"`

### Module template (router.py)
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.schemas.auth import CurrentUser

router = APIRouter(prefix="/{name}", tags=["{Name}"])

@router.get("", ...)
async def list_items(
    current_user: CurrentUser = Depends(require_permission("view", "{name}")),
    db: AsyncSession = Depends(get_db),
):
    ...
```

## RBAC Roles
| Role     | Can do                                   |
|----------|------------------------------------------|
| admin    | All operations including org settings    |
| manager  | Create/edit/delete most resources        |
| analyst  | Create/edit own resources, view all      |
| viewer   | Read-only access                         |

## Key Design Patterns

### Multi-tenancy
Every query must be filtered by `org_id`. Use `tenant_filter()`:
```python
from app.middleware.tenant import tenant_filter
stmt = tenant_filter(select(MyModel), current_user.org_id, MyModel)
```

### Read replica routing
For SELECT-only endpoints, use `get_readonly_db` to route to the replica:
```python
from app.core.database import get_db, get_readonly_db
db: AsyncSession = Depends(get_readonly_db)  # reads
db: AsyncSession = Depends(get_db)           # writes
```

### Background tasks
Celery workers run from the `app.worker` module. Queue a task:
```python
from app.modules.mymodule.tasks import my_task
my_task.delay(str(some_id))
```

## Testing
```bash
# Run all tests
poetry run pytest

# Run specific file
poetry run pytest tests/test_signal_score.py -xvs

# With coverage
poetry run pytest --cov=app --cov-report=term-missing

# Run quickly (short output)
poetry run pytest --tb=short -q
```

### Test fixtures
Tests use the `authenticated_client` fixture from `conftest.py` which:
- Overrides JWT verification with a test user
- Wraps each test in a transaction that rolls back after the test
- Overrides `get_db`, `get_readonly_db`, `get_readonly_session` with the test session

## Pre-Push Checklist
Run `./scripts/check.sh` from the repo root, which runs:
1. `ruff check .` — linting (zero errors)
2. `ruff format --check .` — formatting (run `ruff format .` to fix)
3. `mypy app/` — type checking
4. `alembic heads` — single migration head
5. `alembic check` — no pending model changes
6. `pytest` — all tests pass

Or run each step manually:
```bash
cd apps/api
poetry run ruff check . && poetry run ruff format --check .
poetry run mypy app/ --ignore-missing-imports
poetry run alembic check
poetry run pytest --tb=short -q
```

## Environment Variables
See `.env.example` for the full list. Key vars:
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async URL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis URL (`redis://localhost:6379/0`) |
| `CLERK_SECRET_KEY` | Clerk backend API key |
| `AI_GATEWAY_URL` | AI Gateway service URL (default: http://localhost:8001) |
| `AI_GATEWAY_API_KEY` | Service-to-service auth key |
| `AWS_S3_BUCKET` | S3 bucket for file storage |

## Architecture Notes
- **AI calls** always go through `services/ai-gateway` (port 8001) — never call Anthropic/OpenAI directly from the API
- **Financial calculations** are always deterministic Python — never LLM
- **Audit log**: all write operations are logged immutably via `AuditMiddleware`
- **Token budget**: per-org monthly AI token caps enforced via `app.services.token_budget`
- **Module discovery**: routers in `app/modules/*/router.py` are auto-loaded at startup
