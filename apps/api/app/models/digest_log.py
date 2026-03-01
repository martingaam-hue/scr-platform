"""DigestLog model — append-only record of every sent digest email."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DigestLog(Base):
    """One row per digest email successfully sent to a user."""

    __tablename__ = "digest_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    digest_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="weekly",
        server_default="weekly",
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    data_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_digest_log_org_sent", "org_id", "sent_at"),
        Index("ix_digest_log_user_sent", "user_id", "sent_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<DigestLog(id={self.id}, user_id={self.user_id}, "
            f"digest_type={self.digest_type!r}, sent_at={self.sent_at})>"
        )
