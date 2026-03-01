"""CRM Sync models: CRMConnection, CRMSyncLog, CRMEntityMapping."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import ModelMixin


class CRMConnection(Base, ModelMixin):
    """Stores OAuth credentials and configuration for a CRM provider connection."""

    __tablename__ = "crm_connections"
    __table_args__ = (
        Index("ix_crm_connections_org_id", "org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # hubspot, salesforce

    # OAuth tokens — encrypted at application layer before storing
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    portal_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # HubSpot portal ID
    instance_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Salesforce instance URL

    field_mappings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    # e.g. {"project_name": "dealname", "signal_score": "scr_score__c", ...}

    sync_frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="15min")  # 15min, hourly, daily
    sync_direction: Mapped[str] = mapped_column(String(20), nullable=False, default="bidirectional")  # push, pull, bidirectional
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<CRMConnection(id={self.id}, org_id={self.org_id}, provider={self.provider!r})>"


class CRMSyncLog(Base, ModelMixin):
    """Append-only log of individual sync operations."""

    __tablename__ = "crm_sync_logs"
    __table_args__ = (
        Index("ix_crm_sync_logs_connection_id", "connection_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # push, pull
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # deal, contact, activity
    scr_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    crm_entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # create, update, skip
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success, error, conflict
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<CRMSyncLog(id={self.id}, direction={self.direction!r}, status={self.status!r})>"


class CRMEntityMapping(Base, ModelMixin):
    """Tracks the mapping between SCR entities and their CRM counterparts."""

    __tablename__ = "crm_entity_mappings"
    __table_args__ = (
        Index("ix_crm_entity_mappings_connection_id", "connection_id"),
        UniqueConstraint(
            "connection_id", "scr_entity_type", "scr_entity_id",
            name="uq_crm_entity_mapping_scr",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crm_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scr_entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scr_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    crm_entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    crm_entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<CRMEntityMapping(id={self.id}, "
            f"scr={self.scr_entity_type}/{self.scr_entity_id}, "
            f"crm={self.crm_entity_type}/{self.crm_entity_id})>"
        )
