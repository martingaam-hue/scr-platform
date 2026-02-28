"""FX — Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class FXRateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    base_currency: str
    quote_currency: str
    rate: float
    rate_date: date
    source: str
    created_at: datetime


class LatestRatesResponse(BaseModel):
    rates: dict[str, float]  # {currency: rate_vs_EUR}
    rate_date: date | None


class CurrencyExposureItem(BaseModel):
    currency: str
    value_eur: float
    pct: float
    project_count: int


class FXExposureResponse(BaseModel):
    base_currency: str
    total_value_base: float
    exposure: list[CurrencyExposureItem]
    hedging_recommendation: str


class FXImpactResponse(BaseModel):
    period_days: int
    currency_impacts: list[dict[str, Any]]
    total_impact_eur: float
    total_impact_pct: float


class ConvertRequest(BaseModel):
    amount: float
    from_currency: str
    to_currency: str
    rate_date: date | None = None


class ConvertResponse(BaseModel):
    amount: float
    from_currency: str
    to_currency: str
    converted_amount: float
    rate: float | None
    rate_date: date | None
