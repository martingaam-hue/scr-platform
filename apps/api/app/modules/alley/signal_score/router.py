"""Alley Signal Score API — project holder view of their own project scores."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.alley.signal_score import service
from app.modules.alley.signal_score.schemas import (
    BenchmarkResponse,
    GapAnalysisResponse,
    GenerateScoreResponse,
    PortfolioScoreResponse,
    ProjectScoreDetailResponse,
    ScoreHistoryResponse,
    SimulateRequest,
    SimulateResponse,
    TaskStatusResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/alley/signal-score", tags=["alley-signal-score"])


# ── New portfolio overview endpoint ────────────────────────────────────────────


@router.get(
    "",
    response_model=PortfolioScoreResponse,
    summary="Portfolio overview — all project scores, stats, and improvement guide",
)
async def get_portfolio_overview(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_portfolio_overview(db, current_user.org_id)


# ── Generate score (async) ─────────────────────────────────────────────────────


@router.post(
    "/generate",
    response_model=GenerateScoreResponse,
    summary="Trigger AI score generation for a project",
    status_code=202,
)
async def generate_score(
    project_id: uuid.UUID = Form(...),
    project_summary: str | None = Form(None),
    team_background: str | None = Form(None),
    project_documents: list[UploadFile] = File(default=[]),
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.trigger_generate(db, current_user.org_id, project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Task status — MUST be registered before /{project_id} ─────────────────────


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    summary="Poll async score generation task status",
)
async def get_task_status(
    task_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_task_status(db, task_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Project detail (consolidated) ─────────────────────────────────────────────


@router.get(
    "/{project_id}",
    response_model=ProjectScoreDetailResponse,
    summary="Consolidated project score detail",
)
async def get_project_detail(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_project_detail(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Legacy endpoints (kept for backward compatibility) ─────────────────────────


@router.get(
    "/{project_id}/gaps", response_model=GapAnalysisResponse, summary="Gap analysis for my project"
)
async def get_gap_analysis(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_gap_analysis(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{project_id}/simulate",
    response_model=SimulateResponse,
    summary="Simulate score with criteria changes",
)
async def simulate_score(
    project_id: uuid.UUID,
    body: SimulateRequest,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.simulate_score(
            db, project_id, current_user.org_id, body.criteria_overrides
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{project_id}/history", response_model=ScoreHistoryResponse, summary="Score history timeline"
)
async def get_history(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_score_history(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{project_id}/benchmark",
    response_model=BenchmarkResponse,
    summary="Benchmark position vs peers",
)
async def get_benchmark(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_benchmark(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
