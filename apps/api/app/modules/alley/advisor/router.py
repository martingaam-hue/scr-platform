"""Alley Development Advisor API."""
from __future__ import annotations
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.alley.advisor import service
from app.modules.alley.advisor.schemas import (
    AdvisorQueryRequest,
    AdvisorQueryResponse,
    FinancingReadinessResponse,
    MarketPositioningResponse,
    MilestonePlanResponse,
    RegulatoryGuidanceResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/alley/advisor", tags=["alley-advisor"])


@router.post("/{project_id}/query", response_model=AdvisorQueryResponse, summary="Ask Development Advisor a question")
async def query_advisor(
    project_id: uuid.UUID,
    body: AdvisorQueryRequest,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.query_advisor(db, project_id, current_user.org_id, body.question)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{project_id}/financing", response_model=FinancingReadinessResponse, summary="Financing readiness assessment")
async def financing_readiness(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_financing_readiness(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{project_id}/positioning", response_model=MarketPositioningResponse, summary="Market positioning analysis")
async def market_positioning(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_market_positioning(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{project_id}/milestones", response_model=MilestonePlanResponse, summary="Development milestone plan")
async def milestone_plan(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_milestone_plan(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{project_id}/regulatory", response_model=RegulatoryGuidanceResponse, summary="Regulatory guidance")
async def regulatory_guidance(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_regulatory_guidance(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
