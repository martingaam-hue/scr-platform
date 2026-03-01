"""Market Data — Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ExternalDataPointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    series_id: str
    series_name: str
    data_date: date
    value: float
    unit: str | None
    fetched_at: datetime


class MarketDataSummary(BaseModel):
    """Latest value for a single series plus 1-day change."""

    source: str
    series_id: str
    series_name: str
    latest_date: date
    latest_value: float
    unit: str | None
    change_pct: float | None  # % change vs previous observation; None if only 1 data point


class SeriesGroupResponse(BaseModel):
    """All series available from a given source."""

    source: str
    series: list[dict[str, Any]]  # {series_id, series_name, unit, latest_date, latest_value}


class MarketDataSummaryResponse(BaseModel):
    indicators: list[MarketDataSummary]


class RefreshResponse(BaseModel):
    inserted: int
    sources: list[str]
    message: str
