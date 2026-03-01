"""Metric snapshot and benchmark aggregate models for time-series analytics."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import ModelMixin


class MetricSnapshot(Base, ModelMixin):
    """Point-in-time recording of any platform metric. Enables trend analysis,
    benchmarking, and 'why did it change?' explainability."""
    __tablename__ = "metric_snapshots"
    __table_args__ = (
        Index("ix_metric_snapshots_lookup", "entity_type", "entity_id", "metric_name", "recorded_at"),
        Index("ix_metric_snapshots_time_range", "metric_name", "recorded_at"),
        Index("ix_metric_snapshots_org", "org_id", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    previous_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, default={})
    trigger_event: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trigger_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BenchmarkAggregate(Base, ModelMixin):
    """Pre-computed benchmark statistics. Refreshed nightly.
    Enables: 'Your solar project in Spain is in the top quartile for IRR.'"""
    __tablename__ = "benchmark_aggregates"
    __table_args__ = (
        UniqueConstraint(
            "asset_class", "geography", "stage", "vintage_year", "metric_name", "period",
            name="uq_benchmark_aggregate"
        ),
        Index("ix_benchmark_lookup", "asset_class", "geography", "metric_name", "period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=func.gen_random_uuid()
    )
    asset_class: Mapped[str] = mapped_column(String(50), nullable=False)
    geography: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vintage_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)

    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    median: Mapped[float | None] = mapped_column(Float, nullable=True)
    p25: Mapped[float | None] = mapped_column(Float, nullable=True)
    p75: Mapped[float | None] = mapped_column(Float, nullable=True)
    p10: Mapped[float | None] = mapped_column(Float, nullable=True)
    p90: Mapped[float | None] = mapped_column(Float, nullable=True)
    std_dev: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_val: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_val: Mapped[float | None] = mapped_column(Float, nullable=True)

    period: Mapped[str] = mapped_column(String(20), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
