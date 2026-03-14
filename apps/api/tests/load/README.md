# Load Tests

Locust-based load tests for the SCR Platform API.

## Files

| File | Purpose | Concurrency |
|------|---------|-------------|
| `locustfile.py` | General user journey (read-heavy) | 50 users |
| `test_ai_latency.py` | AI endpoint latency (Ralph, Signal Score) | 10 users |
| `test_data_room.py` | Data room uploads / downloads / listing | 20 users |

## Prerequisites

```bash
cd apps/api
poetry install --with dev  # locust is in the dev group
```

Set environment variables for the test user's JWT and fixture IDs:

```bash
export LOAD_TEST_JWT="eyJ..."          # valid Clerk JWT for a staging test user
export LOAD_TEST_PROJECT_ID="uuid..."  # project that exists in staging
export LOAD_TEST_DEAL_ROOM_ID="uuid..." # deal room that exists in staging
```

## Running

### Interactive UI
```bash
poetry run locust -f tests/load/locustfile.py --host=https://api.pampgroup.com
# Open http://localhost:8089
```

### Headless (CI / baseline capture)
```bash
# General baseline — 50 users, 5/s ramp, 5 minutes
poetry run locust -f tests/load/locustfile.py \
  --host=https://api.pampgroup.com \
  --users=50 --spawn-rate=5 --run-time=5m \
  --headless --csv=tests/load/results/baseline

# AI latency — 10 users, 1/s ramp, 5 minutes
poetry run locust -f tests/load/test_ai_latency.py \
  --host=https://api.pampgroup.com \
  --users=10 --spawn-rate=1 --run-time=5m \
  --headless --csv=tests/load/results/ai_latency

# Data room — 20 users, 2/s ramp, 5 minutes
poetry run locust -f tests/load/test_data_room.py \
  --host=https://api.pampgroup.com \
  --users=20 --spawn-rate=2 --run-time=5m \
  --headless --csv=tests/load/results/data_room
```

## Results

CSV output lands in `tests/load/results/` (gitignored). The `*_stats.csv`
file contains per-endpoint p50/p95/p99 latency and RPS — copy the numbers
into `PERFORMANCE.md` after each baseline run.
