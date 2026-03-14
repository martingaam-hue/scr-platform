# SCR Platform — Performance Baseline

**Date:** 2026-03-14
**Commit:** `1ac8b04`
**Tool:** Locust 2.43.3

---

## ⚠️ Environment Notes

Two environments measured. Results differ significantly:

| Environment | Setup | Notes |
|-------------|-------|-------|
| **Local** | Docker Compose (PostgreSQL 16, Redis 7, AI Gateway) + single Uvicorn worker on macOS M-series | DB and Redis on same host — no network round-trip. Best-case floor. |
| **Staging** | ECS Fargate eu-north-1, ALB, RDS PostgreSQL, ElastiCache Redis | `/health` p50 = 9.1s during test — ECS tasks were cold-starting. Re-run after sustained warm traffic for production-representative numbers. |

> **Auth note:** Authenticated endpoint results below are for a local environment
> without a valid `LOAD_TEST_JWT`. Latency reflects full middleware stack
> (correlation ID, rate limiter, JWT parse + rejection) but **not** actual DB
> query execution. To measure real query latency: set `LOAD_TEST_JWT` to a
> valid Clerk JWT for a staging user and re-run. See
> `apps/api/tests/load/README.md`.

---

## Infrastructure & Routing Overhead (local, 50 concurrent users, 5 min)

These measure the cost of the middleware stack up to and including auth
rejection — the irreducible overhead on every request before any business
logic runs.

| Layer | p50 | p95 | p99 | Notes |
|-------|-----|-----|-----|-------|
| `/health` (no auth) | 13 ms | 27 ms | 71 ms | Full DB + Redis ping |
| `/health/ai` circuit breaker check | 5 ms | 14 ms | 29 ms | Redis state read only |
| Auth rejection overhead (401) | 5 ms | 29–31 ms | 43–85 ms | Rate limiter + JWT decode + reject |
| Peak throughput (`/health` only, 50 users) | — | — | — | **28.1 RPS sustained** |

---

## API Response Times — General Endpoints (local, 50 users, 5 min)

> All authenticated endpoints returned 401 (no `LOAD_TEST_JWT` set).
> Latency = middleware + auth rejection overhead, **not** DB query time.
> Numbers are a lower bound; actual authenticated latency will be higher.

| Endpoint | p50 | p95 | p99 | RPS | Error |
|----------|-----|-----|-----|-----|-------|
| GET /health | **13 ms** | **27 ms** | **71 ms** | 4.2 | 0% ✅ |
| GET /v1/projects | 6 ms | 27 ms | 110 ms | 5.0 | 401 ¹ |
| GET /v1/signal-score/[id] | 7 ms | 25 ms | 91 ms | 3.0 | 401 ¹ |
| GET /v1/risk/[id] | 8 ms | 31 ms | 150 ms | 2.0 | 404 ² |
| GET /v1/portfolio | 7 ms | 28 ms | 120 ms | 2.1 | 401 ¹ |
| GET /v1/deal-flow | 7 ms | 25 ms | 81 ms | 3.2 | 404 ² |
| GET /v1/reports | 6 ms | 24 ms | 120 ms | 2.0 | 401 ¹ |
| GET /v1/valuation/[id] | 7 ms | 20 ms | 120 ms | 0.9 | 404 ² |
| GET /v1/watchlists | 13 ms | 53 ms | 550 ms | 1.0 | 401 ¹ |
| **Aggregated (all endpoints)** | **8 ms** | **32 ms** | **130 ms** | **24.5** | — |

¹ 401 Unauthorized — no `LOAD_TEST_JWT` set. Middleware latency only.
² 404 Not Found — locustfile URL path does not match registered route prefix. Update `locustfile.py` with correct paths and re-run with auth.

---

## AI Endpoint Latency (10 concurrent users)

> Requires `LOAD_TEST_JWT`. Re-run `test_ai_latency.py` against staging
> after setting credentials. AI endpoints depend on Anthropic API latency
> and are expected to be 2–15 s for full generation.

| Endpoint | p50 | p95 | p99 | Notes |
|----------|-----|-----|-----|-------|
| POST /v1/ralph/conversations | — | — | — | Requires auth + live Anthropic API |
| POST /v1/ralph/[id]/message | — | — | — | Requires auth + live Anthropic API |
| POST /v1/signal-score/[id]/calculate | — | — | — | Requires auth + Celery task |

---

## Data Room (local, 20 concurrent users, 3 min)

> All requests returned 401/404 (no auth). Latency = multipart parsing +
> routing + auth rejection. Upload numbers include client-side multipart
> assembly time. Real upload latency will include S3 transfer time.

| Operation | p50 | p95 | p99 | RPS |
|-----------|-----|-----|-----|-----|
| GET /v1/dataroom/[id]/documents (list) | **8 ms** | **13 ms** | **18 ms** | 1.47 |
| GET /v1/dataroom/[id]/documents?page=2 | **8 ms** | **13 ms** | **21 ms** | 0.81 |
| POST /v1/dataroom/[id]/documents (1 MB) | **8 ms** | **13 ms** | **25 ms** | 0.71 |
| POST /v1/dataroom/[id]/documents (5 MB) | **11 ms** | **19 ms** | **22 ms** | 0.29 |
| POST /v1/dataroom/[id]/documents (25 MB) | **25 ms** | **32 ms** | **34 ms** | 0.25 |
| GET /v1/deal-rooms/[id] | **6 ms** | **13 ms** | **33 ms** | 0.91 |
| GET /v1/deal-rooms | **13 ms** | **19 ms** | **26 ms** | 0.57 |
| **Aggregated** | **8 ms** | **24 ms** | **32 ms** | **5.0** |

> 25 MB upload p50 = 25 ms in local environment (routing overhead only).
> In staging with S3, expect 1–5 s depending on network.

---

## Concurrency Limits

| Metric | Value | Notes |
|--------|-------|-------|
| Max concurrent users before p95 > 1 s (health endpoint) | **> 50** | p95 stayed at 27 ms under 50 users — limit not reached |
| Max concurrent users before error rate > 1 % (health) | **> 50** | 0% error rate at 50 users |
| Max RPS sustained at p95 < 500 ms (`/health`) | **~28 RPS** | Local, single worker. Multiply by worker count for production estimate. |
| Rate limiter trigger threshold | **~300 req/min per IP** | Observed at 50 users hitting same IP |

> Full concurrency limit test (ramp to 200+ users until degradation) not yet
> run. Run `locust --users=200 --spawn-rate=10 --run-time=5m` against staging
> with auth to find the real inflection point.

---

## Staging Health Check (cold start, 2 min)

Staging was tested in the same session. ECS tasks were cold-starting:

| Endpoint | p50 | p95 | p99 | Notes |
|----------|-----|-----|-----|-------|
| GET /health (staging) | 9,100 ms | 12,000 ms | 13,000 ms | Cold start — tasks spinning up |
| GET /v1/projects (staging, 401) | 3,700 ms | 4,900 ms | 5,600 ms | Cold start |

Re-run against staging **after sustained warm traffic** for production-representative numbers.
ECS `healthCheckGracePeriodSeconds=120` is configured; allow 2–3 min of traffic before benchmarking.

---

## Recommendations

1. **Set `LOAD_TEST_JWT` and re-run against staging** (warmed, not cold-start) — this is the only measurement that counts for production capacity planning.
2. **Fix locustfile.py endpoint paths** — `/v1/deal-flow`, `/v1/risk/[id]`, `/v1/valuation/[id]`, `/v1/dataroom/[id]/documents` returned 404. Correct paths and re-run.
3. **Run concurrency ramp test** — `--users=200 --spawn-rate=10` to find the actual p95 > 1s inflection point.
4. **Add p95 < 500 ms SLO alarm** to CloudWatch (Terraform) once baseline is established.

---

## How to Update This File

```bash
# 1. Set credentials
export LOAD_TEST_JWT="eyJ..."              # valid Clerk JWT for staging test user
export LOAD_TEST_PROJECT_ID="uuid..."     # project that exists in staging
export LOAD_TEST_DEAL_ROOM_ID="uuid..."   # deal room that exists in staging

# 2. Run tests
cd apps/api
poetry run locust -f tests/load/locustfile.py \
  --host=https://api.pampgroup.com \
  --users=50 --spawn-rate=5 --run-time=5m \
  --headless --csv=tests/load/results/general

# 3. Copy p50/p95/p99/RPS from tests/load/results/general_stats.csv
# 4. Commit: git commit -m "perf: update baseline $(date +%Y-%m-%d)"
```
