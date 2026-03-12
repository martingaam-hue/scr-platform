#!/bin/bash
set -e
echo "=== API Lint ==="
cd apps/api && poetry run ruff check . && poetry run ruff format --check .
echo "=== API Types ==="
poetry run mypy .
cd ../..
echo "=== Web Lint ==="
cd apps/web && pnpm exec eslint .
echo "=== Web Types ==="
pnpm exec tsc --noEmit
cd ../..
echo "All checks passed"
