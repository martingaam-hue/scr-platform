"""Score Backtesting API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.backtesting.schemas import (
    BacktestRunRequest,
    BacktestRunResponse,
    BacktestSummaryResponse,
    DealOutcomeResponse,
    RecordOutcomeRequest,
)
from app.modules.backtesting.service import BacktestService
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/backtesting", tags=["backtesting"])


@router.post(
    "/outcomes",
    response_model=DealOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_outcome(
    body: RecordOutcomeRequest,
    current_user: CurrentUser = Depends(require_permission("create", "analysis")),
    db: AsyncSession = Depends(get_db),
) -> DealOutcomeResponse:
    """Record a deal outcome for use in backtesting."""
    svc = BacktestService(db)
    outcome = await svc.record_outcome(current_user.org_id, body)
    return DealOutcomeResponse.model_validate(outcome)


@router.get(
    "/outcomes",
    response_model=list[DealOutcomeResponse],
)
async def list_outcomes(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DealOutcomeResponse]:
    """List all recorded deal outcomes for the organisation."""
    svc = BacktestService(db)
    outcomes = await svc.list_outcomes(current_user.org_id)
    return [DealOutcomeResponse.model_validate(o) for o in outcomes]


@router.post(
    "/runs",
    response_model=BacktestRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_backtest(
    body: BacktestRunRequest,
    current_user: CurrentUser = Depends(require_permission("create", "analysis")),
    db: AsyncSession = Depends(get_db),
) -> BacktestRunResponse:
    """Execute a backtesting run over historical deal outcomes."""
    svc = BacktestService(db)
    run = await svc.run_backtest(current_user.org_id, current_user.user_id, body)
    return BacktestRunResponse.model_validate(run)


@router.get(
    "/runs",
    response_model=list[BacktestRunResponse],
)
async def list_backtest_runs(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BacktestRunResponse]:
    """List all backtest runs for the organisation."""
    svc = BacktestService(db)
    runs = await svc.list_runs(current_user.org_id)
    return [BacktestRunResponse.model_validate(r) for r in runs]


@router.get(
    "/runs/{run_id}",
    response_model=BacktestRunResponse,
)
async def get_backtest_run(
    run_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestRunResponse:
    """Get a single backtest run with full results."""
    svc = BacktestService(db)
    run = await svc.get_run(current_user.org_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return BacktestRunResponse.model_validate(run)


@router.get(
    "/summary",
    response_model=BacktestSummaryResponse,
)
async def get_summary(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestSummaryResponse:
    """Get org-level backtesting summary statistics."""
    svc = BacktestService(db)
    return await svc.get_summary(current_user.org_id)
