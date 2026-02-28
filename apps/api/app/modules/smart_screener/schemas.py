"""Smart Screener Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ScreenerQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    existing_filters: dict[str, Any] | None = None


class ParsedFilters(BaseModel):
    project_types: list[str] = []
    geographies: list[str] = []
    stages: list[str] = []
    min_signal_score: int | None = None
    max_signal_score: int | None = None
    min_ticket_size: float | None = None
    max_ticket_size: float | None = None
    min_capacity_mw: float | None = None
    max_capacity_mw: float | None = None
    sector_keywords: list[str] = []
    esg_requirements: list[str] = []
    sort_by: str = "signal_score"


class ScreenerResult(BaseModel):
    id: uuid.UUID
    name: str
    project_type: str | None
    geography_country: str | None
    stage: str | None
    total_investment_required: float | None
    currency: str | None
    signal_score: int | None
    status: str | None


class ScreenerResponse(BaseModel):
    query: str
    parsed_filters: ParsedFilters
    results: list[ScreenerResult]
    total_results: int
    suggestions: list[str]


class SaveSearchRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    query: str = Field(..., min_length=1, max_length=2000)
    filters: dict[str, Any]
    notify_new_matches: bool = False


class SavedSearchResponse(BaseModel):
    id: uuid.UUID
    name: str
    query: str
    filters: dict[str, Any]
    notify_new_matches: bool
    last_used: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
