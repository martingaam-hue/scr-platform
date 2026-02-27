"""Capital Efficiency API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.capital_efficiency import service
from app.modules.capital_efficiency.schemas import (
    BenchmarkResponse,
    EfficiencyBreakdownResponse,
    EfficiencyMetricsResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/capital-efficiency", tags=["capital-efficiency"])


@router.get("", response_model=EfficiencyMetricsResponse)
async def get_metrics(
    portfolio_id: uuid.UUID | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> EfficiencyMetricsResponse:
    """Get the most recent capital efficiency metrics for the org."""
    return await service.get_current_metrics(db, current_user.org_id, portfolio_id)


@router.get("/breakdown", response_model=EfficiencyBreakdownResponse)
async def get_breakdown(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> EfficiencyBreakdownResponse:
    """Get a categorised savings breakdown with vs-industry annotations."""
    return await service.get_breakdown(db, current_user.org_id)


@router.get("/benchmark", response_model=BenchmarkResponse)
async def get_benchmark(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> BenchmarkResponse:
    """Compare platform performance against industry averages."""
    return await service.get_benchmark(db, current_user.org_id)
