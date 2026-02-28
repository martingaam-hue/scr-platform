"""Comparable Transactions model — stores market transaction data for benchmarking."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ComparableTransaction(BaseModel):
    """A market transaction used as a comparable for valuation and benchmarking.

    org_id = NULL  → global/public comp visible to all orgs
    org_id = UUID  → org-private comp visible only to that org
    """

    __tablename__ = "comparable_transactions"

    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    # NULL = global/public comp, non-null = org-private comp

    # ── Deal identity ─────────────────────────────────────────────────────────

    deal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # solar, wind, hydro, bess, biomass, other
    geography: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # ── Transaction timing ────────────────────────────────────────────────────

    close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    close_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Denormalised year for quick range filtering

    # ── Size & value ──────────────────────────────────────────────────────────

    deal_size_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity_mw: Mapped[float | None] = mapped_column(Float, nullable=True)
    ev_per_mw: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Enterprise value per MW (€k/MW)
    equity_value_eur: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Return metrics ────────────────────────────────────────────────────────

    equity_irr: Mapped[float | None] = mapped_column(Float, nullable=True)
    project_irr: Mapped[float | None] = mapped_column(Float, nullable=True)
    ebitda_multiple: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Project characteristics ───────────────────────────────────────────────

    stage_at_close: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # construction_ready, operational, development
    offtake_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # ppa, merchant, cfd, subsidy
    offtake_counterparty_rating: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )
    # AAA, AA, A, BBB, BB, B, NR

    # ── Parties (anonymised) ──────────────────────────────────────────────────

    buyer_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # pe_fund, infrastructure_fund, utility, corporate, sovereign_fund
    seller_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Source / data quality ─────────────────────────────────────────────────

    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    data_quality: Mapped[str] = mapped_column(
        String(20), default="estimated", server_default="estimated", nullable=False
    )
    # confirmed, estimated, rumored

    # ── AI / search metadata ──────────────────────────────────────────────────

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────

    added_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
