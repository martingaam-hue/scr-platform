"""Insurance module Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Coverage Types ─────────────────────────────────────────────────────────────

COVERAGE_TYPES = [
    "construction_all_risk",
    "operational_all_risk",
    "third_party_liability",
    "business_interruption",
    "political_risk",
    "environmental_liability",
    "directors_officers",
    "cyber_liability",
    "machinery_breakdown",
    "weather_parametric",
]


# ── Recommendation ─────────────────────────────────────────────────────────────


class CoverageRecommendation(BaseModel):
    policy_type: str
    label: str
    is_mandatory: bool
    typical_coverage_pct: float  # % of project value
    rationale: str
    priority: str  # critical | high | medium | low


# ── Impact Analysis ────────────────────────────────────────────────────────────


class InsuranceImpactResponse(BaseModel):
    project_id: uuid.UUID
    project_name: str
    project_type: str
    geography: str
    total_investment: float
    currency: str

    # Coverage summary
    recommended_coverage_types: list[str]
    estimated_annual_premium_pct: float  # % of total investment
    estimated_annual_premium: float      # in project currency

    # Risk impact
    risk_reduction_score: int     # 0–100 (how much insurance reduces risk)
    coverage_adequacy: str        # excellent | good | partial | insufficient
    uncovered_risk_areas: list[str]

    # Financial impact
    irr_impact_bps: int           # basis points impact (negative = cost)
    npv_premium_cost: float       # PV of 20-year premium stream

    # Recommendations
    recommendations: list[CoverageRecommendation]
    ai_narrative: str

    # Meta
    analyzed_at: datetime


# ── Project Insurance Summary (lighter) ───────────────────────────────────────


class InsuranceSummaryResponse(BaseModel):
    project_id: uuid.UUID
    coverage_adequacy: str
    risk_reduction_score: int
    estimated_annual_premium: float
    currency: str
    coverage_gaps: list[str]
    top_recommendation: str | None


# ── Quote CRUD ─────────────────────────────────────────────────────────────────


class QuoteCreate(BaseModel):
    project_id: uuid.UUID | None = None
    provider_name: str
    coverage_type: str
    coverage_amount: Decimal
    quoted_premium: Decimal
    currency: str = "USD"
    valid_until: date | None = None
    terms: dict[str, Any] = {}
    side: str = "investor"  # ally | investor


class QuoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID | None
    provider_name: str
    coverage_type: str
    coverage_amount: Decimal
    quoted_premium: Decimal
    currency: str
    valid_until: date | None
    terms: dict[str, Any] | None
    side: str
    created_at: datetime


# ── Policy CRUD ────────────────────────────────────────────────────────────────


class PolicyCreate(BaseModel):
    quote_id: uuid.UUID
    project_id: uuid.UUID | None = None
    portfolio_id: uuid.UUID | None = None
    policy_number: str
    provider_name: str
    coverage_type: str
    coverage_amount: Decimal
    premium_amount: Decimal
    premium_frequency: str = "annual"  # monthly | quarterly | annual
    start_date: date
    end_date: date
    side: str = "investor"  # ally | investor
    terms: dict[str, Any] = {}


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    org_id: uuid.UUID
    quote_id: uuid.UUID
    project_id: uuid.UUID | None
    portfolio_id: uuid.UUID | None
    policy_number: str
    provider_name: str
    coverage_type: str
    coverage_amount: Decimal
    premium_amount: Decimal
    premium_frequency: str
    start_date: date
    end_date: date
    status: str
    risk_score_impact: Decimal
    side: str
    created_at: datetime
