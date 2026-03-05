"""add market enrichment tables

Revision ID: k1a2b3c4d5e6
Revises: j1a2b3c4d5e6
Create Date: 2026-03-05 10:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "k1a2b3c4d5e6"
down_revision = "j1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── market_data_sources ───────────────────────────────────────────────────
    op.create_table(
        "market_data_sources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("tier", sa.Integer, nullable=False),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("legal_basis", sa.String(50), nullable=False, server_default="public_data"),
        sa.Column("rate_limit_per_hour", sa.Integer, nullable=False, server_default="60"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "slug", name="uq_market_data_source_slug"),
    )
    op.create_index("ix_market_data_sources_org_id", "market_data_sources", ["org_id"])
    op.create_index("ix_market_data_sources_tier", "market_data_sources", ["tier"])
    op.create_index("ix_market_data_sources_is_active", "market_data_sources", ["is_active"])

    # ── market_enrichment_fetch_logs ──────────────────────────────────────────
    op.create_table(
        "market_enrichment_fetch_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("records_fetched", sa.Integer, nullable=False, server_default="0"),
        sa.Column("records_new", sa.Integer, nullable=False, server_default="0"),
        sa.Column("records_updated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(2000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["market_data_sources.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_enrichment_fetch_log_org", "market_enrichment_fetch_logs", ["org_id"])
    op.create_index(
        "ix_enrichment_fetch_log_source", "market_enrichment_fetch_logs", ["source_id"]
    )
    op.create_index(
        "ix_enrichment_fetch_log_status", "market_enrichment_fetch_logs", ["status"]
    )

    # ── market_data_raw ───────────────────────────────────────────────────────
    op.create_table(
        "market_data_raw",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fetch_log_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_id", sa.String(500), nullable=True),
        sa.Column("raw_content", postgresql.JSONB, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_id"], ["market_data_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["fetch_log_id"], ["market_enrichment_fetch_logs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id", "source_id", "content_hash", name="uq_market_data_raw_dedup"
        ),
    )
    op.create_index("ix_market_data_raw_content_hash", "market_data_raw", ["content_hash"])
    op.create_index("ix_market_data_raw_source", "market_data_raw", ["source_id"])
    op.create_index("ix_market_data_raw_org", "market_data_raw", ["org_id"])

    # ── market_data_processed ─────────────────────────────────────────────────
    op.create_table(
        "market_data_processed",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("data_type", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("technology", sa.String(100), nullable=True),
        sa.Column("effective_date", sa.Date, nullable=True),
        sa.Column("value_numeric", sa.Numeric(20, 6), nullable=True),
        sa.Column("value_text", sa.Text, nullable=True),
        sa.Column("value_json", postgresql.JSONB, nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False, server_default="1.0"),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column(
            "review_status", sa.String(20), nullable=False, server_default="auto_accepted"
        ),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["raw_id"], ["market_data_raw.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_market_data_processed_data_type", "market_data_processed", ["data_type"]
    )
    op.create_index(
        "ix_market_data_processed_effective_date", "market_data_processed", ["effective_date"]
    )
    op.create_index("ix_market_data_processed_org", "market_data_processed", ["org_id"])
    op.create_index(
        "ix_market_data_processed_review_status", "market_data_processed", ["review_status"]
    )

    # ── data_review_queue ─────────────────────────────────────────────────────
    op.create_table(
        "data_review_queue",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processed_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["processed_id"], ["market_data_processed.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_review_queue_org", "data_review_queue", ["org_id"])
    op.create_index("ix_data_review_queue_processed", "data_review_queue", ["processed_id"])


def downgrade() -> None:
    op.drop_index("ix_data_review_queue_processed", "data_review_queue")
    op.drop_index("ix_data_review_queue_org", "data_review_queue")
    op.drop_table("data_review_queue")

    op.drop_index("ix_market_data_processed_review_status", "market_data_processed")
    op.drop_index("ix_market_data_processed_org", "market_data_processed")
    op.drop_index("ix_market_data_processed_effective_date", "market_data_processed")
    op.drop_index("ix_market_data_processed_data_type", "market_data_processed")
    op.drop_table("market_data_processed")

    op.drop_index("ix_market_data_raw_org", "market_data_raw")
    op.drop_index("ix_market_data_raw_source", "market_data_raw")
    op.drop_index("ix_market_data_raw_content_hash", "market_data_raw")
    op.drop_table("market_data_raw")

    op.drop_index("ix_enrichment_fetch_log_status", "market_enrichment_fetch_logs")
    op.drop_index("ix_enrichment_fetch_log_source", "market_enrichment_fetch_logs")
    op.drop_index("ix_enrichment_fetch_log_org", "market_enrichment_fetch_logs")
    op.drop_table("market_enrichment_fetch_logs")

    op.drop_index("ix_market_data_sources_is_active", "market_data_sources")
    op.drop_index("ix_market_data_sources_tier", "market_data_sources")
    op.drop_index("ix_market_data_sources_org_id", "market_data_sources")
    op.drop_table("market_data_sources")
