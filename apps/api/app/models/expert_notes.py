"""SQLAlchemy model for expert notes."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import ModelMixin


class ExpertNote(Base, ModelMixin):
    """Expert insights note — call notes, site visits, expert interviews, etc."""

    __tablename__ = "expert_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    note_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_takeaways: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    risk_factors_identified: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    linked_signal_dimensions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    participants: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    meeting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    enrichment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending", default="pending"
    )
    is_private: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
