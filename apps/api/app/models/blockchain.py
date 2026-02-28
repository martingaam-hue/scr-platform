"""Blockchain audit trail anchor models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class BlockchainAnchor(BaseModel):
    """Immutable blockchain proof for a critical platform event."""

    __tablename__ = "blockchain_anchors"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # document_upload, signal_score, certification, deal_transition, lp_report_approval
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Cryptographic proof
    data_hash: Mapped[str] = mapped_column(String(66), nullable=False)   # SHA-256 hex
    merkle_root: Mapped[str | None] = mapped_column(String(66), nullable=True)
    merkle_proof: Mapped[str | None] = mapped_column(String(4000), nullable=True)  # JSON proof path

    # Blockchain record
    chain: Mapped[str] = mapped_column(String(20), default="polygon", server_default="polygon")
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True, index=True)
    block_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    anchored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Batch grouping
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )  # pending, anchored, failed

    __table_args__ = (
        Index("ix_anchor_entity", "entity_type", "entity_id"),
        Index("ix_anchor_org_status", "org_id", "status"),
    )
