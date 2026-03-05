"""Market Data Enrichment — Pydantic v2 schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── MarketDataSource ──────────────────────────────────────────────────────────


class MarketDataSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9_-]+$")
    description: str | None = None
    source_type: str = Field(..., pattern="^(official_api|rss_feed|document|manual)$")
    tier: int = Field(..., ge=1, le=4)
    base_url: str | None = None
    legal_basis: str = Field(
        "public_data", pattern="^(public_data|licensed|fair_use|manual_entry)$"
    )
    rate_limit_per_hour: int = Field(60, ge=1, le=10000)
    is_active: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class MarketDataSourceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    base_url: str | None = None
    legal_basis: str | None = None
    rate_limit_per_hour: int | None = None
    is_active: bool | None = None
    config: dict[str, Any] | None = None


class MarketDataSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    name: str
    slug: str
    description: str | None
    source_type: str
    tier: int
    base_url: str | None
    legal_basis: str
    rate_limit_per_hour: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── FetchLog ──────────────────────────────────────────────────────────────────


class FetchLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    source_id: UUID
    status: str
    records_fetched: int
    records_new: int
    records_updated: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class EnrichmentRunResponse(BaseModel):
    fetch_log_id: UUID
    status: str
    records_fetched: int


# ── MarketDataProcessed ───────────────────────────────────────────────────────


class MarketDataProcessedRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    raw_id: UUID | None
    data_type: str
    category: str
    region: str | None
    technology: str | None
    effective_date: date | None
    value_numeric: Decimal | None
    value_text: str | None
    value_json: dict | None
    unit: str | None
    confidence: float
    source_url: str | None
    review_status: str
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    created_at: datetime


class ManualEntryCreate(BaseModel):
    data_type: str = Field(..., pattern="^(price|policy|project_pipeline|macro_indicator|news)$")
    category: str = Field(..., min_length=1, max_length=100)
    region: str | None = None
    technology: str | None = None
    effective_date: date | None = None
    value_numeric: Decimal | None = None
    value_text: str | None = None
    value_json: dict[str, Any] | None = None
    unit: str | None = None
    source_url: str | None = None


# ── ReviewDecision ────────────────────────────────────────────────────────────


class ReviewDecision(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    notes: str | None = None


# ── ReviewQueue ───────────────────────────────────────────────────────────────


class ReviewQueueItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    processed_id: UUID
    assigned_to: UUID | None
    priority: int
    reason: str
    resolved_at: datetime | None
    created_at: datetime
    processed: MarketDataProcessedRead | None = None


# ── Dashboard ─────────────────────────────────────────────────────────────────


class MarketEnrichmentDashboard(BaseModel):
    sources_count: int
    active_sources_count: int
    records_today: int
    pending_review_count: int
    recent_fetches: list[FetchLogRead]
