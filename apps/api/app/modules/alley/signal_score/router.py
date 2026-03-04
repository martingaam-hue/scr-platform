"""Alley Signal Score API — project holder view of their own project scores."""
from __future__ import annotations
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.alley.signal_score import service
from app.modules.alley.signal_score.schemas import (
    AlleyScoreListResponse,
    BenchmarkResponse,
    GapAnalysisResponse,
    ScoreHistoryResponse,
    SimulateRequest,
    SimulateResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/alley/signal-score", tags=["alley-signal-score"])


@router.get("", response_model=AlleyScoreListResponse, summary="List all project scores for my org")
async def list_my_scores(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    items = await service.list_scores(db, current_user.org_id)
    return AlleyScoreListResponse(items=items, total=len(items))


@router.get("/{project_id}/gaps", response_model=GapAnalysisResponse, summary="Gap analysis for my project")
async def get_gap_analysis(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_gap_analysis(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{project_id}/simulate", response_model=SimulateResponse, summary="Simulate score with criteria changes")
async def simulate_score(
    project_id: uuid.UUID,
    body: SimulateRequest,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.simulate_score(db, project_id, current_user.org_id, body.criteria_overrides)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{project_id}/history", response_model=ScoreHistoryResponse, summary="Score history timeline")
async def get_history(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_score_history(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{project_id}/benchmark", response_model=BenchmarkResponse, summary="Benchmark position vs peers")
async def get_benchmark(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_benchmark(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
