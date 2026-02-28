"""Due Diligence Checklist models."""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class DDChecklistTemplate(BaseModel):
    __tablename__ = "dd_checklist_templates"
    __table_args__ = (
        Index("ix_dd_template_type_stage", "asset_type", "deal_stage"),
    )

    asset_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    deal_stage: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    jurisdiction_group: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class DDChecklistItem(BaseModel):
    __tablename__ = "dd_checklist_items"

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dd_checklist_templates.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    required_document_types: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    verification_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="required", server_default="required")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    estimated_time_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    regulatory_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)


class DDProjectChecklist(BaseModel):
    __tablename__ = "dd_project_checklists"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dd_checklist_templates.id"),
        nullable=False
    )
    investor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="in_progress", server_default="in_progress")
    completion_percentage: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    total_items: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    completed_items: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    custom_items: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")


class DDItemStatus(BaseModel):
    __tablename__ = "dd_item_statuses"
    __table_args__ = (
        UniqueConstraint("checklist_id", "item_id", name="uq_dd_item_status"),
        Index("ix_dd_item_status_checklist", "checklist_id"),
    )

    checklist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dd_project_checklists.id", ondelete="CASCADE"),
        nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dd_checklist_items.id", ondelete="CASCADE"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    satisfied_by_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    ai_review_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
