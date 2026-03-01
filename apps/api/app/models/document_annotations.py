"""SQLAlchemy model for document annotations (highlights, notes, bookmarks)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import ModelMixin


class DocumentAnnotation(Base, ModelMixin):
    """An annotation placed on a specific page of a document.

    Supports highlight, note, bookmark, and question_link types. The ``position``
    JSONB field stores normalised coordinates (percentage-based) so annotations
    scale correctly regardless of zoom level:
    ``{x, y, width, height, rects: [{x, y, w, h}]}``
    """

    __tablename__ = "document_annotations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default="gen_random_uuid()",
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    # highlight | note | bookmark | question_link
    annotation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(
        String(20), nullable=False, default="#FFFF00", server_default="#FFFF00"
    )
    linked_qa_question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    linked_citation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    is_private: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="now()"
    )
