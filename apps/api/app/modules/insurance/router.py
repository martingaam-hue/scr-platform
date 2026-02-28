"""Insurance module API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.insurance import service
from app.modules.insurance.schemas import InsuranceImpactResponse, InsuranceSummaryResponse
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/insurance", tags=["insurance"])


@router.get(
    "/projects/{project_id}/impact",
    response_model=InsuranceImpactResponse,
)
async def get_insurance_impact(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Full AI-powered insurance impact analysis for a project.

    Returns recommended coverage types, estimated premium costs, risk reduction
    score, and financial impact on investor returns.
    """
    try:
        return await service.get_insurance_impact(db, current_user.org_id, project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/projects/{project_id}/summary",
    response_model=InsuranceSummaryResponse,
)
async def get_insurance_summary(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Lightweight insurance summary (no AI call — fast, for dashboard cards)."""
    try:
        return await service.get_insurance_summary(db, current_user.org_id, project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
