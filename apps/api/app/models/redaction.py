"""SQLAlchemy model for AI document redaction jobs."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import ModelMixin


class RedactionJob(Base, ModelMixin):
    """Tracks a single PII-detection + redaction workflow for a document.

    Lifecycle: pending → analyzing → review → applying → done | failed
    """

    __tablename__ = "redaction_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default="gen_random_uuid()",
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    # pending | analyzing | review | applying | done | failed
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    # List of detected PII entity dicts (each includes id, entity_type, text, page, confidence, position, is_high_sensitivity)
    detected_entities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Subset of detected_entities approved by the user for actual redaction
    approved_redactions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # UUID of the newly created redacted document in the data room (nullable until done)
    redacted_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    redacted_s3_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    approved_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="now()"
    )
