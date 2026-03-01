"""Covenant & KPI Monitoring models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import ModelMixin


class Covenant(Base, ModelMixin):
    """Loan/investment covenant with threshold-based compliance tracking."""

    __tablename__ = "covenants"
    __table_args__ = (
        Index("ix_covenants_org_id", "org_id"),
        Index("ix_covenants_project_id", "project_id"),
        Index("ix_covenants_org_project", "org_id", "project_id"),
        Index("ix_covenants_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # financial_ratio, operational_kpi, reporting_deadline, milestone,
    # insurance_maintenance, other
    covenant_type: Mapped[str] = mapped_column(String(50), nullable=False)

    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    # >=, <=, ==, between, not_null
    comparison: Mapped[str] = mapped_column(String(10), nullable=False)
    threshold_upper: Mapped[float | None] = mapped_column(Float, nullable=True)

    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # compliant, warning, breach, waived, not_applicable
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="compliant", server_default="compliant"
    )
    warning_threshold_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.1, server_default="0.1"
    )
    breach_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    waived_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    waived_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    # daily, weekly, monthly, quarterly
    check_frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, default="monthly", server_default="monthly"
    )

    def __repr__(self) -> str:
        return f"<Covenant(id={self.id}, name={self.name!r}, status={self.status})>"


class KPIActual(Base, ModelMixin):
    """Recorded actual KPI values for a project in a given period."""

    __tablename__ = "kpi_actuals"
    __table_args__ = (
        Index("ix_kpi_actuals_org_id", "org_id"),
        Index("ix_kpi_actuals_project_id", "project_id"),
        Index("ix_kpi_actuals_project_kpi", "project_id", "kpi_name"),
        Index("ix_kpi_actuals_project_period", "project_id", "period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    kpi_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # e.g. "2026-Q1", "2026-01"
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    # monthly, quarterly, annual
    period_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="quarterly", server_default="quarterly"
    )

    # manual, document_extraction, api_connector
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    entered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<KPIActual(id={self.id}, kpi={self.kpi_name!r}, period={self.period!r})>"


class KPITarget(Base, ModelMixin):
    """Target KPI values for a project in a given period."""

    __tablename__ = "kpi_targets"
    __table_args__ = (
        Index("ix_kpi_targets_org_id", "org_id"),
        Index("ix_kpi_targets_project_id", "project_id"),
        Index("ix_kpi_targets_project_kpi", "project_id", "kpi_name"),
        Index("ix_kpi_targets_project_period", "project_id", "period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    kpi_name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    tolerance_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.1, server_default="0.1"
    )
    # business_plan, investment_memo, manual
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="business_plan", server_default="business_plan"
    )

    def __repr__(self) -> str:
        return f"<KPITarget(id={self.id}, kpi={self.kpi_name!r}, period={self.period!r})>"
