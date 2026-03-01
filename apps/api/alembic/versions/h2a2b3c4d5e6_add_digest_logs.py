"""Add digest_logs table for tracking sent digest emails.

Revision ID: h2a2b3c4d5e6
Revises: h1a2b3c4d5e6
Create Date: 2026-03-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "h2a2b3c4d5e6"
down_revision = "h1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "digest_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "digest_type",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'weekly'"),
        ),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("narrative", sa.Text, nullable=False),
        sa.Column(
            "data_snapshot",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_digest_log_org_sent",
        "digest_logs",
        ["org_id", "sent_at"],
    )
    op.create_index(
        "ix_digest_log_user_sent",
        "digest_logs",
        ["user_id", "sent_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_digest_log_user_sent", table_name="digest_logs")
    op.drop_index("ix_digest_log_org_sent", table_name="digest_logs")
    op.drop_table("digest_logs")
