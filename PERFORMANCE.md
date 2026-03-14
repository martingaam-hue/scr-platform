# SCR Platform — Performance Baseline

**Date:** March 2026
**Environment:** Staging (ECS Fargate, eu-north-1)
**Tool:** Locust 2.x
**Load:** 50 concurrent users, 5 users/s ramp-up, 5-minute run

> Results below are placeholders. Run the load tests against staging and fill in actual numbers.
> See `apps/api/tests/load/README.md` for instructions.

## API Response Times — General Endpoints

| Endpoint                         | p50  | p95  | p99  | RPS |
|----------------------------------|------|------|------|-----|
| GET /health                      | —    | —    | —    | —   |
| GET /v1/projects                 | —    | —    | —    | —   |
| GET /v1/signal-score/[id]        | —    | —    | —    | —   |
| GET /v1/risk/[id]                | —    | —    | —    | —   |
| GET /v1/portfolio                | —    | —    | —    | —   |
| GET /v1/deal-flow                | —    | —    | —    | —   |
| GET /v1/reports                  | —    | —    | —    | —   |
| GET /v1/valuation/[id]           | —    | —    | —    | —   |

## AI Endpoint Latency (10 concurrent users)

| Endpoint                                  | p50  | p95  | p99  |
|-------------------------------------------|------|------|------|
| POST /v1/ralph/conversations              | —    | —    | —    |
| POST /v1/ralph/[id]/message               | —    | —    | —    |
| POST /v1/signal-score/[id]/calculate      | —    | —    | —    |

## Data Room (20 concurrent users)

| Operation                                 | p50  | p95  | p99  | RPS |
|-------------------------------------------|------|------|------|-----|
| GET /v1/dataroom/[id]/documents (list)    | —    | —    | —    | —   |
| POST /v1/dataroom/[id]/documents (1 MB)   | —    | —    | —    | —   |
| POST /v1/dataroom/[id]/documents (5 MB)   | —    | —    | —    | —   |
| POST /v1/dataroom/[id]/documents (25 MB)  | —    | —    | —    | —   |
| GET /v1/deal-rooms/[id]                   | —    | —    | —    | —   |

## Concurrency Limits

| Metric                                         | Value |
|------------------------------------------------|-------|
| Max concurrent users before p95 > 1 s          | —     |
| Max concurrent users before error rate > 1 %   | —     |
| Sustained RPS at p95 < 500 ms                  | —     |

## Recommendations

> Fill in after running baseline tests.

---

## How to Update This File

1. Run the baseline tests (see `apps/api/tests/load/README.md`)
2. Open `tests/load/results/baseline_stats.csv`
3. Copy p50 / p95 / p99 / RPS columns into the tables above
4. Commit with `git commit -m "perf: update baseline YYYY-MM-DD"`
