"""Market Data Enrichment models — DataSource registry, fetch logs, raw/processed data, review queue."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class MarketDataSource(BaseModel):
    """Registry of data sources with legal_basis tracking and tier classification."""

    __tablename__ = "market_data_sources"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # "official_api" | "rss_feed" | "document" | "manual"
    tier: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # 1=Official APIs, 2=RSS, 3=Documents, 4=Manual
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    legal_basis: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="public_data"
    )  # "public_data" | "licensed" | "fair_use" | "manual_entry"
    rate_limit_per_hour: Mapped[int] = mapped_column(Integer, default=60, server_default="60")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("org_id", "slug", name="uq_market_data_source_slug"),
        Index("ix_market_data_sources_org_id", "org_id"),
        Index("ix_market_data_sources_tier", "tier"),
        Index("ix_market_data_sources_is_active", "is_active"),
    )


class MarketEnrichmentFetchLog(BaseModel):
    """Log of each data fetch attempt — status, record counts, errors."""

    __tablename__ = "market_enrichment_fetch_logs"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("market_data_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending"
    )  # "pending" | "running" | "success" | "failed" | "rate_limited"
    records_fetched: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    records_new: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    records_updated: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_enrichment_fetch_log_org", "org_id"),
        Index("ix_enrichment_fetch_log_source", "source_id"),
        Index("ix_enrichment_fetch_log_status", "status"),
    )


class MarketDataRaw(BaseModel):
    """Raw payload from each data source — stored verbatim for auditability."""

    __tablename__ = "market_data_raw"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("market_data_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    fetch_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("market_enrichment_fetch_logs.id", ondelete="SET NULL"),
        nullable=True,
    )
    external_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("org_id", "source_id", "content_hash", name="uq_market_data_raw_dedup"),
        Index("ix_market_data_raw_content_hash", "content_hash"),
        Index("ix_market_data_raw_source", "source_id"),
        Index("ix_market_data_raw_org", "org_id"),
    )


class MarketDataProcessed(BaseModel):
    """Structured data extracted from raw records — typed, unit-aware, reviewable."""

    __tablename__ = "market_data_processed"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    raw_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("market_data_raw.id", ondelete="SET NULL"),
        nullable=True,
    )
    data_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "price" | "policy" | "project_pipeline" | "macro_indicator" | "news"
    category: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "solar_ppi", "capacity_factor", "feed_in_tariff"
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    technology: Mapped[str | None] = mapped_column(String(100), nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "USD/MWh", "MW", "%"
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), default=1.0, server_default="1.0")
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="auto_accepted"
    )  # "pending_review" | "auto_accepted" | "approved" | "rejected"
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_market_data_processed_data_type", "data_type"),
        Index("ix_market_data_processed_effective_date", "effective_date"),
        Index("ix_market_data_processed_org", "org_id"),
        Index("ix_market_data_processed_review_status", "review_status"),
    )


class DataReviewQueue(BaseModel):
    """Human review queue for low-confidence or anomalous data points."""

    __tablename__ = "data_review_queue"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    processed_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("market_data_processed.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_data_review_queue_org", "org_id"),
        Index("ix_data_review_queue_processed", "processed_id"),
    )
