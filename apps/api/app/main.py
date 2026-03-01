from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.core.config import settings
from app.middleware.security import (
    RateLimitMiddleware,
    RequestBodySizeLimitMiddleware,
    SecurityHeadersMiddleware,
)

import app.models  # noqa: F401 — register all models at startup

from app.auth.router import router as auth_router
from app.middleware.audit import AuditMiddleware
from app.middleware.tenant import TenantMiddleware
from app.modules.dataroom.router import router as dataroom_router
from app.modules.portfolio.router import router as portfolio_router
from app.modules.onboarding.router import router as onboarding_router
from app.modules.projects.router import router as projects_router
from app.modules.reporting.router import router as reporting_router
from app.modules.collaboration.router import router as collaboration_router
from app.modules.notifications.router import router as notifications_router
from app.modules.signal_score.router import router as signal_score_router
from app.modules.deal_intelligence.router import router as deal_intelligence_router
from app.modules.risk.router import router as risk_router
from app.modules.matching.router import router as matching_router
from app.modules.settings.router import router as settings_router
from app.modules.impact.router import router as impact_router
from app.modules.valuation.router import router as valuation_router
from app.modules.marketplace.router import router as marketplace_router
from app.modules.tax_credits.router import router as tax_credits_router
from app.modules.legal.router import router as legal_router
from app.modules.carbon_credits.router import router as carbon_credits_router
from app.modules.board_advisor.router import router as board_advisor_router
from app.modules.investor_personas.router import router as investor_personas_router
from app.modules.equity_calculator.router import router as equity_calculator_router
from app.modules.capital_efficiency.router import router as capital_efficiency_router
from app.modules.investor_signal_score.router import router as investor_signal_score_router
from app.modules.value_quantifier.router import router as value_quantifier_router
from app.modules.tokenization.router import router as tokenization_router
from app.modules.development_os.router import router as development_os_router
from app.modules.ecosystem.router import router as ecosystem_router
from app.modules.ralph_ai.router import router as ralph_ai_router
from app.modules.admin.router import router as admin_router
from app.modules.admin.prompts.router import router as admin_prompts_router
from app.modules.search.router import router as search_router
from app.modules.ai_feedback.router import router as ai_feedback_router
from app.modules.smart_screener.router import router as smart_screener_router
from app.modules.risk_profile.router import router as risk_profile_router
from app.modules.certification.router import router as certification_router
from app.modules.deal_flow.router import router as deal_flow_router
from app.modules.due_diligence.router import router as due_diligence_router
from app.modules.esg.router import router as esg_router
from app.modules.lp_reporting.router import router as lp_reporting_router
from app.modules.comps.router import router as comps_router
from app.modules.warm_intros.router import router as warm_intros_router
from app.modules.doc_versions.router import router as doc_versions_router
from app.modules.fx.router import router as fx_router
from app.modules.meeting_prep.router import router as meeting_prep_router
from app.modules.compliance.router import router as compliance_router
from app.modules.stress_test.router import router as stress_test_router
from app.modules.connectors.router import router as connectors_router
from app.modules.deal_rooms.router import router as deal_rooms_router
from app.modules.watchlists.router import router as watchlists_router
from app.modules.blockchain_audit.router import router as blockchain_audit_router
from app.modules.voice_input.router import router as voice_input_router
from app.modules.gamification.router import router as gamification_router
from app.modules.insurance.router import router as insurance_router
from app.modules.digest.router import router as digest_router
from app.modules.metrics.router import router as metrics_router
from app.modules.citations.router import router as citations_router
from app.modules.lineage.router import router as lineage_router
from app.modules.qa_workflow.router import router as qa_workflow_router
from app.modules.engagement.router import router as engagement_router
from app.modules.monitoring.router import router as monitoring_router
from app.modules.excel_api.router import router as excel_api_router
from app.modules.crm_sync.router import router as crm_sync_router
from app.modules.pacing.router import router as pacing_router
from app.modules.taxonomy.router import router as taxonomy_router
from app.modules.financial_templates.router import router as financial_templates_router
from app.modules.business_plans.router import router as business_plans_router
from app.modules.backtesting.router import router as backtesting_router
from app.modules.expert_insights.router import router as expert_insights_router
from app.modules.webhooks.router import router as webhooks_router
from app.modules.document_annotations.router import router as document_annotations_router
from app.modules.redaction.router import router as redaction_router
from app.modules.market_data.router import router as market_data_router
from app.modules.launch.router import router as launch_router
from app.modules.custom_domain.router import router as custom_domain_router
from app.core.elasticsearch import setup_indices, close_es_client
from app.core.sentry import init_sentry

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
        except Exception as exc:  # noqa: BLE001
            logger.warning("feature_flag_seed_failed", error=str(exc))

    yield
    logger.info("Shutting down SCR API")
    await close_es_client()


_is_prod = settings.APP_ENV == "production"

app = FastAPI(
    title="SCR Platform API",
    description="Investment intelligence platform connecting impact project developers with investors.",
    version="0.1.0",
    # Disable interactive docs in production — use /openapi.json directly if needed
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Window"],
)
app.add_middleware(AuditMiddleware)
app.add_middleware(TenantMiddleware)
# Security middleware (added last = outermost = first to see requests, last to touch responses)
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
        checks["postgresql"] = {"status": "unhealthy", "error": str(exc)}

    # ── Redis ─────────────────────────────────────────────────────────────────
    try:
        from redis.asyncio import from_url as redis_from_url
        r = redis_from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = {"status": "healthy"}
    except Exception as exc:
        checks["redis"] = {"status": "unhealthy", "error": str(exc)}

    # ── Elasticsearch ─────────────────────────────────────────────────────────
    try:
        from app.core.elasticsearch import get_es_client
        es = get_es_client()
        info = await asyncio.wait_for(es.info(), timeout=3.0)
        checks["elasticsearch"] = {
            "status": "healthy",
            "version": info.get("version", {}).get("number", "unknown"),
        }
    except Exception as exc:
        checks["elasticsearch"] = {"status": "unhealthy", "error": str(exc)}

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
            config=BotoConfig(connect_timeout=2, read_timeout=2),
        )
        s3.head_bucket(Bucket=settings.AWS_S3_BUCKET)
        checks["s3"] = {"status": "healthy"}
    except Exception as exc:
        checks["s3"] = {"status": "unhealthy", "error": str(exc)}

    overall = (
        "healthy"
        if all(c["status"] == "healthy" for c in checks.values())
        else "degraded"
    )
    return {"status": overall, "service": "scr-api", "checks": checks}


# ── /v1 versioned router ──────────────────────────────────────────────────────

api_v1 = APIRouter(prefix="/v1")

api_v1.include_router(auth_router)
api_v1.include_router(dataroom_router)
api_v1.include_router(projects_router)
api_v1.include_router(portfolio_router)
api_v1.include_router(onboarding_router)
api_v1.include_router(reporting_router)
api_v1.include_router(collaboration_router)
api_v1.include_router(notifications_router)
api_v1.include_router(signal_score_router)
api_v1.include_router(deal_intelligence_router)
api_v1.include_router(risk_router)
api_v1.include_router(matching_router)
api_v1.include_router(settings_router)
api_v1.include_router(impact_router)
api_v1.include_router(valuation_router)
api_v1.include_router(marketplace_router)
api_v1.include_router(tax_credits_router)
api_v1.include_router(legal_router)
api_v1.include_router(carbon_credits_router)
api_v1.include_router(board_advisor_router)
api_v1.include_router(investor_personas_router)
api_v1.include_router(equity_calculator_router)
api_v1.include_router(capital_efficiency_router)
api_v1.include_router(investor_signal_score_router)
api_v1.include_router(value_quantifier_router)
api_v1.include_router(tokenization_router)
api_v1.include_router(development_os_router)
api_v1.include_router(ecosystem_router)
api_v1.include_router(ralph_ai_router)
api_v1.include_router(admin_router)
api_v1.include_router(admin_prompts_router)
api_v1.include_router(search_router)
api_v1.include_router(ai_feedback_router)
api_v1.include_router(smart_screener_router)
api_v1.include_router(risk_profile_router)
api_v1.include_router(certification_router)
api_v1.include_router(deal_flow_router)
api_v1.include_router(due_diligence_router)
api_v1.include_router(esg_router)
api_v1.include_router(lp_reporting_router)
api_v1.include_router(comps_router)
api_v1.include_router(warm_intros_router)
api_v1.include_router(doc_versions_router)
api_v1.include_router(fx_router)
api_v1.include_router(meeting_prep_router)
api_v1.include_router(compliance_router)
api_v1.include_router(stress_test_router)
api_v1.include_router(connectors_router)
api_v1.include_router(deal_rooms_router)
api_v1.include_router(watchlists_router)
api_v1.include_router(blockchain_audit_router)
api_v1.include_router(voice_input_router)
api_v1.include_router(gamification_router)
api_v1.include_router(insurance_router)
api_v1.include_router(digest_router)
api_v1.include_router(metrics_router)
api_v1.include_router(citations_router)
api_v1.include_router(lineage_router)
api_v1.include_router(qa_workflow_router)
api_v1.include_router(engagement_router)
api_v1.include_router(monitoring_router)
api_v1.include_router(excel_api_router)
api_v1.include_router(crm_sync_router)
api_v1.include_router(pacing_router)
api_v1.include_router(taxonomy_router)
api_v1.include_router(financial_templates_router)
api_v1.include_router(business_plans_router)
api_v1.include_router(backtesting_router)
api_v1.include_router(expert_insights_router)
api_v1.include_router(webhooks_router)
api_v1.include_router(document_annotations_router)
api_v1.include_router(redaction_router)
api_v1.include_router(market_data_router)
api_v1.include_router(launch_router)
api_v1.include_router(custom_domain_router)

app.include_router(api_v1)
