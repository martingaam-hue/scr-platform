"""Marketplace module schemas — Listings, RFQs, Transactions."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, field_validator, model_validator


# ── Listing ───────────────────────────────────────────────────────────────────


class ListingCreateRequest(BaseModel):
    project_id: uuid.UUID | None = None
    title: str
    description: str = ""
    listing_type: str  # ListingType value
    visibility: str = "qualified_only"
    asking_price: float | None = None
    minimum_investment: float | None = None
    currency: str = "USD"
    details: dict[str, Any] | None = None
    expires_at: date | None = None

    @field_validator("listing_type")
    @classmethod
    def valid_listing_type(cls, v: str) -> str:
        valid = {"equity_sale", "debt_sale", "co_investment", "carbon_credit"}
        if v not in valid:
            raise ValueError(f"listing_type must be one of {valid}")
        return v

    @field_validator("visibility")
    @classmethod
    def valid_visibility(cls, v: str) -> str:
        valid = {"public", "qualified_only", "invite_only"}
        if v not in valid:
            raise ValueError(f"visibility must be one of {valid}")
        return v


class ListingUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    visibility: str | None = None
    asking_price: float | None = None
    minimum_investment: float | None = None
    details: dict[str, Any] | None = None
    expires_at: date | None = None


class ListingResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID | None
    title: str
    description: str
    listing_type: str
    status: str
    visibility: str
    asking_price: str | None
    minimum_investment: str | None
    currency: str
    details: dict[str, Any]
    expires_at: date | None
    # Enriched from joined tables
    project_name: str | None = None
    project_type: str | None = None
    geography_country: str | None = None
    signal_score: int | None = None
    rfq_count: int = 0
    created_at: datetime
    updated_at: datetime


class ListingListResponse(BaseModel):
    items: list[ListingResponse]
    total: int


class PriceSuggestion(BaseModel):
    suggested_price: float
    price_range_min: float
    price_range_max: float
    basis: str
    comparable_count: int


# ── RFQ ──────────────────────────────────────────────────────────────────────


class RFQCreateRequest(BaseModel):
    proposed_price: float
    currency: str = "USD"
    message: str = ""
    proposed_terms: dict[str, Any] | None = None


class RFQRespondRequest(BaseModel):
    action: Literal["accept", "reject", "counter"]
    counter_price: float | None = None
    counter_terms: dict[str, Any] | None = None
    message: str = ""

    @model_validator(mode="after")
    def counter_requires_price(self) -> RFQRespondRequest:
        if self.action == "counter" and self.counter_price is None:
            raise ValueError("counter_price is required when action='counter'")
        return self


class RFQResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    buyer_org_id: uuid.UUID
    proposed_price: str
    currency: str
    status: str
    message: str
    counter_price: str | None
    counter_terms: dict[str, Any] | None
    submitted_by: uuid.UUID
    listing_title: str | None = None
    created_at: datetime
    updated_at: datetime


class RFQListResponse(BaseModel):
    items: list[RFQResponse]
    total: int


# ── Transaction ───────────────────────────────────────────────────────────────


class TransactionResponse(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    buyer_org_id: uuid.UUID
    seller_org_id: uuid.UUID
    rfq_id: uuid.UUID | None
    amount: str
    currency: str
    status: str
    terms: dict[str, Any] | None
    settlement_details: dict[str, Any] | None
    completed_at: datetime | None
    listing_title: str | None = None
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
