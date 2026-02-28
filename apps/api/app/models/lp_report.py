"""LP Report model — tracks LP-facing fund performance reports."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, Float, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class LPReport(BaseModel):
    """ILPA-style LP report with calculated financial metrics and AI-generated narrative."""

    __tablename__ = "lp_reports"

    # Tenant scoping
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Period
    report_period: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "Q1 2025"
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Workflow status
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft", nullable=False
    )  # draft | review | approved | distributed
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Financial metrics — computed deterministically in Python (NEVER by LLM)
    gross_irr: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_irr: Mapped[float | None] = mapped_column(Float, nullable=True)
    tvpi: Mapped[float | None] = mapped_column(Float, nullable=True)   # Total Value to Paid-In
    dpi: Mapped[float | None] = mapped_column(Float, nullable=True)    # Distributions to Paid-In
    rvpi: Mapped[float | None] = mapped_column(Float, nullable=True)   # Residual Value to Paid-In
    moic: Mapped[float | None] = mapped_column(Float, nullable=True)   # Multiple on Invested Capital

    total_committed: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_invested: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_returned: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_nav: Mapped[float | None] = mapped_column(Float, nullable=True)

    # AI-generated narrative sections stored as JSONB
    # Schema: {executive_summary, portfolio_commentary, market_outlook, esg_highlights}
    narrative: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Per-investment data snapshot for the period
    # Schema: [{project_id, name, vintage, committed, invested, nav, realized, moic, stage, notes}]
    investments_data: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Generated HTML report stored in S3
    pdf_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(nullable=True)
