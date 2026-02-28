"""Compliance deadline & regulatory calendar models."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ComplianceDeadline(BaseModel):
    """Regulatory / compliance deadline with reminder tracking."""

    __tablename__ = "compliance_deadlines"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="SET NULL"), nullable=True
    )

    # Classification
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # regulatory_filing, tax, environmental, permit, license, insurance, reporting, sfdr
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    regulatory_body: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Scheduling
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    recurrence: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # monthly, quarterly, annually, one_time

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="upcoming", server_default="upcoming"
    )  # upcoming, in_progress, completed, overdue, waived
    priority: Mapped[str] = mapped_column(
        String(10), default="high", server_default="high"
    )  # critical, high, medium, low

    # Assignment
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Reminder flags — set True once notification sent
    reminder_30d_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    reminder_14d_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    reminder_7d_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    reminder_1d_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    __table_args__ = (
        Index("ix_compliance_org_due", "org_id", "due_date"),
        Index("ix_compliance_org_status", "org_id", "status"),
    )
