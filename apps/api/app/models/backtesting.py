"""SQLAlchemy models for the Score Backtesting module."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DATE, INTEGER, NUMERIC, TEXT, TIMESTAMP, VARCHAR, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import ModelMixin


class DealOutcome(Base, ModelMixin):
    """Records the actual outcome of a deal for backtesting purposes."""

    __tablename__ = "deal_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Plain UUID — deal_flow_stages table does not exist
    deal_flow_stage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    outcome_type: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    actual_irr: Mapped[Decimal | None] = mapped_column(NUMERIC(10, 4), nullable=True)
    actual_moic: Mapped[Decimal | None] = mapped_column(NUMERIC(10, 4), nullable=True)
    actual_revenue_eur: Mapped[Decimal | None] = mapped_column(NUMERIC(19, 4), nullable=True)
    signal_score_at_evaluation: Mapped[Decimal | None] = mapped_column(NUMERIC(5, 2), nullable=True)
    signal_score_at_decision: Mapped[Decimal | None] = mapped_column(NUMERIC(5, 2), nullable=True)
    signal_dimensions_at_decision: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    decision_date: Mapped[date | None] = mapped_column(DATE, nullable=True)
    outcome_date: Mapped[date | None] = mapped_column(DATE, nullable=True)
    notes: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BacktestRun(Base, ModelMixin):
    """Records the results of a backtesting run."""

    __tablename__ = "backtest_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    methodology: Mapped[str] = mapped_column(
        VARCHAR(50),
        nullable=False,
        server_default="threshold",
    )
    date_from: Mapped[date | None] = mapped_column(DATE, nullable=True)
    date_to: Mapped[date | None] = mapped_column(DATE, nullable=True)
    min_score_threshold: Mapped[Decimal | None] = mapped_column(NUMERIC(5, 2), nullable=True)
    accuracy: Mapped[Decimal | None] = mapped_column(NUMERIC(5, 4), nullable=True)
    precision: Mapped[Decimal | None] = mapped_column(NUMERIC(5, 4), nullable=True)
    recall: Mapped[Decimal | None] = mapped_column(NUMERIC(5, 4), nullable=True)
    auc_roc: Mapped[Decimal | None] = mapped_column(NUMERIC(5, 4), nullable=True)
    f1_score: Mapped[Decimal | None] = mapped_column(NUMERIC(5, 4), nullable=True)
    sample_size: Mapped[int | None] = mapped_column(INTEGER, nullable=True)
    results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        nullable=False,
    )
