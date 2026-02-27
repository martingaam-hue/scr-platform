"""Pydantic schemas for Portfolio endpoints."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    AssetType,
    FundType,
    HoldingStatus,
    PortfolioStatus,
    PortfolioStrategy,
    SFDRClassification,
)


# ── Portfolio ───────────────────────────────────────────────────────────────


class PortfolioCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    strategy: PortfolioStrategy
    fund_type: FundType
    vintage_year: int | None = None
    target_aum: Decimal = Field(..., gt=0)
    current_aum: Decimal = Field(default=Decimal("0"))
    currency: str = Field("USD", max_length=3)
    sfdr_classification: SFDRClassification = SFDRClassification.NOT_APPLICABLE


class PortfolioUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    strategy: PortfolioStrategy | None = None
    fund_type: FundType | None = None
    vintage_year: int | None = None
    target_aum: Decimal | None = Field(None, gt=0)
    current_aum: Decimal | None = None
    currency: str | None = Field(None, max_length=3)
    sfdr_classification: SFDRClassification | None = None
    status: PortfolioStatus | None = None


class PortfolioMetricsResponse(BaseModel):
    irr_gross: Decimal | None = None
    irr_net: Decimal | None = None
    moic: Decimal | None = None
    tvpi: Decimal | None = None
    dpi: Decimal | None = None
    rvpi: Decimal | None = None
    total_invested: Decimal
    total_distributions: Decimal
    total_value: Decimal
    carbon_reduction_tons: Decimal | None = None
    as_of_date: date


class PortfolioResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    strategy: PortfolioStrategy
    fund_type: FundType
    vintage_year: int | None = None
    target_aum: Decimal
    current_aum: Decimal
    currency: str
    sfdr_classification: SFDRClassification
    status: PortfolioStatus
    created_at: datetime
    updated_at: datetime


class PortfolioDetailResponse(PortfolioResponse):
    latest_metrics: PortfolioMetricsResponse | None = None
    holding_count: int = 0


class PortfolioListResponse(BaseModel):
    items: list[PortfolioResponse]
    total: int


# ── Holdings ────────────────────────────────────────────────────────────────


class HoldingCreateRequest(BaseModel):
    asset_name: str = Field(..., min_length=1, max_length=500)
    asset_type: AssetType
    investment_date: date
    investment_amount: Decimal = Field(..., gt=0)
    current_value: Decimal = Field(..., ge=0)
    ownership_pct: Decimal | None = Field(None, ge=0, le=100)
    currency: str = Field("USD", max_length=3)
    project_id: uuid.UUID | None = None
    notes: str = ""


class HoldingUpdateRequest(BaseModel):
    asset_name: str | None = Field(None, min_length=1, max_length=500)
    asset_type: AssetType | None = None
    investment_date: date | None = None
    investment_amount: Decimal | None = Field(None, gt=0)
    current_value: Decimal | None = Field(None, ge=0)
    ownership_pct: Decimal | None = Field(None, ge=0, le=100)
    currency: str | None = Field(None, max_length=3)
    status: HoldingStatus | None = None
    exit_date: date | None = None
    exit_amount: Decimal | None = None
    notes: str | None = None


class HoldingResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    project_id: uuid.UUID | None = None
    asset_name: str
    asset_type: AssetType
    investment_date: date
    investment_amount: Decimal
    current_value: Decimal
    ownership_pct: Decimal | None = None
    currency: str
    status: HoldingStatus
    exit_date: date | None = None
    exit_amount: Decimal | None = None
    notes: str
    moic: Decimal | None = None
    created_at: datetime
    updated_at: datetime


class HoldingTotals(BaseModel):
    total_invested: Decimal
    total_current_value: Decimal
    weighted_moic: Decimal | None = None


class HoldingListResponse(BaseModel):
    items: list[HoldingResponse]
    total: int
    totals: HoldingTotals


# ── Cash Flows & Allocation ─────────────────────────────────────────────────


class CashFlowEntry(BaseModel):
    date: date
    amount: Decimal
    type: str  # "contribution" | "distribution"
    holding_name: str | None = None


class CashFlowResponse(BaseModel):
    items: list[CashFlowEntry]


class AllocationBreakdown(BaseModel):
    name: str
    value: Decimal
    percentage: Decimal


class AllocationResponse(BaseModel):
    by_sector: list[AllocationBreakdown] = []
    by_geography: list[AllocationBreakdown] = []
    by_stage: list[AllocationBreakdown] = []
    by_asset_type: list[AllocationBreakdown] = []
