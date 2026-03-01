"""Covenant & KPI Monitoring API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.monitoring.schemas import (
    CovenantCreate,
    CovenantResponse,
    CovenantSummary,
    CovenantUpdate,
    CovenantWaiveRequest,
    KPIActualCreate,
    KPIActualResponse,
    KPITargetCreate,
    KPITargetResponse,
    KPIVarianceItem,
    MonitoringDashboardItem,
)
from app.modules.monitoring.service import MonitoringService
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/monitoring", tags=["Covenant & KPI Monitoring"])


# ── Covenants ─────────────────────────────────────────────────────────────────


@router.post(
    "/covenants/{project_id}",
    response_model=CovenantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_covenant(
    project_id: uuid.UUID,
    body: CovenantCreate,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new covenant for a project."""
    svc = MonitoringService(db, current_user.org_id)
    covenant = await svc.create_covenant(project_id, body)
    return CovenantResponse.model_validate(covenant)


@router.get("/covenants/{project_id}", response_model=list[CovenantResponse])
async def list_covenants(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """List all active (non-waived) covenants for a project."""
    svc = MonitoringService(db, current_user.org_id)
    covenants = await svc.list_covenants(project_id)
    return [CovenantResponse.model_validate(c) for c in covenants]


@router.put("/covenants/{covenant_id}", response_model=CovenantResponse)
async def update_covenant(
    covenant_id: uuid.UUID,
    body: CovenantUpdate,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Update a covenant's name, threshold, status, or check frequency."""
    svc = MonitoringService(db, current_user.org_id)
    try:
        covenant = await svc.update_covenant(covenant_id, body)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return CovenantResponse.model_validate(covenant)


@router.post(
    "/covenants/{covenant_id}/waive",
    response_model=CovenantResponse,
)
async def waive_covenant(
    covenant_id: uuid.UUID,
    body: CovenantWaiveRequest,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Waive a covenant breach with a documented reason."""
    svc = MonitoringService(db, current_user.org_id)
    try:
        covenant = await svc.waive_covenant(
            covenant_id, current_user.user_id, body.reason
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return CovenantResponse.model_validate(covenant)


@router.post("/covenants/check", response_model=list[dict])
async def check_covenants(
    project_id: uuid.UUID | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("admin", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Trigger covenant compliance check for the organisation (admin only).
    Returns a list of status changes detected."""
    svc = MonitoringService(db, current_user.org_id)
    return await svc.check_covenants(project_id=project_id)


# ── KPIs ──────────────────────────────────────────────────────────────────────


@router.post(
    "/kpis/{project_id}",
    response_model=KPIActualResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_kpi_actual(
    project_id: uuid.UUID,
    body: KPIActualCreate,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Record an actual KPI value for a project period."""
    svc = MonitoringService(db, current_user.org_id)
    actual = await svc.record_kpi_actual(
        project_id, body, entered_by=current_user.user_id
    )
    return KPIActualResponse.model_validate(actual)


@router.get("/kpis/{project_id}", response_model=list[KPIActualResponse])
async def list_kpi_actuals(
    project_id: uuid.UUID,
    period: str | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """List KPI actuals for a project, optionally filtered by period."""
    svc = MonitoringService(db, current_user.org_id)
    actuals = await svc.list_kpi_actuals(project_id, period=period)
    return [KPIActualResponse.model_validate(a) for a in actuals]


@router.post(
    "/kpis/{project_id}/targets",
    response_model=KPITargetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def set_kpi_target(
    project_id: uuid.UUID,
    body: KPITargetCreate,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Set a KPI target for a project period."""
    svc = MonitoringService(db, current_user.org_id)
    target = await svc.set_kpi_target(project_id, body)
    return KPITargetResponse.model_validate(target)


@router.get(
    "/kpis/{project_id}/variance",
    response_model=list[KPIVarianceItem],
)
async def get_kpi_variance(
    project_id: uuid.UUID,
    period: str | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get KPI variance (actual vs target) for a project, optionally filtered by period."""
    svc = MonitoringService(db, current_user.org_id)
    return await svc.get_kpi_variance(project_id, period=period)


@router.post("/kpis/extract/{document_id}", response_model=dict)
async def auto_extract_kpis(
    document_id: uuid.UUID,
    project_id: uuid.UUID = Query(...),
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Use AI to auto-extract KPIs from an uploaded document."""
    svc = MonitoringService(db, current_user.org_id)
    return await svc.auto_extract_kpis(document_id, project_id)


# ── Dashboard & Trends ────────────────────────────────────────────────────────


@router.get(
    "/dashboard/{portfolio_id}",
    response_model=list[MonitoringDashboardItem],
)
async def get_portfolio_dashboard(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get covenant monitoring dashboard for all projects in a portfolio."""
    svc = MonitoringService(db, current_user.org_id)
    raw = await svc.get_portfolio_dashboard(portfolio_id)
    return [
        MonitoringDashboardItem(
            project_id=item["project_id"],
            project_name=item["project_name"],
            covenants=[
                CovenantSummary.model_validate(c) for c in item["covenants"]
            ],
            overall_status=item["overall_status"],
        )
        for item in raw
    ]


@router.get("/trends/{project_id}/{kpi_name}", response_model=list[dict])
async def get_kpi_trend(
    project_id: uuid.UUID,
    kpi_name: str,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get historical trend data for a specific KPI across all recorded periods."""
    svc = MonitoringService(db, current_user.org_id)
    return await svc.get_kpi_trend(project_id, kpi_name)
