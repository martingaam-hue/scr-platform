"""Comparable Transactions — Pydantic v2 schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


# ── Core comp schemas ─────────────────────────────────────────────────────────


class CompCreate(BaseModel):
    """Schema for creating a new comparable transaction."""

    deal_name: str
    asset_type: str
    geography: str | None = None
    country_code: str | None = None

    close_date: date | None = None
    close_year: int | None = None

    deal_size_eur: float | None = None
    capacity_mw: float | None = None
    ev_per_mw: float | None = None
    equity_value_eur: float | None = None

    equity_irr: float | None = None
    project_irr: float | None = None
    ebitda_multiple: float | None = None

    stage_at_close: str | None = None
    offtake_type: str | None = None
    offtake_counterparty_rating: str | None = None

    buyer_type: str | None = None
    seller_type: str | None = None

    source: str | None = None
    source_url: str | None = None
    data_quality: str = "estimated"

    description: str | None = None
    tags: list[Any] | None = None

    @field_validator("data_quality")
    @classmethod
    def validate_data_quality(cls, v: str) -> str:
        allowed = {"confirmed", "estimated", "rumored"}
        if v not in allowed:
            raise ValueError(f"data_quality must be one of: {', '.join(sorted(allowed))}")
        return v


class CompUpdate(BaseModel):
    """Schema for updating an existing comparable transaction (all fields optional)."""

    deal_name: str | None = None
    asset_type: str | None = None
    geography: str | None = None
    country_code: str | None = None

    close_date: date | None = None
    close_year: int | None = None

    deal_size_eur: float | None = None
    capacity_mw: float | None = None
    ev_per_mw: float | None = None
    equity_value_eur: float | None = None

    equity_irr: float | None = None
    project_irr: float | None = None
    ebitda_multiple: float | None = None

    stage_at_close: str | None = None
    offtake_type: str | None = None
    offtake_counterparty_rating: str | None = None

    buyer_type: str | None = None
    seller_type: str | None = None

    source: str | None = None
    source_url: str | None = None
    data_quality: str | None = None

    description: str | None = None
    tags: list[Any] | None = None


class CompResponse(BaseModel):
    """Full comp representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID | None

    deal_name: str
    asset_type: str
    geography: str | None
    country_code: str | None

    close_date: date | None
    close_year: int | None

    deal_size_eur: float | None
    capacity_mw: float | None
    ev_per_mw: float | None
    equity_value_eur: float | None

    equity_irr: float | None
    project_irr: float | None
    ebitda_multiple: float | None

    stage_at_close: str | None
    offtake_type: str | None
    offtake_counterparty_rating: str | None

    buyer_type: str | None
    seller_type: str | None

    source: str | None
    source_url: str | None
    data_quality: str

    description: str | None
    tags: list[Any] | None

    added_by: uuid.UUID | None

    created_at: datetime
    updated_at: datetime
    is_deleted: bool


# ── List response ─────────────────────────────────────────────────────────────


class CompListResponse(BaseModel):
    items: list[CompResponse]
    total: int


# ── AI similarity ─────────────────────────────────────────────────────────────


class SimilarCompResult(BaseModel):
    """A single comp ranked by AI similarity against a project."""

    comp: dict[str, Any]
    similarity_score: int  # 0–100
    rationale: str


class SimilarCompsResponse(BaseModel):
    items: list[SimilarCompResult]


# ── Implied valuation ─────────────────────────────────────────────────────────


class ImpliedValuationRequest(BaseModel):
    """Request body for the implied valuation calculator."""

    comp_ids: list[uuid.UUID]
    project: dict[str, Any]
    # Must contain at minimum: capacity_mw (float) and optionally ebitda (float)


class ImpliedValuationResponse(BaseModel):
    """Statistical summary of valuation implied by selected comps."""

    ev_per_mw_median: float | None
    ev_per_mw_p25: float | None
    ev_per_mw_p75: float | None
    implied_ev_eur: float | None

    ebitda_multiple_median: float | None
    ebitda_multiple_p25: float | None
    ebitda_multiple_p75: float | None
    implied_ev_from_ebitda: float | None

    comps_used: int
    rationale: str


# ── CSV import ────────────────────────────────────────────────────────────────


class ImportCSVResponse(BaseModel):
    """Result of a bulk CSV import."""

    created: int
    errors: list[dict[str, Any]]
