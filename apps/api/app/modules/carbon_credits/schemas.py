"""Carbon Credits API schemas."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class CarbonEstimateResult(BaseModel):
    annual_tons_co2e: float
    methodology: str
    methodology_label: str
    assumptions: dict[str, Any]
    confidence: str  # low|medium|high
    notes: str


class CarbonCreditResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    registry: str
    methodology: str
    vintage_year: int
    quantity_tons: float
    price_per_ton: float | None
    currency: str
    serial_number: str | None
    verification_status: str
    verification_body: str | None
    issuance_date: date | None
    retirement_date: date | None
    estimated_annual_tons: float | None
    suggested_methodology: str | None
    revenue_projection: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class CarbonCreditUpdate(BaseModel):
    registry: str | None = None
    methodology: str | None = None
    vintage_year: int | None = None
    quantity_tons: float | None = None
    price_per_ton: float | None = None
    currency: str | None = None
    serial_number: str | None = None
    verification_body: str | None = None


class VerificationStatusUpdate(BaseModel):
    verification_status: str
    verification_body: str | None = None
    notes: str | None = None


class PricingTrendPoint(BaseModel):
    date: str
    vcs_price: float
    gold_standard_price: float
    eu_ets_price: float


class MethodologyResponse(BaseModel):
    id: str
    name: str
    registry: str
    applicable_project_types: list[str]
    description: str
    verification_complexity: str  # low|medium|high
