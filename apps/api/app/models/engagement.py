"""Document engagement tracking models: DocumentEngagement, DealEngagementSummary."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import ModelMixin


class DocumentEngagement(Base, ModelMixin):
    """Records a single viewer session for a document.

    Tracks open/close times, pages viewed with per-page dwell time,
    downloads and prints. Used to compute per-investor engagement scores.
    """

    __tablename__ = "document_engagements"
    __table_args__ = (
        Index("ix_document_engagements_org_id", "org_id"),
        Index("ix_document_engagements_document_id", "document_id"),
        Index("ix_document_engagements_user_id", "user_id"),
        Index("ix_document_engagements_doc_opened", "document_id", "opened_at"),
        Index("ix_document_engagements_user_org", "user_id", "org_id"),
    )

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
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[str] = mapped_column(String(100), nullable=False)

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # [{"page": 1, "time_seconds": 45}, ...]
    pages_viewed: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pages_viewed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    downloaded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    printed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    referrer_page: Mapped[str | None] = mapped_column(String(200), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # desktop, tablet, mobile

    def __repr__(self) -> str:
        return f"<DocumentEngagement(id={self.id}, document_id={self.document_id}, user_id={self.user_id})>"


class DealEngagementSummary(Base, ModelMixin):
    """Pre-aggregated engagement summary per investor per project.

    Refreshed on demand (or via background task) to power the
    Deal Room investor-activity dashboard.
    """

    __tablename__ = "deal_engagement_summaries"
    __table_args__ = (
        Index("ix_deal_engagement_summaries_org_id", "org_id"),
        Index("ix_deal_engagement_summaries_project_id", "project_id"),
        Index("ix_deal_engagement_summaries_project_investor", "project_id", "investor_org_id"),
    )

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
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deal_room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deal_rooms.id", ondelete="SET NULL"),
        nullable=True,
    )
    investor_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    total_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unique_documents_viewed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_documents_available: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    documents_downloaded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    engagement_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<DealEngagementSummary(id={self.id}, project_id={self.project_id}, "
            f"investor_org_id={self.investor_org_id})>"
        )
