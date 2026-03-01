"""Add launch features: feature_flags, usage_events, waitlist.

Revision ID: g2a2b3c4d5e6
Revises: g1a2b3c4d5e6
Create Date: 2026-03-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "g2a2b3c4d5e6"
down_revision = "g1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── feature_flags ─────────────────────────────────────────────────────────
    op.create_table(
        "feature_flags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "enabled_globally",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "rollout_pct",
            sa.Integer,
            nullable=False,
            server_default=sa.text("100"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("name", name="uq_feature_flags_name"),
    )
    op.create_index("ix_feature_flags_name", "feature_flags", ["name"])

    # ── feature_flag_overrides ────────────────────────────────────────────────
    op.create_table(
        "feature_flag_overrides",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "flag_name",
            sa.String(100),
            sa.ForeignKey("feature_flags.name", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("flag_name", "org_id", name="uq_flag_override_org"),
    )
    op.create_index(
        "ix_feature_flag_overrides_org_id",
        "feature_flag_overrides",
        ["org_id"],
    )
    op.create_index(
        "ix_feature_flag_overrides_flag_name",
        "feature_flag_overrides",
        ["flag_name"],
    )

    # ── usage_events ──────────────────────────────────────────────────────────
    op.create_table(
        "usage_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_usage_events_org_id", "usage_events", ["org_id"])
    op.create_index("ix_usage_events_created_at", "usage_events", ["created_at"])
    op.create_index("ix_usage_events_event_type", "usage_events", ["event_type"])

    # ── waitlist_entries ──────────────────────────────────────────────────────
    op.create_table(
        "waitlist_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("use_case", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("email", name="uq_waitlist_email"),
    )
    op.create_index("ix_waitlist_entries_email", "waitlist_entries", ["email"])
    op.create_index("ix_waitlist_entries_status", "waitlist_entries", ["status"])


def downgrade() -> None:
    op.drop_index("ix_waitlist_entries_status", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_entries_email", table_name="waitlist_entries")
    op.drop_table("waitlist_entries")

    op.drop_index("ix_usage_events_event_type", table_name="usage_events")
    op.drop_index("ix_usage_events_created_at", table_name="usage_events")
    op.drop_index("ix_usage_events_org_id", table_name="usage_events")
    op.drop_table("usage_events")

    op.drop_index(
        "ix_feature_flag_overrides_flag_name", table_name="feature_flag_overrides"
    )
    op.drop_index(
        "ix_feature_flag_overrides_org_id", table_name="feature_flag_overrides"
    )
    op.drop_table("feature_flag_overrides")

    op.drop_index("ix_feature_flags_name", table_name="feature_flags")
    op.drop_table("feature_flags")
