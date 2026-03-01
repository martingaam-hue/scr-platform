"""Cashflow pacing models for J-curve tracking."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.investors import Portfolio


class CashflowAssumption(BaseModel):
    """Per-portfolio pacing assumptions (one active set per portfolio)."""

    __tablename__ = "cashflow_assumptions"

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    # Commitment & deployment
    committed_capital: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    investment_period_years: Mapped[int] = mapped_column(nullable=False, default=5)
    fund_life_years: Mapped[int] = mapped_column(nullable=False, default=10)
    # Scenario modifiers (multipliers on base case)
    optimistic_modifier: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("1.20"))
    pessimistic_modifier: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0.80"))
    # J-curve shape parameters (JSONB: {"year_1_pct": -0.05, ...})
    deployment_schedule: Mapped[dict] = mapped_column(JSONB, default=dict)
    distribution_schedule: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Metadata
    label: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True)

    __table_args__ = (
        UniqueConstraint("portfolio_id", "is_active", name="uq_one_active_pacing_per_portfolio"),
    )


class CashflowProjection(BaseModel):
    """Annual projected and actual cashflow lines (one row per year per scenario)."""

    __tablename__ = "cashflow_projections"

    assumption_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cashflow_assumptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    scenario: Mapped[str] = mapped_column(String(20), nullable=False)  # base|optimistic|pessimistic
    year: Mapped[int] = mapped_column(nullable=False)  # fund year 1..N
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    # Projected
    projected_contributions: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    projected_distributions: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    projected_nav: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    projected_net_cashflow: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    # Actual (filled in as data becomes available)
    actual_contributions: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    actual_distributions: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    actual_nav: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    actual_net_cashflow: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))

    __table_args__ = (
        UniqueConstraint("assumption_id", "scenario", "year", name="uq_cashflow_projection_row"),
    )
