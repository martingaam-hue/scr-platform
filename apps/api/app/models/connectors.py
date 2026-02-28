"""Data connector catalog and org-level configuration models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TimestampedModel


class DataConnector(BaseModel):
    """Platform-level catalog of available third-party data connectors."""

    __tablename__ = "data_connectors"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # market_data, esg, property, energy, company, weather
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auth_type: Mapped[str] = mapped_column(String(20), default="api_key")  # api_key, oauth2, basic, none
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    pricing_tier: Mapped[str] = mapped_column(String(20), default="free")  # free, professional, enterprise
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    documentation_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class OrgConnectorConfig(BaseModel):
    """Per-organisation connector enablement and credentials."""

    __tablename__ = "org_connector_configs"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    connector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_connectors.id", ondelete="CASCADE"), nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    api_key_encrypted: Mapped[str | None] = mapped_column(String(1000), nullable=True)  # AES-256-GCM
    config: Mapped[dict] = mapped_column(JSONB, default=dict)  # connector-specific settings
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    total_calls_this_month: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    __table_args__ = (
        UniqueConstraint("org_id", "connector_id", name="uq_org_connector"),
        Index("ix_org_connector_config_org", "org_id"),
    )


class DataFetchLog(TimestampedModel):
    """Immutable log of each API call made through a connector."""

    __tablename__ = "data_fetch_logs"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    connector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_connectors.id", ondelete="CASCADE"), nullable=False
    )
    endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    __table_args__ = (
        Index("ix_fetch_log_org_connector", "org_id", "connector_id"),
        Index("ix_fetch_log_created", "created_at"),
    )
