"""Alley Pipeline Analytics API."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.alley.analytics import service
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/alley/analytics", tags=["alley-analytics"])


@router.get("", summary="Pipeline overview stats")
async def get_overview(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_overview(db, current_user.org_id)


@router.get("/stage-distribution", summary="Projects by development stage")
async def stage_distribution(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_stage_distribution(db, current_user.org_id)


@router.get("/score-distribution", summary="Score histogram")
async def score_distribution(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_score_distribution(db, current_user.org_id)


@router.get("/risk-heatmap", summary="Risk heat map across all projects")
async def risk_heatmap(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_risk_heatmap(db, current_user.org_id)


@router.get("/document-completeness", summary="Document upload completeness per project")
async def document_completeness(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_document_completeness(db, current_user.org_id)


@router.get("/compare", summary="Side-by-side project comparison")
async def compare(
    project_ids: list[uuid.UUID] = Query(...),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    return await service.compare_projects(db, current_user.org_id, project_ids)
