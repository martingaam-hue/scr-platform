"""ESG Impact Dashboard API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.esg import service
from app.modules.esg.schemas import (
    ESGMetricsHistoryResponse,
    ESGMetricsResponse,
    ESGMetricsUpsertRequest,
    ESGPortfolioSummaryResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/esg", tags=["esg"])


# ── Portfolio summary ─────────────────────────────────────────────────────────


@router.get("/portfolio-summary", response_model=ESGPortfolioSummaryResponse)
async def get_portfolio_summary(
    portfolio_id: uuid.UUID | None = Query(None),
    period: str | None = Query(None, description='Filter by period, e.g. "2024-Q4"'),
    current_user: CurrentUser = Depends(require_permission("view", "impact")),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate ESG metrics across all projects in the org portfolio."""
    return await service.get_portfolio_esg_summary(
        db, current_user.org_id, portfolio_id=portfolio_id, period=period
    )


# ── Portfolio CSV export ──────────────────────────────────────────────────────


@router.get("/portfolio-summary/export")
async def export_portfolio_csv(
    period: str | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "impact")),
    db: AsyncSession = Depends(get_db),
):
    """Export ESG portfolio data as CSV."""
    csv_content = await service.export_portfolio_csv(
        db, current_user.org_id, period=period
    )
    filename = f"esg-portfolio{f'-{period}' if period else ''}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Per-project metrics ───────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/metrics",
    response_model=ESGMetricsHistoryResponse,
)
async def get_project_metrics(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "impact")),
    db: AsyncSession = Depends(get_db),
):
    """Return full ESG metrics history for a project."""
    records = await service.get_project_esg_metrics(
        db, project_id, current_user.org_id
    )
    return ESGMetricsHistoryResponse(project_id=project_id, records=records)


@router.put(
    "/projects/{project_id}/metrics",
    response_model=ESGMetricsResponse,
    status_code=status.HTTP_200_OK,
)
async def upsert_project_metrics(
    project_id: uuid.UUID,
    body: ESGMetricsUpsertRequest,
    current_user: CurrentUser = Depends(require_permission("create", "impact")),
    db: AsyncSession = Depends(get_db),
):
    """Create or update ESG metrics for a project period."""
    try:
        metrics = await service.upsert_esg_metrics(
            db, project_id, current_user.org_id, body
        )
        await db.commit()
        await db.refresh(metrics)
    except Exception as exc:
        logger.error("esg_upsert_failed", project_id=str(project_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save ESG metrics.",
        )
    return service._to_response(metrics)
