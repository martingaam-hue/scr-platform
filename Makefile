.PHONY: help setup start stop reset db-migrate db-reset test lint

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## First-time setup (install dependencies)
	docker compose up -d
	cd apps/web && pnpm install
	cd apps/api && poetry install
	@echo ""
	@echo "✓ Setup complete. Run 'make start' to start development servers."

start: ## Start all services
	docker compose up -d
	@echo "Starting API server..."
	cd apps/api && poetry run uvicorn app.main:app --reload --port 8000 &
	@echo "Starting AI Gateway..."
	cd services/ai-gateway && poetry run uvicorn app.main:app --reload --port 8001 &
	@echo "Starting frontend..."
	cd apps/web && pnpm dev &
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  Frontend:       http://localhost:3000"
	@echo "  API:            http://localhost:8000"
	@echo "  API Docs:       http://localhost:8000/docs"
	@echo "  AI Gateway:     http://localhost:8001"
	@echo "  MinIO Console:  http://localhost:9001"
	@echo "  MailHog:        http://localhost:8025"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

stop: ## Stop all services
	docker compose down
	@pkill -f "uvicorn app.main:app" || true
	@pkill -f "next dev" || true
	@echo "All services stopped."

reset: ## Reset everything (WARNING: deletes all data)
	docker compose down -v
	@echo "All data deleted. Run 'make setup' to start fresh."

db-migrate: ## Run database migrations
	cd apps/api && poetry run alembic upgrade head

db-reset: ## Reset database (drop + recreate)
	docker compose down -v postgres_data
	docker compose up -d db
	sleep 3
	cd apps/api && poetry run alembic upgrade head
	@echo "Database reset complete."

test: ## Run all tests
	cd apps/api && poetry run pytest -v
	cd apps/web && pnpm test

lint: ## Lint all code
	cd apps/api && poetry run ruff check .
	cd apps/web && pnpm lint
