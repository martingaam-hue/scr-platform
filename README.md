# SCR Platform

Investment intelligence platform connecting impact project developers (Allies) with professional investors (Investors).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Celery |
| Database | PostgreSQL 16, Redis 7, ElasticSearch 8 |
| AI | Claude Sonnet 4 (primary), GPT-4o (vision), litellm |
| Storage | S3 (MinIO locally) |
| Auth | Clerk |
| Monorepo | Turborepo, pnpm workspaces |

## Project Structure

```
scr-platform/
├── apps/
│   ├── web/                 # Next.js 14 frontend
│   └── api/                 # FastAPI backend
├── packages/
│   ├── ui/                  # Shared React component library
│   ├── types/               # Shared TypeScript types
│   └── config/              # Shared ESLint, Tailwind, TypeScript configs
├── services/
│   └── ai-gateway/          # AI Gateway microservice
├── infrastructure/
│   ├── docker/              # Dockerfiles
│   ├── terraform/           # AWS infrastructure as code
│   └── scripts/             # Utility scripts
└── docs/                    # Documentation
```

## Quick Start

### Prerequisites

- Node.js >= 20
- pnpm >= 9
- Python 3.12+
- Poetry
- Docker & Docker Compose

### Setup

```bash
# Automated setup
chmod +x infrastructure/scripts/setup.sh
./infrastructure/scripts/setup.sh

# Or manual setup
cp .env.example .env              # Configure environment
docker compose up -d              # Start databases
pnpm install                      # Install JS dependencies
cd apps/api && poetry install     # Install API dependencies
cd services/ai-gateway && poetry install  # Install AI Gateway deps
```

### Development

```bash
make start                        # Start all services
# Or individually:
docker compose up -d              # Start databases
cd apps/api && poetry run uvicorn app.main:app --reload  # API on :8000
cd services/ai-gateway && poetry run uvicorn app.main:app --reload --port 8001  # AI Gateway on :8001
cd apps/web && pnpm dev           # Frontend on :3000
```

### Services

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| AI Gateway | http://localhost:8001 |
| MinIO Console | http://localhost:9001 |
| MailHog (emails) | http://localhost:8025 |

## Commands

```bash
make setup          # First-time setup
make start          # Start all services
make stop           # Stop all services
make test           # Run all tests
make lint           # Lint all code
make db-migrate     # Run database migrations
make db-reset       # Reset database
make reset          # Reset everything (deletes all data)
```

## Architecture Decisions

- **Multi-tenant**: Every database query scoped to `org_id` via middleware
- **RBAC**: admin > manager > analyst > viewer
- **Audit**: All write operations logged immutably
- **AI Gateway**: Central service routes to the correct LLM per task type
- **Caching**: Redis for API responses, AI results cached by input hash
- **Financial calculations**: Always deterministic Python, never LLM
