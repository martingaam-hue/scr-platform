"""add metric snapshots and benchmark aggregates

Revision ID: a1b2c3d4e5f6
Revises: ff0011223344
Create Date: 2026-03-01 10:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a9b8c7d6e5f4"
down_revision = ("ff0011223344", "aa9988776655")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "metric_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("previous_value", sa.Float, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("trigger_event", sa.String(100), nullable=True),
        sa.Column("trigger_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metric_snapshots_lookup", "metric_snapshots", ["entity_type", "entity_id", "metric_name", "recorded_at"])
    op.create_index("ix_metric_snapshots_time_range", "metric_snapshots", ["metric_name", "recorded_at"])
    op.create_index("ix_metric_snapshots_org", "metric_snapshots", ["org_id", "recorded_at"])

    op.create_table(
        "benchmark_aggregates",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("asset_class", sa.String(50), nullable=False),
        sa.Column("geography", sa.String(100), nullable=True),
        sa.Column("stage", sa.String(50), nullable=True),
        sa.Column("vintage_year", sa.Integer, nullable=True),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("count", sa.Integer, server_default="0", nullable=False),
        sa.Column("mean", sa.Float, nullable=True),
        sa.Column("median", sa.Float, nullable=True),
        sa.Column("p25", sa.Float, nullable=True),
        sa.Column("p75", sa.Float, nullable=True),
        sa.Column("p10", sa.Float, nullable=True),
        sa.Column("p90", sa.Float, nullable=True),
        sa.Column("std_dev", sa.Float, nullable=True),
        sa.Column("min_val", sa.Float, nullable=True),
        sa.Column("max_val", sa.Float, nullable=True),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_class", "geography", "stage", "vintage_year", "metric_name", "period", name="uq_benchmark_aggregate"),
    )
    op.create_index("ix_benchmark_lookup", "benchmark_aggregates", ["asset_class", "geography", "metric_name", "period"])


def downgrade() -> None:
    op.drop_table("benchmark_aggregates")
    op.drop_table("metric_snapshots")
