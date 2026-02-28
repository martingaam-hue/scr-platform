"""ESG Impact metrics model — per-project, per-period ESG data."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ESGMetrics(BaseModel):
    __tablename__ = "esg_metrics"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "2024-Q4"

    # ── Environmental ─────────────────────────────────────────────────────────
    carbon_footprint_tco2e: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbon_avoided_tco2e: Mapped[float | None] = mapped_column(Float, nullable=True)
    renewable_energy_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_usage_cubic_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    waste_diverted_tonnes: Mapped[float | None] = mapped_column(Float, nullable=True)
    biodiversity_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0–100

    # ── Social ────────────────────────────────────────────────────────────────
    jobs_created: Mapped[int | None] = mapped_column(Integer, nullable=True)
    jobs_supported: Mapped[int | None] = mapped_column(Integer, nullable=True)
    local_procurement_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    community_investment_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    gender_diversity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    health_safety_incidents: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Governance ────────────────────────────────────────────────────────────
    board_independence_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    audit_completed: Mapped[bool] = mapped_column(default=False, server_default="false")
    esg_reporting_standard: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # GRI, SASB, TCFD, SFDR

    # ── EU Taxonomy ───────────────────────────────────────────────────────────
    taxonomy_eligible: Mapped[bool] = mapped_column(default=False, server_default="false")
    taxonomy_aligned: Mapped[bool] = mapped_column(default=False, server_default="false")
    taxonomy_activity: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── SFDR classification ───────────────────────────────────────────────────
    sfdr_article: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 6, 8, or 9

    # ── SDG contributions (JSONB) ─────────────────────────────────────────────
    # {7: {"name": "Affordable Clean Energy", "contribution_level": "high"}, ...}
    sdg_contributions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── AI-generated narrative ────────────────────────────────────────────────
    esg_narrative: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("project_id", "period", name="uq_esg_project_period"),
    )
