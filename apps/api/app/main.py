from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

import app.models
from app.auth.router import router as auth_router
from app.core.circuit_breaker import AIGatewayUnavailableError
from app.core.config import settings
from app.core.elasticsearch import close_es_client, setup_indices
from app.core.errors import (
    ai_gateway_unavailable_handler,
    global_exception_handler,
    http_exception_handler,
)
from app.core.logging import configure_logging
from app.core.sentry import init_sentry
from app.middleware.audit import AuditMiddleware
from app.middleware.correlation import CorrelationIdMiddleware
from app.middleware.security import (
    RateLimitMiddleware,
    RequestBodySizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.middleware.tenant import TenantMiddleware

# Configure structlog before any logger is used.
configure_logging("api")

# Module routers are auto-discovered — no manual imports needed here.
# To disable a module: add its label to app.core.module_discovery.DISABLED_MODULES
from app.core.module_discovery import discover_routers  # noqa: E402

# ── Sentry — must be initialised BEFORE FastAPI app is created ────────────────
init_sentry(settings.SENTRY_DSN, settings.SENTRY_ENVIRONMENT, settings.APP_VERSION)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    logger.info("Starting SCR API", env=settings.APP_ENV)
    await setup_indices()

    # Seed default feature flags
    from app.core.database import async_session_factory
    from app.modules.launch.service import seed_default_flags

    async with async_session_factory() as db:
        try:
            await seed_default_flags(db)
        except Exception as exc:
            logger.warning("feature_flag_seed_failed", error=str(exc))

    # ── Startup dependency validation ─────────────────────────────────────────
    import httpx

    checks: dict[str, str] = {}

    # Database check
    try:
        from sqlalchemy import text

        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"FAILED: {exc}"

    # Redis check
    try:
        import redis.asyncio as aioredis

        redis_url = (
            settings.REDIS_URL if hasattr(settings, "REDIS_URL") else "redis://localhost:6379/0"
        )
        r = aioredis.from_url(redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"FAILED: {exc}"

    # AI Gateway check (non-blocking)
    try:
        ai_gw_url = (
            settings.AI_GATEWAY_URL
            if hasattr(settings, "AI_GATEWAY_URL")
            else "http://localhost:8001"
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{ai_gw_url}/health")
            checks["ai_gateway"] = (
                "ok" if resp.status_code == 200 else f"WARNING: HTTP {resp.status_code}"
            )
    except Exception as exc:
        checks["ai_gateway"] = f"WARNING: {exc}"

    # Anthropic key check (non-blocking)
    anthropic_key = settings.ANTHROPIC_API_KEY if hasattr(settings, "ANTHROPIC_API_KEY") else ""
    checks["anthropic_key"] = "ok" if anthropic_key else "WARNING: ANTHROPIC_API_KEY not set"

    # Log all results
    for service, status in checks.items():
        if status.startswith("FAILED"):
            logger.error("startup_check_failed", service=service, detail=status)
        elif status.startswith("WARNING"):
            logger.warning("startup_check_warning", service=service, detail=status)
        else:
            logger.info("startup_check_passed", service=service)

    # Block on critical failures only
    critical = [
        k for k, v in checks.items() if v.startswith("FAILED") and k in ("database", "redis")
    ]
    if critical:
        raise RuntimeError(f"Critical startup dependencies unavailable: {', '.join(critical)}")

    yield
    logger.info("Shutting down SCR API")
    await close_es_client()


_is_prod = settings.APP_ENV == "production"

app = FastAPI(
    title="SCR Platform API",
    description="""
SCR Platform — investment intelligence for impact capital markets.

**Modules**: 77 auto-discovered feature modules across Deal Flow, Portfolio,
AI-powered analysis (Ralph AI), Signal Scoring, Risk, Legal, ESG, and more.

**Auth**: All endpoints require a valid Clerk JWT in the `Authorization: Bearer` header.

**Multi-tenancy**: All data is isolated by `org_id`. Requests from one organisation
cannot access another's data.

**Permissions**: RBAC with roles `admin > manager > analyst > viewer`.
""",
    version="0.1.0",
    # Disable interactive docs in production — use /openapi.json directly if needed
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
    lifespan=lifespan,
)

app.add_exception_handler(Exception, global_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(AIGatewayUnavailableError, ai_gateway_unavailable_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID", "X-Correlation-ID"],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Window",
        "X-Correlation-ID",
    ],
)
app.add_middleware(AuditMiddleware)
app.add_middleware(TenantMiddleware)
# Security + correlation middleware (added last = outermost = first to see requests)
app.add_middleware(
    RequestBodySizeLimitMiddleware,  # type: ignore[arg-type]
    max_bytes=settings.MAX_REQUEST_BODY_BYTES,
)
app.add_middleware(
    RateLimitMiddleware,  # type: ignore[arg-type]
    redis_url=settings.REDIS_URL,
    enabled=settings.RATE_LIMIT_ENABLED,
)
app.add_middleware(
    SecurityHeadersMiddleware,  # type: ignore[arg-type]
    is_production=_is_prod,
)
# CorrelationIdMiddleware is outermost: generates/reads the ID before rate
# limiting, auth, or any handler runs, so all logs carry the correlation_id.
app.add_middleware(CorrelationIdMiddleware)  # type: ignore[arg-type]


# ── X-API-Version response header ────────────────────────────────────────────


@app.middleware("http")
async def add_version_header(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-API-Version"] = "v1"
    return response


# ── Health check (root-level, not under /v1) ─────────────────────────────────


@app.get("/health")
async def health_check() -> dict:
    """Deep health check: probes PostgreSQL, Redis, Elasticsearch, and S3."""
    import asyncio

    checks: dict[str, dict] = {}

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    try:
        from sqlalchemy import text

        from app.core.database import async_session_factory

        async with async_session_factory() as db:
            await db.execute(text("SELECT 1"))
        checks["postgresql"] = {"status": "healthy"}
    except Exception as exc:
        logger.error(f"Health check failed for postgresql: {exc}")
        checks["postgresql"] = {"status": "unhealthy", "error": "connection_failed"}

    # ── Read replica lag ──────────────────────────────────────────────────────
    try:
        from app.core.database import _read_replica_url, get_cached_replica_lag

        if _read_replica_url:
            lag = await get_cached_replica_lag()
            if lag is None:
                checks["replica"] = {"status": "unknown", "lag_seconds": None}
            elif lag > 10:
                checks["replica"] = {"status": "degraded", "lag_seconds": round(lag, 1)}
            else:
                checks["replica"] = {"status": "healthy", "lag_seconds": round(lag, 1)}
        else:
            checks["replica"] = {"status": "not_configured"}
    except Exception as exc:
        logger.error(f"Health check failed for replica: {exc}")
        checks["replica"] = {"status": "unhealthy", "error": "connection_failed"}

    # ── Redis ─────────────────────────────────────────────────────────────────
    try:
        from redis.asyncio import from_url as redis_from_url

        r = redis_from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = {"status": "healthy"}
    except Exception as exc:
        logger.error(f"Health check failed for redis: {exc}")
        checks["redis"] = {"status": "unhealthy", "error": "connection_failed"}

    # ── Elasticsearch ─────────────────────────────────────────────────────────
    try:
        from app.core.elasticsearch import get_es_client

        es = get_es_client()
        if es is None:
            checks["elasticsearch"] = {"status": "not_configured"}
        else:
            info = await asyncio.wait_for(es.info(), timeout=3.0)
            checks["elasticsearch"] = {
                "status": "healthy",
                "version": info.get("version", {}).get("number", "unknown"),
            }
    except Exception as exc:
        logger.error(f"Health check failed for elasticsearch: {exc}")
        checks["elasticsearch"] = {"status": "unhealthy", "error": "connection_failed"}

    # ── S3 / MinIO ────────────────────────────────────────────────────────────
    try:
        import boto3
        from botocore.config import Config as BotoConfig

        s3 = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION,
            config=BotoConfig(connect_timeout=2, read_timeout=2, max_attempts=1),
        )
        s3.head_bucket(Bucket=settings.AWS_S3_BUCKET)
        checks["s3"] = {"status": "healthy"}
    except Exception as exc:
        logger.error(f"Health check failed for s3: {exc}")
        checks["s3"] = {"status": "unhealthy", "error": "connection_failed"}

    overall = "healthy" if all(c["status"] == "healthy" for c in checks.values()) else "degraded"
    return {"status": overall, "service": "scr-api", "checks": checks}


@app.get("/health/ai")
async def health_ai() -> dict:
    """Circuit-breaker status for the AI Gateway."""
    from app.core.circuit_breaker import ai_gateway_cb

    return await ai_gateway_cb.get_status()


# ── /v1 versioned router ──────────────────────────────────────────────────────

api_v1 = APIRouter(prefix="/v1")

# Auth router lives outside app/modules/ so it is registered manually.
api_v1.include_router(auth_router)

# Auto-discover and register all module routers.
# Each router already declares its own prefix and tags — no extra prefix added.
for _module_name, _router in discover_routers():
    api_v1.include_router(_router)

app.include_router(api_v1)
