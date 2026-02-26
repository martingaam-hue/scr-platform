from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import completions

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    logger.info("Starting AI Gateway", env=settings.APP_ENV)
    yield
    logger.info("Shutting down AI Gateway")


app = FastAPI(
    title="SCR AI Gateway",
    description="Unified AI/LLM access gateway with cost tracking and rate limiting.",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.API_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(completions.router, prefix="/v1", tags=["completions"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "ai-gateway"}
