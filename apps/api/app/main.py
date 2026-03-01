from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from app.core.elasticsearch import setup_indices, close_es_client

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    logger.info("Starting SCR API", env=settings.APP_ENV)
    await setup_indices()
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

# Routers
app.include_router(auth_router)
app.include_router(dataroom_router)
app.include_router(projects_router)
app.include_router(portfolio_router)
app.include_router(onboarding_router)
app.include_router(reporting_router)
app.include_router(collaboration_router)
app.include_router(notifications_router)
app.include_router(signal_score_router)
app.include_router(deal_intelligence_router)
app.include_router(risk_router)
app.include_router(matching_router)
app.include_router(settings_router)
app.include_router(impact_router)
app.include_router(valuation_router)
app.include_router(marketplace_router)
app.include_router(tax_credits_router)
app.include_router(legal_router)
app.include_router(carbon_credits_router)
app.include_router(board_advisor_router)
app.include_router(investor_personas_router)
app.include_router(equity_calculator_router)
app.include_router(capital_efficiency_router)
app.include_router(investor_signal_score_router)
app.include_router(value_quantifier_router)
app.include_router(tokenization_router)
app.include_router(development_os_router)
app.include_router(ecosystem_router)
app.include_router(ralph_ai_router)
app.include_router(admin_router)
app.include_router(admin_prompts_router)
app.include_router(search_router)
app.include_router(ai_feedback_router)
app.include_router(smart_screener_router)
app.include_router(risk_profile_router)
app.include_router(certification_router)
app.include_router(deal_flow_router)
app.include_router(due_diligence_router)
app.include_router(esg_router)
app.include_router(lp_reporting_router)
app.include_router(comps_router)
app.include_router(warm_intros_router)
app.include_router(doc_versions_router)
app.include_router(fx_router)
app.include_router(meeting_prep_router)
app.include_router(compliance_router)
app.include_router(stress_test_router)
app.include_router(connectors_router)
app.include_router(deal_rooms_router)
app.include_router(watchlists_router)
app.include_router(blockchain_audit_router)
app.include_router(voice_input_router)
app.include_router(gamification_router)
app.include_router(insurance_router)
app.include_router(digest_router)
app.include_router(metrics_router)
app.include_router(citations_router)
app.include_router(lineage_router)
app.include_router(qa_workflow_router)
app.include_router(engagement_router)
app.include_router(monitoring_router)
app.include_router(excel_api_router)
app.include_router(crm_sync_router)
app.include_router(pacing_router)
app.include_router(taxonomy_router)
app.include_router(financial_templates_router)
app.include_router(business_plans_router)
app.include_router(backtesting_router)
app.include_router(expert_insights_router)
app.include_router(webhooks_router)
app.include_router(document_annotations_router)
app.include_router(redaction_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "scr-api"}
