"""LP Reporting — Pydantic v2 schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Narrative schema ──────────────────────────────────────────────────────────


class LPReportNarrative(BaseModel):
    """AI-generated narrative sections for an LP report."""

    executive_summary: str = ""
    portfolio_commentary: str = ""
    market_outlook: str = ""
    esg_highlights: str = ""


# ── Investment data item ──────────────────────────────────────────────────────


class InvestmentDataItem(BaseModel):
    """Per-investment data snapshot stored in JSONB."""

    project_id: str
    name: str
    vintage: int | None = None
    committed: float | None = None
    invested: float | None = None
    nav: float | None = None
    realized: float | None = None
    moic: float | None = None
    stage: str | None = None
    notes: str | None = None


# ── Request schemas ───────────────────────────────────────────────────────────


class CreateLPReportRequest(BaseModel):
    """Request body for creating an LP report."""

    portfolio_id: uuid.UUID | None = None
    report_period: str = Field(..., description='e.g. "Q1 2025"')
    period_start: date
    period_end: date

    # Optional: cash flows for IRR calculation
    # [{date: "YYYY-MM-DD", amount: float}] — negative=invested, positive=returned/NAV
    cash_flows: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Cash flows for IRR calculation. Negative=invested, positive=returned.",
    )

    # Optional: investment data to include in the report
    investments_data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Per-investment snapshots",
    )

    # Optional fund-level totals (if not derivable from cash_flows)
    total_committed: float | None = None
    total_invested: float | None = None
    total_returned: float | None = None
    total_nav: float | None = None


class UpdateLPReportRequest(BaseModel):
    """Request body for updating narrative sections of an LP report."""

    narrative: LPReportNarrative | None = None
    investments_data: list[dict[str, Any]] | None = None
    report_period: str | None = None
    period_start: date | None = None
    period_end: date | None = None


# ── Response schemas ──────────────────────────────────────────────────────────


class LPReportResponse(BaseModel):
    """Full LP report response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    portfolio_id: uuid.UUID | None

    report_period: str
    period_start: date
    period_end: date

    status: str
    approved_by: uuid.UUID | None
    approved_at: datetime | None

    # Financial metrics
    gross_irr: float | None
    net_irr: float | None
    tvpi: float | None
    dpi: float | None
    rvpi: float | None
    moic: float | None
    total_committed: float | None
    total_invested: float | None
    total_returned: float | None
    total_nav: float | None

    # AI narrative
    narrative: dict[str, Any] | None

    # Investment data
    investments_data: list[Any] | None

    # PDF / HTML report
    pdf_s3_key: str | None
    generated_at: datetime | None
    download_url: str | None = None

    created_at: datetime
    updated_at: datetime


class LPReportListResponse(BaseModel):
    """Paginated list of LP reports."""

    items: list[LPReportResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ApproveReportResponse(BaseModel):
    """Response after approving an LP report."""

    id: uuid.UUID
    status: str
    approved_by: uuid.UUID
    approved_at: datetime


class GeneratePDFResponse(BaseModel):
    """Response after generating the HTML/PDF for an LP report."""

    id: uuid.UUID
    pdf_s3_key: str
    download_url: str
    generated_at: datetime
