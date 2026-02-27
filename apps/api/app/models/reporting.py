"""Reporting models: ReportTemplate, GeneratedReport, ScheduledReport."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import ReportCategory, ReportFrequency, ReportStatus


class ReportTemplate(BaseModel):
    __tablename__ = "report_templates"
    __table_args__ = (
        Index("ix_report_templates_org_id", "org_id"),
        Index("ix_report_templates_category", "category"),
    )

    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[ReportCategory] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    template_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    sections: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_system: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    generated_reports: Mapped[list["GeneratedReport"]] = relationship(
        back_populates="template"
    )
    scheduled_reports: Mapped[list["ScheduledReport"]] = relationship(
        back_populates="template"
    )

    def __repr__(self) -> str:
        return f"<ReportTemplate(id={self.id}, name={self.name!r}, category={self.category.value})>"


class GeneratedReport(BaseModel):
    __tablename__ = "generated_reports"
    __table_args__ = (
        Index("ix_generated_reports_org_id", "org_id"),
        Index("ix_generated_reports_template_id", "template_id"),
        Index("ix_generated_reports_status", "status"),
        Index("ix_generated_reports_org_id_status", "org_id", "status"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_templates.id", ondelete="SET NULL"),
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        nullable=False, default=ReportStatus.QUEUED
    )
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    s3_key: Mapped[str | None] = mapped_column(String(1000))
    error_message: Mapped[str | None] = mapped_column(Text)
    generated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column()

    # Relationships
    template: Mapped["ReportTemplate | None"] = relationship(
        back_populates="generated_reports"
    )

    def __repr__(self) -> str:
        return f"<GeneratedReport(id={self.id}, title={self.title!r}, status={self.status.value})>"


class ScheduledReport(BaseModel):
    __tablename__ = "scheduled_reports"
    __table_args__ = (
        Index("ix_scheduled_reports_org_id", "org_id"),
        Index("ix_scheduled_reports_template_id", "template_id"),
        Index("ix_scheduled_reports_is_active", "org_id", "is_active"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    frequency: Mapped[ReportFrequency] = mapped_column(nullable=False)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    recipients: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(
        default=True, server_default="true", nullable=False
    )
    last_run_at: Mapped[datetime | None] = mapped_column()
    next_run_at: Mapped[datetime | None] = mapped_column()

    # Relationships
    template: Mapped["ReportTemplate"] = relationship(
        back_populates="scheduled_reports"
    )

    def __repr__(self) -> str:
        return f"<ScheduledReport(id={self.id}, name={self.name!r}, frequency={self.frequency.value})>"
