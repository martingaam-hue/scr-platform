"""AI Gateway — unified LLM access with routing, rate limiting, and RAG."""
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import sentry_sdk
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration

from app.core.config import settings
from app.routers import completions, embeddings, search, feeds

logger = structlog.get_logger()

# ── Sentry — initialise before FastAPI app is created ────────────────────────
_sentry_dsn = getattr(settings, "SENTRY_DSN", None)
if _sentry_dsn:
    _env = getattr(settings, "SENTRY_ENVIRONMENT", "development")
    _is_prod = _env == "production"
    sentry_sdk.init(
        dsn=_sentry_dsn,
        environment=_env,
        traces_sample_rate=0.1 if _is_prod else 1.0,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            HttpxIntegration(),
        ],
        send_default_pii=False,
    )
    logger.info("sentry_initialized", service="ai-gateway", environment=_env)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    logger.info("Starting AI Gateway", env=settings.APP_ENV, port=settings.PORT)
    # Warm up vector store singleton
    from app.services.vector_store import vector_store as vs
    vs()
    logger.info("Vector store initialized", backend=settings.VECTOR_STORE_BACKEND)
    yield
    logger.info("Shutting down AI Gateway")


app = FastAPI(
    title="SCR AI Gateway",
    description=(
        "Unified AI/LLM access gateway with model routing, rate limiting, "
        "cost tracking, vector search, and RAG pipeline."
    ),
    version="2.0.0",
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

# Mount all routers under /v1
app.include_router(completions.router, prefix="/v1", tags=["completions"])
app.include_router(embeddings.router, prefix="/v1", tags=["embeddings"])
app.include_router(search.router, prefix="/v1", tags=["search"])
app.include_router(feeds.router, prefix="/v1", tags=["feeds"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "ai-gateway", "version": "2.0.0"}


@app.get("/v1/models")
async def list_models() -> dict:
    """List all supported task types and their assigned models."""
    from app.routers.completions import MODEL_ROUTING
    return {"task_type_routing": MODEL_ROUTING, "total": len(MODEL_ROUTING)}
