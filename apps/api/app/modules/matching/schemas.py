"""Matching module API schemas."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


# ── Alignment breakdown ───────────────────────────────────────────────────────


class AlignmentBreakdownResponse(BaseModel):
    overall: int
    sector: int
    geography: int
    ticket_size: int
    stage: int
    risk_return: int
    esg: int
    breakdown: dict[str, Any]


# ── Investor → Project recommendations ───────────────────────────────────────


class RecommendedProjectResponse(BaseModel):
    match_id: uuid.UUID | None       # None if not yet in pipeline
    project_id: uuid.UUID
    project_name: str
    project_type: str
    geography_country: str
    stage: str
    total_investment_required: str
    currency: str
    cover_image_url: str | None
    signal_score: int | None
    alignment: AlignmentBreakdownResponse
    status: str                      # MatchStatus value, "new" if not yet matched
    mandate_id: uuid.UUID | None
    mandate_name: str | None
    updated_at: datetime | None


class InvestorRecommendationsResponse(BaseModel):
    items: list[RecommendedProjectResponse]
    total: int


# ── Ally → Investor recommendations ──────────────────────────────────────────


class MatchingInvestorResponse(BaseModel):
    match_id: uuid.UUID | None
    investor_org_id: uuid.UUID
    investor_name: str
    logo_url: str | None
    mandate_id: uuid.UUID | None
    mandate_name: str | None
    ticket_size_min: str
    ticket_size_max: str
    sectors: list[str]
    geographies: list[str]
    risk_tolerance: str
    alignment: AlignmentBreakdownResponse
    status: str
    initiated_by: str | None
    updated_at: datetime | None


class AllyRecommendationsResponse(BaseModel):
    project_id: uuid.UUID
    project_name: str
    items: list[MatchingInvestorResponse]
    total: int


# ── Match messages ────────────────────────────────────────────────────────────


class MatchMessageResponse(BaseModel):
    id: uuid.UUID
    match_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    is_system: bool
    created_at: datetime


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class MessagesResponse(BaseModel):
    items: list[MatchMessageResponse]
    total: int


# ── Status update ─────────────────────────────────────────────────────────────


class MatchStatusUpdateRequest(BaseModel):
    status: str
    notes: str | None = None


class MatchStatusResponse(BaseModel):
    match_id: uuid.UUID
    status: str
    updated_at: datetime


# ── Mandate CRUD ──────────────────────────────────────────────────────────────


class MandateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    sectors: list[str] | None = None
    geographies: list[str] | None = None
    stages: list[str] | None = None
    ticket_size_min: Decimal = Field(..., ge=0)
    ticket_size_max: Decimal = Field(..., ge=0)
    target_irr_min: Decimal | None = None
    risk_tolerance: str = "moderate"
    esg_requirements: dict[str, Any] | None = None
    exclusions: dict[str, Any] | None = None
    is_active: bool = True


class MandateUpdateRequest(BaseModel):
    name: str | None = None
    sectors: list[str] | None = None
    geographies: list[str] | None = None
    stages: list[str] | None = None
    ticket_size_min: Decimal | None = None
    ticket_size_max: Decimal | None = None
    target_irr_min: Decimal | None = None
    risk_tolerance: str | None = None
    esg_requirements: dict[str, Any] | None = None
    exclusions: dict[str, Any] | None = None
    is_active: bool | None = None


class MandateResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    sectors: list[str] | None
    geographies: list[str] | None
    stages: list[str] | None
    ticket_size_min: str
    ticket_size_max: str
    target_irr_min: str | None
    risk_tolerance: str
    esg_requirements: dict[str, Any] | None
    exclusions: dict[str, Any] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
