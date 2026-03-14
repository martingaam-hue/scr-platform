#!/bin/bash
set -e
echo "=== API Lint ==="
cd apps/api && poetry run ruff check . && poetry run ruff format --check .
echo "=== API Types ==="
poetry run mypy .
echo "=== Migration Check ==="
HEAD_COUNT=$(poetry run alembic heads 2>/dev/null | grep -c .)
if [ "$HEAD_COUNT" -ne 1 ]; then
  echo "❌ Multiple migration heads ($HEAD_COUNT heads)! Run: poetry run alembic merge heads -m 'merge heads'"
  poetry run alembic heads
  exit 1
fi
echo "✅ Single migration head"
poetry run alembic check || {
  echo "❌ Missing migrations for model changes! Run: poetry run alembic revision --autogenerate -m 'description'"
  exit 1
}
echo "✅ No missing migrations"
echo "=== API Tests ==="
poetry run pytest --tb=short -q
cd ../..
echo "=== Web Lint ==="
cd apps/web && pnpm exec eslint .
echo "=== Web Types ==="
pnpm exec tsc --noEmit
cd ../..
echo "All checks passed"
