from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

import app.models  # noqa: F401 — register all models at startup

from app.auth.router import router as auth_router
from app.middleware.audit import AuditMiddleware
from app.middleware.tenant import TenantMiddleware
from app.modules.dataroom.router import router as dataroom_router
from app.modules.portfolio.router import router as portfolio_router
from app.modules.onboarding.router import router as onboarding_router
from app.modules.projects.router import router as projects_router
from app.modules.reporting.router import router as reporting_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    logger.info("Starting SCR API", env=settings.APP_ENV)
    yield
    logger.info("Shutting down SCR API")


app = FastAPI(
    title="SCR Platform API",
    description="Investment intelligence platform connecting impact project developers with investors.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)
app.add_middleware(TenantMiddleware)

# Routers
app.include_router(auth_router)
app.include_router(dataroom_router)
app.include_router(projects_router)
app.include_router(portfolio_router)
app.include_router(onboarding_router)
app.include_router(reporting_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "scr-api"}
