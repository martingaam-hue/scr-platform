"""Risk Analysis & Compliance API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.risk import service
from app.modules.risk.schemas import (
    AuditTrailResponse,
    ComplianceStatusResponse,
    ConcentrationAnalysisResponse,
    RiskAssessmentCreate,
    RiskAssessmentResponse,
    RiskDashboardResponse,
    ScenarioRequest,
    ScenarioResult,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/dashboard/{portfolio_id}", response_model=RiskDashboardResponse)
async def get_risk_dashboard(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    """Risk dashboard: heatmap, top risks, auto-identification, concentration."""
    try:
        return await service.get_risk_dashboard(db, portfolio_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/assess",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_risk_assessment(
    body: RiskAssessmentCreate,
    current_user: CurrentUser = Depends(require_permission("create", "risk")),
    db: AsyncSession = Depends(get_db),
):
    """Create or log a risk assessment for a portfolio/holding/project."""
    try:
        assessment = await service.create_risk_assessment(
            db, current_user.org_id, current_user.user_id, body
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return service._assessment_to_response(assessment)


@router.get("/assessments", response_model=list[RiskAssessmentResponse])
async def list_risk_assessments(
    entity_type: str | None = Query(None),
    entity_id: uuid.UUID | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    """List risk assessments filtered by entity."""
    assessments = await service.get_risk_assessments(
        db, current_user.org_id, entity_type, entity_id
    )
    return [service._assessment_to_response(a) for a in assessments]


@router.post("/scenarios/{portfolio_id}", response_model=ScenarioResult)
async def run_scenario(
    portfolio_id: uuid.UUID,
    body: ScenarioRequest,
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    """Run a scenario stress-test against a portfolio."""
    try:
        return await service.run_scenario_analysis(
            db, portfolio_id, current_user.org_id, body.scenario_type, body.parameters
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/concentration/{portfolio_id}", response_model=ConcentrationAnalysisResponse)
async def get_concentration(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    """Concentration analysis by sector, geography, counterparty, currency."""
    try:
        return await service.get_concentration_analysis(
            db, portfolio_id, current_user.org_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/compliance/{portfolio_id}", response_model=ComplianceStatusResponse)
async def get_compliance(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    """SFDR / EU Taxonomy compliance status for a portfolio."""
    try:
        return await service.get_compliance_status(
            db, portfolio_id, current_user.org_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/audit-trail", response_model=AuditTrailResponse)
async def get_audit_trail(
    entity_type: str | None = Query(None),
    entity_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    """Filterable audit trail of all entity changes."""
    return await service.get_audit_trail(
        db, current_user.org_id, entity_type, entity_id, page, page_size
    )
