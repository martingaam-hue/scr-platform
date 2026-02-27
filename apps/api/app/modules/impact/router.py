"""Impact measurement API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.impact import service
from app.modules.impact.schemas import (
    AdditionalityResponse,
    CarbonCreditCreateRequest,
    CarbonCreditListResponse,
    CarbonCreditResponse,
    CarbonCreditUpdateRequest,
    ImpactKPIUpdateRequest,
    PortfolioImpactResponse,
    ProjectImpactResponse,
    SDGMappingRequest,
    SDGSummary,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/impact", tags=["impact"])


# ── Portfolio-level impact ────────────────────────────────────────────────────


@router.get("/portfolio", response_model=PortfolioImpactResponse)
async def get_portfolio_impact(
    current_user: CurrentUser = Depends(require_permission("view", "impact")),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate impact metrics across all org projects."""
    return await service.get_portfolio_impact(db, current_user.org_id)


# ── Carbon credits ────────────────────────────────────────────────────────────


@router.get("/carbon-credits", response_model=CarbonCreditListResponse)
async def list_carbon_credits(
    project_id: uuid.UUID | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "impact")),
    db: AsyncSession = Depends(get_db),
):
    """List carbon credits for current org (optionally filtered by project)."""
    return await service.list_carbon_credits(db, current_user.org_id, project_id)


@router.post(
    "/carbon-credits",
    response_model=CarbonCreditResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_carbon_credit(
    body: CarbonCreditCreateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "impact")),
    db: AsyncSession = Depends(get_db),
):
    """Register a new carbon credit record."""
    try:
        cc = await service.create_carbon_credit(db, current_user.org_id, body)
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return service._credit_to_response(cc)


@router.put("/carbon-credits/{credit_id}", response_model=CarbonCreditResponse)
async def update_carbon_credit(
    credit_id: uuid.UUID,
    body: CarbonCreditUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "impact")),
    db: AsyncSession = Depends(get_db),
):
    """Update carbon credit details (e.g. verification status)."""
    try:
        cc = await service.update_carbon_credit(db, current_user.org_id, credit_id, body)
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return service._credit_to_response(cc)


# ── Per-project impact ────────────────────────────────────────────────────────


@router.get("/projects/{project_id}", response_model=ProjectImpactResponse)
async def get_project_impact(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "impact")),
    db: AsyncSession = Depends(get_db),
):
    """Get impact metrics and SDG mapping for a project."""
    try:
        return await service.get_project_impact(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/projects/{project_id}/kpis", response_model=ProjectImpactResponse)
async def update_kpis(
    project_id: uuid.UUID,
    body: ImpactKPIUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "impact")),
    db: AsyncSession = Depends(get_db),
):
    """Update impact KPI values for a project."""
    try:
        result = await service.update_impact_kpis(
            db, project_id, current_user.org_id, body.kpis
        )
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/projects/{project_id}/sdg", response_model=SDGSummary)
async def get_sdg_mapping(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "impact")),
    db: AsyncSession = Depends(get_db),
):
    """Get SDG goal mapping for a project."""
    try:
        return await service.get_sdg_summary(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/projects/{project_id}/sdg", response_model=SDGSummary)
async def update_sdg_mapping(
    project_id: uuid.UUID,
    body: SDGMappingRequest,
    current_user: CurrentUser = Depends(require_permission("create", "impact")),
    db: AsyncSession = Depends(get_db),
):
    """Update SDG goal mapping for a project."""
    try:
        result = await service.update_sdg_mapping(
            db, project_id, current_user.org_id, body
        )
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/projects/{project_id}/additionality", response_model=AdditionalityResponse
)
async def get_additionality(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "impact")),
    db: AsyncSession = Depends(get_db),
):
    """Compute additionality score for a project (deterministic)."""
    try:
        return await service.get_additionality(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
