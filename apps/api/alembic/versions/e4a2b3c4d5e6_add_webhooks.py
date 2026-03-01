"""add_webhooks

Revision ID: e4a2b3c4d5e6
Revises: e2a2b3c4d5e6
Create Date: 2026-03-01 15:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e4a2b3c4d5e6"
down_revision = "e2a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── webhook_subscriptions ─────────────────────────────────────────────────
    op.create_table(
        "webhook_subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("secret", sa.String(255), nullable=False),
        sa.Column(
            "events",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("disabled_reason", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_webhook_subscriptions_org_id", "webhook_subscriptions", ["org_id"]
    )

    # ── webhook_deliveries ────────────────────────────────────────────────────
    op.create_table(
        "webhook_deliveries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["webhook_subscriptions.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_webhook_deliveries_subscription_id",
        "webhook_deliveries",
        ["subscription_id"],
    )
    op.create_index(
        "ix_webhook_deliveries_org_id", "webhook_deliveries", ["org_id"]
    )
    op.create_index(
        "ix_webhook_deliveries_status", "webhook_deliveries", ["status"]
    )
    op.create_index(
        "ix_webhook_deliveries_next_retry_at",
        "webhook_deliveries",
        ["next_retry_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_next_retry_at", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_status", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_org_id", table_name="webhook_deliveries")
    op.drop_index(
        "ix_webhook_deliveries_subscription_id", table_name="webhook_deliveries"
    )
    op.drop_table("webhook_deliveries")
    op.drop_index(
        "ix_webhook_subscriptions_org_id", table_name="webhook_subscriptions"
    )
    op.drop_table("webhook_subscriptions")
