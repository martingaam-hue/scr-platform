"""FX API router — exchange rates and portfolio currency exposure."""

from __future__ import annotations

import uuid
from datetime import date

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.fx import service
from app.modules.fx.schemas import (
    ConvertRequest,
    ConvertResponse,
    CurrencyExposureItem,
    FXExposureResponse,
    LatestRatesResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/fx", tags=["fx"])


@router.get("/rates/latest", response_model=LatestRatesResponse)
async def get_latest_rates(
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    """Return the most recent ECB reference rates."""
    rates, rate_date = await service.get_latest_rates(db)
    return LatestRatesResponse(rates=rates, rate_date=rate_date)


@router.post("/rates/refresh")
async def refresh_rates(
    current_user: CurrentUser = Depends(require_permission("create", "report")),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger an ECB rate fetch (auto-runs daily via Celery Beat)."""
    rates = await service.fetch_ecb_rates(db)
    logger.info("fx.manual_refresh", currencies=len(rates), org_id=str(current_user.org_id))
    return {"fetched": len(rates), "currencies": list(rates.keys())}


@router.get("/exposure", response_model=FXExposureResponse)
async def get_fx_exposure(
    portfolio_id: uuid.UUID | None = None,
    base_currency: str = Query("EUR", max_length=3),
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    """Portfolio currency exposure breakdown."""
    result = await service.get_fx_exposure(
        db,
        org_id=current_user.org_id,
        portfolio_id=portfolio_id,
        base_currency=base_currency,
    )
    return FXExposureResponse(
        base_currency=result["base_currency"],
        total_value_base=result["total_value_base"],
        exposure=[CurrencyExposureItem(**e) for e in result["exposure"]],
        hedging_recommendation=result["hedging_recommendation"],
    )


@router.post("/convert", response_model=ConvertResponse)
async def convert_currency(
    body: ConvertRequest,
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    """Convert an amount between two currencies using stored ECB rates."""
    converted, rate = await service.convert_amount(
        db,
        amount=body.amount,
        from_currency=body.from_currency.upper(),
        to_currency=body.to_currency.upper(),
        on_date=body.rate_date,
    )
    return ConvertResponse(
        amount=body.amount,
        from_currency=body.from_currency.upper(),
        to_currency=body.to_currency.upper(),
        converted_amount=converted,
        rate=rate,
        rate_date=body.rate_date or date.today(),
    )
