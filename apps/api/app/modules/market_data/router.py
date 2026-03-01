"""Market Data API router — public economic indicators."""

from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.market_data import service
from app.modules.market_data.schemas import (
    ExternalDataPointResponse,
    MarketDataSummaryResponse,
    RefreshResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/series")
async def list_series(
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return all available series grouped by data source."""
    return await service.list_series(db)


@router.get("/series/{source}/{series_id}", response_model=list[ExternalDataPointResponse])
async def get_series_history(
    source: str,
    series_id: str,
    days: int = 90,
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
) -> list[ExternalDataPointResponse]:
    """Return historical data points for a specific series (default last 90 days)."""
    points = await service.get_series(db, source=source, series_id=series_id, days=days)
    if not points:
        raise HTTPException(status_code=404, detail=f"No data found for {source}/{series_id}")
    return [ExternalDataPointResponse.model_validate(p) for p in points]


@router.get("/summary", response_model=MarketDataSummaryResponse)
async def get_summary(
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
) -> MarketDataSummaryResponse:
    """Return latest values for key economic indicators (10Y Treasury, Fed Funds, etc.)."""
    indicators = await service.get_summary(db)
    return MarketDataSummaryResponse(indicators=indicators)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_market_data(
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    """Manually trigger a market data fetch (admin / analyst+). Runs synchronously."""
    logger.info("market_data.manual_refresh", user_id=str(current_user.id))

    fred_rows = await service.ingest_fred_data(db)
    wb_rows = await service.ingest_worldbank_data(db)

    return RefreshResponse(
        inserted=fred_rows + wb_rows,
        sources=["fred", "worldbank"],
        message=f"Ingested {fred_rows} FRED rows and {wb_rows} World Bank rows.",
    )
