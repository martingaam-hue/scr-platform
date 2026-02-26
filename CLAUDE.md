# SCR Platform — Claude Code Instructions

## What is this project?
SCR Platform is a SaaS investment intelligence platform connecting impact project developers ("Allies") with professional investors ("Investors"). It has 25 modules across 4 domains.

## Tech Stack
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, React Query, Zustand
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Celery
- **Database:** PostgreSQL 16, Redis 7, ElasticSearch 8
- **AI:** Claude Sonnet 4 (primary), GPT-4o (vision), litellm for unified access
- **Storage:** S3 (MinIO locally)
- **Auth:** Clerk

## Project Structure
```
scr-platform/
├── apps/
│   ├── web/          # Next.js frontend
│   └── api/          # FastAPI backend
├── packages/
│   ├── ui/           # Shared component library
│   ├── types/        # Shared TypeScript types
│   └── config/       # Shared configs
├── services/
│   └── ai-gateway/   # AI Gateway microservice
├── infrastructure/
│   ├── docker/
│   ├── terraform/
│   └── scripts/
└── docs/
```

## Coding Standards
- TypeScript strict mode, all frontend code
- Python type hints + Pydantic v2 models, all backend code
- Every API endpoint documented in OpenAPI
- Unit tests for all business logic
- Conventional commits
- Never hardcode secrets — use environment variables
- All database queries must be scoped to org_id (multi-tenant)
- Financial calculations: ALWAYS deterministic Python, NEVER LLM
- All AI calls go through the AI Gateway service

## Running Locally
```bash
docker compose up -d            # Start databases
cd apps/api && poetry run uvicorn app.main:app --reload  # Start API
cd apps/web && pnpm dev         # Start frontend
```

## Database Migrations
```bash
cd apps/api
poetry run alembic upgrade head          # Apply migrations
poetry run alembic revision --autogenerate -m "description"  # New migration
```

## Key Design Decisions
- Multi-tenant: every query filtered by org_id via middleware
- RBAC: admin > manager > analyst > viewer
- Audit: all write operations logged immutably
- AI Gateway: central service routes to correct LLM per task type
- Caching: Redis for API responses, AI results cached by input hash
