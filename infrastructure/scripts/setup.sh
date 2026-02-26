#!/usr/bin/env bash
set -euo pipefail

echo "================================================"
echo "  SCR Platform — Local Development Setup"
echo "================================================"
echo ""

# Check prerequisites
command -v node >/dev/null 2>&1 || { echo "Error: Node.js is required (>= 20). Install from https://nodejs.org"; exit 1; }
command -v pnpm >/dev/null 2>&1 || { echo "Error: pnpm is required (>= 9). Run: npm install -g pnpm"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Error: Python 3.12+ is required. Install from https://python.org"; exit 1; }
command -v poetry >/dev/null 2>&1 || { echo "Error: Poetry is required. Run: pip install poetry"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Error: Docker is required. Install from https://docker.com"; exit 1; }

echo "All prerequisites found."
echo ""

# Copy env file if missing
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit it with your API keys."
else
  echo ".env already exists, skipping."
fi

# Start infrastructure
echo ""
echo "Starting Docker services (PostgreSQL, Redis, ElasticSearch, MinIO)..."
docker compose up -d

# Install frontend dependencies
echo ""
echo "Installing Node.js dependencies..."
pnpm install

# Install API dependencies
echo ""
echo "Installing Python API dependencies..."
cd apps/api && poetry install && cd ../..

# Install AI Gateway dependencies
echo ""
echo "Installing AI Gateway dependencies..."
cd services/ai-gateway && poetry install && cd ../..

echo ""
echo "================================================"
echo "  Setup complete!"
echo ""
echo "  Start developing:"
echo "    make start         # Start all services"
echo "    make dev           # Or use Turborepo"
echo ""
echo "  Services:"
echo "    Frontend:       http://localhost:3000"
echo "    API:            http://localhost:8000"
echo "    API Docs:       http://localhost:8000/docs"
echo "    AI Gateway:     http://localhost:8001"
echo "    MinIO Console:  http://localhost:9001"
echo "    MailHog:        http://localhost:8025"
echo "================================================"
