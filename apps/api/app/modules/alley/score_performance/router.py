"""Alley Score Performance (Score Journey) API."""
from __future__ import annotations
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.alley.score_performance import service
from app.modules.alley.score_performance.schemas import (
    DimensionTrendsResponse,
    ScoreInsightsResponse,
    ScoreJourneyResponse,
    ScorePerformanceListResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/alley/score-performance", tags=["alley-score-performance"])


@router.get("", response_model=ScorePerformanceListResponse, summary="Score journey overview for all projects")
async def list_performance(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    items = await service.list_performance_summaries(db, current_user.org_id)
    return ScorePerformanceListResponse(items=items, total=len(items))


@router.get("/{project_id}", response_model=ScoreJourneyResponse, summary="Full score journey for one project")
async def get_journey(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_score_journey(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{project_id}/dimensions", response_model=DimensionTrendsResponse, summary="Per-dimension score trends")
async def get_dimension_trends(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_dimension_trends(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{project_id}/insights", response_model=ScoreInsightsResponse, summary="AI-generated improvement insights")
async def get_insights(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_score_insights(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
