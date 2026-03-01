"""Data Lineage model — traces computed values back to their sources."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import ModelMixin


class DataLineage(Base, ModelMixin):
    """Traces any computed value back to its source."""
    __tablename__ = "data_lineage"
    __table_args__ = (
        Index("ix_lineage_entity", "entity_type", "entity_id", "field_name"),
        Index("ix_lineage_org", "org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    field_value: Mapped[str | None] = mapped_column(String(500), nullable=True)

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # document_extraction, manual_entry, api_connector, ai_generated, computed, user_input
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)

    source_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    computation_chain: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
