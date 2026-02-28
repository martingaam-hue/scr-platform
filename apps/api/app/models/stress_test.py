"""Portfolio stress test / Monte Carlo simulation result models."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class StressTestRun(BaseModel):
    """Persisted result of a Monte Carlo portfolio stress test."""

    __tablename__ = "stress_test_runs"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Scenario identity
    scenario_key: Mapped[str] = mapped_column(String(100), nullable=False)  # predefined key or "custom"
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict)  # scenario shock params
    simulations_count: Mapped[int] = mapped_column(Integer, default=10000)

    # Aggregate NAV statistics (EUR)
    base_nav: Mapped[float] = mapped_column(Float, nullable=False)
    mean_nav: Mapped[float] = mapped_column(Float, nullable=False)
    median_nav: Mapped[float] = mapped_column(Float, nullable=False)
    p5_nav: Mapped[float] = mapped_column(Float, nullable=False)   # 5th percentile (VaR floor)
    p95_nav: Mapped[float] = mapped_column(Float, nullable=False)  # 95th percentile
    var_95: Mapped[float] = mapped_column(Float, nullable=False)   # Value at Risk (95%)
    max_loss_pct: Mapped[float] = mapped_column(Float, nullable=False)   # worst simulation loss %
    probability_of_loss: Mapped[float] = mapped_column(Float, nullable=False)  # P(NAV < base)

    # Full distribution + per-project sensitivities
    histogram: Mapped[list] = mapped_column(JSONB, default=list)         # 50-bin counts
    histogram_edges: Mapped[list] = mapped_column(JSONB, default=list)   # 51 bin edges
    project_sensitivities: Mapped[list] = mapped_column(JSONB, default=list)
    # [{project_id, project_name, base_value, stressed_value, change_pct}]

    __table_args__ = (
        Index("ix_stress_portfolio_created", "portfolio_id", "created_at"),
    )
