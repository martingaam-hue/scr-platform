"""Metrics API router — trend analysis, benchmarking, and score history."""

import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.metrics.benchmark_service import BenchmarkService
from app.modules.metrics.schemas import (
    BenchmarkAggregateResponse,
    BenchmarkComparison,
    ChangeEvent,
    PacingProjection,
    TrendPoint,
)
from app.modules.metrics.snapshot_service import MetricSnapshotService
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()
router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/trend/{entity_type}/{entity_id}/{metric_name}", response_model=list[TrendPoint])
async def get_trend(
    entity_type: str,
    entity_id: uuid.UUID,
    metric_name: str,
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get time series of a metric for trend charts."""
    svc = MetricSnapshotService(db)
    snapshots = await svc.get_trend(entity_type, entity_id, metric_name, from_date, to_date)
    return [
        TrendPoint(
            date=s.recorded_at.isoformat(),
            value=s.value,
            previous_value=s.previous_value,
            delta=round(s.value - s.previous_value, 2) if s.previous_value is not None else None,
            trigger_event=s.trigger_event,
        )
        for s in snapshots
    ]


@router.get("/changes/{entity_type}/{entity_id}/{metric_name}", response_model=list[ChangeEvent])
async def get_changes(
    entity_type: str,
    entity_id: uuid.UUID,
    metric_name: str,
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get change explanations for a metric with trigger events."""
    svc = MetricSnapshotService(db)
    changes = await svc.get_change_explanation(entity_type, entity_id, metric_name, from_date, to_date)
    return [
        ChangeEvent(
            date=c["date"],
            from_value=c["from"],
            to_value=c["to"],
            delta=c["delta"],
            trigger=c["trigger"],
            trigger_entity=c["trigger_entity"],
            metadata=c["metadata"],
        )
        for c in changes
    ]


@router.get("/rank/{entity_type}/{entity_id}/{metric_name}")
async def get_percentile_rank(
    entity_type: str,
    entity_id: uuid.UUID,
    metric_name: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get percentile rank of this entity vs all others for this metric."""
    svc = MetricSnapshotService(db)
    rank = await svc.get_percentile_rank(entity_type, entity_id, metric_name)
    if rank is None:
        return {"percentile": None, "message": "Insufficient data for ranking"}
    return {"entity_type": entity_type, "entity_id": str(entity_id), "metric_name": metric_name, "percentile": rank}


@router.get("/benchmark/compare/{project_id}")
async def compare_to_benchmark(
    project_id: uuid.UUID,
    metrics: Optional[str] = Query(None, description="Comma-separated metric names"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare a project to its peer group benchmark."""
    svc = BenchmarkService(db)
    metric_list = [m.strip() for m in metrics.split(",")] if metrics else None
    try:
        return await svc.compare_to_benchmark(project_id, current_user.org_id, metric_list)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/benchmark/list", response_model=list[BenchmarkAggregateResponse])
async def list_benchmarks(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all available benchmark aggregates."""
    svc = BenchmarkService(db)
    return await svc.list_benchmarks()


@router.post("/benchmark/compute")
async def compute_benchmarks(
    current_user: CurrentUser = Depends(require_permission("edit", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Admin trigger: recompute all benchmark aggregates."""
    svc = BenchmarkService(db)
    result = await svc.compute_benchmarks()
    return {"status": "complete", **result}


@router.post("/benchmark/import")
async def import_benchmarks(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permission("edit", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Upload CSV of external benchmark data (Preqin, Cambridge Associates)."""
    content = (await file.read()).decode("utf-8")
    svc = BenchmarkService(db)
    result = await svc.import_external_benchmarks(content, source=file.filename or "upload")
    return result


@router.get("/benchmark/pacing/{portfolio_id}", response_model=list[PacingProjection])
async def get_cashflow_pacing(
    portfolio_id: uuid.UUID,
    scenario: str = Query("base", pattern="^(base|optimistic|pessimistic)$"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get J-curve cashflow pacing projections for a portfolio."""
    svc = BenchmarkService(db)
    return await svc.get_cashflow_pacing(portfolio_id, current_user.org_id, scenario)


@router.get("/benchmark/quartile-chart/{project_id}")
async def get_quartile_chart(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get data for quartile position visualization across benchmark metrics."""
    svc = BenchmarkService(db)
    try:
        return await svc.get_quartile_chart_data(project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
