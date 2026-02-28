# Deployment Guide

## Overview

SCR Platform is deployed on AWS using ECS Fargate (serverless containers), RDS PostgreSQL, ElastiCache Redis, and S3. Infrastructure is managed with Terraform. CI/CD runs on GitHub Actions.

```
GitHub Actions CI  ──→  ECR (image registry)
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
               ECS Staging        ECS Production
               (auto-deploy)      (manual confirm)
                    │
                    ▼
          ┌─────────────────────────────────┐
          │  ALB (HTTPS, TLS 1.3)           │
          │  /api/*   → scr-api (port 8000) │
          │  /        → scr-web (port 3000) │
          └─────────────────────────────────┘
```

---

## CI Pipeline

Defined in `.github/workflows/ci.yml`. Runs on every push to `main` and on all pull requests.

### Jobs (run in parallel)

| Job | What it checks |
|-----|---------------|
| `api-lint` | `ruff check`, `ruff format --check`, `mypy` |
| `api-test` | `pytest` with coverage against real PostgreSQL + Redis service containers |
| `api-security` | `pip-audit` against exported requirements.txt |
| `gateway-lint` | `ruff check` on AI Gateway |
| `web-lint` | `tsc --noEmit` + ESLint |
| `web-build` | Full Next.js production build |
| `web-security` | `pnpm audit --audit-level moderate` |
| `ci-passed` | Summary gate — required status check for merges |

`api-test` depends on `api-lint` (fail fast). `web-build` depends on `web-lint`. All other jobs are independent.

### Test environment

The `api-test` job spins up PostgreSQL 16 and Redis 7 as service containers, applies Alembic migrations, then runs the full test suite with coverage reported to Codecov.

---

## Staging CD Pipeline

Defined in `.github/workflows/cd-staging.yml`. Triggers automatically on every merge to `main`.

### Flow

```
1. Build images (parallel):
   ├── API image     → ECR: scr-api:{sha}, scr-api:staging-latest
   ├── Web image     → ECR: scr-web:{sha}, scr-web:staging-latest
   └── Gateway image → ECR: scr-ai-gateway:{sha}, scr-ai-gateway:staging-latest

2. Run DB migrations (sequential, waits on API image):
   └── aws ecs run-task --overrides '{"command":["alembic","upgrade","head"]}'
       └── Wait for exit 0 — abort if non-zero

3. Deploy services (rolling update, sequential):
   ├── API service     → wait-for-stability (10 min timeout)
   ├── Gateway service → wait-for-stability
   └── Web service     → wait-for-stability

4. Smoke tests:
   ├── GET /health → expect 200
   └── GET / → expect 200 or 307
```

Deployments are never cancelled mid-flight (`cancel-in-progress: false`).

---

## Production CD Pipeline

Defined in `.github/workflows/cd-production.yml`.

### Triggers

| Trigger | When |
|---------|------|
| `workflow_dispatch` | Manual trigger — requires `confirm: DEPLOY` |
| Tag push `v*.*.*` | Automatic on semver tags |

### Flow

```
1. Confirm (manual trigger only):
   └── Check input confirm == "DEPLOY" — abort if not

2. Promote images (re-tag, no rebuild):
   └── scr-{api,web,ai-gateway}:{sha} → scr-{api,web,ai-gateway}:production-latest
       (guarantees exact same bytes as staging)

3. Run DB migrations:
   └── Same pattern as staging, but against production cluster

4. Deploy services (rolling update, 15 min timeout for API):
   ├── API → scr-api-production
   ├── Gateway → scr-ai-gateway-production
   └── Web → scr-web-production

5. Verification:
   ├── GET /health → retry 10× with 15s delay
   ├── GET / → expect 200/301/307
   └── Create GitHub release (on tag push only)
```

---

## Required GitHub Secrets

Configure these in **Settings → Secrets → Actions** for both `staging` and `production` environments.

### AWS

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM user with ECR push + ECS deploy permissions |
| `AWS_SECRET_ACCESS_KEY` | Secret for the above |
| `ECR_REGISTRY` | ECR registry URI, e.g. `123456789.dkr.ecr.eu-west-1.amazonaws.com` |

### Staging environment

| Secret | Description |
|--------|-------------|
| `STAGING_API_URL` | API base URL for smoke tests, e.g. `https://api.staging.scr-platform.com` |
| `STAGING_WEB_URL` | Web URL for smoke tests, e.g. `https://staging.scr-platform.com` |
| `STAGING_API_URL` | Also used as `NEXT_PUBLIC_API_URL` build arg |
| `STAGING_CLERK_PUBLISHABLE_KEY` | Clerk publishable key for staging |
| `STAGING_PRIVATE_SUBNET_IDS` | Comma-separated private subnet IDs for migration ECS task |
| `STAGING_ECS_SG_ID` | Security group ID for migration ECS task |

### Production environment

| Secret | Description |
|--------|-------------|
| `PROD_API_URL` | Production API URL |
| `PROD_WEB_URL` | Production web URL |
| `PROD_PRIVATE_SUBNET_IDS` | Private subnet IDs for migration ECS task |
| `PROD_ECS_SG_ID` | Security group ID for migration ECS task |

---

## AWS Infrastructure (Terraform)

All infrastructure is defined in `infrastructure/terraform/`.

### Files

| File | Contents |
|------|----------|
| `variables.tf` | Environment, region, instance sizes, ACM cert ARN |
| `ecr.tf` | 3 ECR repositories with scan-on-push + lifecycle policies |
| `ecs.tf` | ECS cluster, IAM roles, security groups, task definitions, services, ALB, auto-scaling |

### First-time setup

```bash
cd infrastructure/terraform

# Initialise Terraform
terraform init

# Plan changes
terraform plan -var="environment=staging" -var="acm_certificate_arn=arn:aws:acm:..."

# Apply
terraform apply -var="environment=staging" -var="acm_certificate_arn=arn:aws:acm:..."
```

### Key Terraform variables

| Variable | Default | Description |
|----------|---------|-------------|
| `environment` | `staging` | `staging` or `production` |
| `aws_region` | `eu-west-1` | AWS region |
| `db_instance_class` | `db.t4g.medium` | RDS instance class |
| `redis_node_type` | `cache.t4g.micro` | ElastiCache node type |
| `api_cpu` | `512` | ECS API task CPU units (512 = 0.5 vCPU) |
| `api_memory` | `1024` | ECS API task memory (MiB) |
| `acm_certificate_arn` | — | **Required.** ACM cert for ALB HTTPS listener |

### ECR repositories

| Repository | Image | Lifecycle policy |
|-----------|-------|-----------------|
| `scr-api` | FastAPI backend | Keep last 20 tagged; delete untagged after 1 day |
| `scr-web` | Next.js frontend | Same |
| `scr-ai-gateway` | AI Gateway | Same |

### ECS services

| Service | Staging tasks | Production tasks | Auto-scaling |
|---------|--------------|-----------------|--------------|
| `scr-api` | 1 | 2–10 | CPU target 70% |
| `scr-ai-gateway` | 1 | 1 | None |
| `scr-web` | 1 | 2 | None |

### ALB routing

```
HTTPS :443
  ├── /api/*  → scr-api    (target group, port 8000)
  └── /*      → scr-web    (target group, port 3000)

HTTP :80 → redirect to HTTPS 301
```

TLS policy: `ELBSecurityPolicy-TLS13-1-2-2021-06` (TLS 1.2 minimum, TLS 1.3 preferred).

### Secrets Management

All application secrets are stored in AWS Secrets Manager and injected at ECS task start via `secrets` in the task definition. Secrets are never baked into images or passed as plain environment variables in production.

The Terraform `ecs.tf` references secrets by ARN in task definitions:

```hcl
secrets = [
  { name = "DATABASE_URL",      valueFrom = aws_secretsmanager_secret.database_url.arn },
  { name = "REDIS_URL",         valueFrom = aws_secretsmanager_secret.redis_url.arn },
  { name = "CLERK_SECRET_KEY",  valueFrom = aws_secretsmanager_secret.clerk_secret_key.arn },
  { name = "ANTHROPIC_API_KEY", valueFrom = aws_secretsmanager_secret.anthropic_api_key.arn },
  ...
]
```

---

## Docker Images

### API (`infrastructure/docker/Dockerfile.api`)

Multi-stage build:

1. **`base`** — Python 3.12 slim, installs Poetry
2. **`deps`** — Installs production dependencies only (no dev extras)
3. **`final`** — Non-root `scr` user, copies app code, starts uvicorn with `--proxy-headers`

```bash
docker build -f infrastructure/docker/Dockerfile.api -t scr-api:local .
```

HEALTHCHECK: `curl -f http://localhost:8000/health || exit 1` (30s interval)

### Web (`infrastructure/docker/Dockerfile.web`)

Multi-stage build:

1. **`base`** — Node 20 alpine, installs pnpm
2. **`deps`** — pnpm install (with lockfile)
3. **`builder`** — pnpm build (Next.js standalone output)
4. **`runner`** — Non-root `nextjs` user, copies `.next/standalone` + static assets

Requires `output: "standalone"` in `next.config.mjs` (already configured).

```bash
docker build -f infrastructure/docker/Dockerfile.web \
  --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 \
  --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_... \
  -t scr-web:local .
```

### AI Gateway (`services/ai-gateway/Dockerfile`)

Same multi-stage pattern as API. Built from the `services/ai-gateway/` context.

---

## Database Migrations

Alembic migrations are **never** run at container startup. They run as a one-off ECS Fargate task before each deploy. This separates migration failures from service failures and allows rollback.

```bash
# Manual migration (local)
cd apps/api
poetry run alembic upgrade head

# Rollback one step
poetry run alembic downgrade -1

# Check current state
poetry run alembic current
poetry run alembic history
```

In CI/CD, the migration task uses the same Docker image as the API service with a command override:

```
command: ["poetry", "run", "alembic", "upgrade", "head"]
```

The deployment pipeline waits for the task to exit with code 0 before proceeding to rolling service update. Non-zero exit aborts the deployment.

---

## Health Checks

| Service | Endpoint | Expected |
|---------|---------|---------|
| API | `GET /health` | `200 OK` |
| AI Gateway | `GET /health` | `200 OK` |
| Web | `GET /` | `200` or `307` (auth redirect) |

The ALB health check targets `/health` on the API and Gateway containers. ECS will replace unhealthy tasks automatically.

---

## Monitoring

| Service | Tool |
|---------|------|
| Container logs | CloudWatch Logs (14 days staging, 90 days production) |
| ECS metrics | CloudWatch Container Insights |
| API costs | `GET /admin/ai-costs` (platform admin endpoint) |
| System health | `GET /admin/system-health` (DB, Redis, AI Gateway latency) |

---

## Rollback

Since production images are never rebuilt (they are re-tagged from staging), rollback is a re-deploy of a previous SHA:

```bash
# Roll back to a specific commit SHA
gh workflow run cd-production.yml \
  -f image_tag=<previous-sha> \
  -f confirm=DEPLOY
```

For database rollbacks:

```bash
# Via ECS one-off task
aws ecs run-task \
  --cluster scr-production \
  --task-definition scr-api-migrate-production \
  --overrides '{"containerOverrides":[{"name":"api","command":["poetry","run","alembic","downgrade","-1"]}]}'
```

---

## Local Production Simulation

```bash
# Build all images locally
docker build -f infrastructure/docker/Dockerfile.api -t scr-api:local .
docker build -f infrastructure/docker/Dockerfile.web \
  --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 \
  --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_... \
  -t scr-web:local .

# Run with docker compose (dev override)
docker compose up -d
```

For true production configuration testing, use `APP_ENV=production` and supply all required secrets via `.env`.
