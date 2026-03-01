"""Add custom_domains table for E03 Custom Domain feature.

Revision ID: h1a2b3c4d5e6
Revises: g2a2b3c4d5e6
Create Date: 2026-03-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "h1a2b3c4d5e6"
down_revision = "g2a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "custom_domains",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("cname_target", sa.String(255), nullable=False),
        sa.Column("verification_token", sa.String(100), nullable=False),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "ssl_provisioned_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_checked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("org_id", name="uq_custom_domain_org"),
        sa.UniqueConstraint("domain", name="uq_custom_domain_domain"),
    )
    op.create_index("ix_custom_domains_org_id", "custom_domains", ["org_id"])
    op.create_index("ix_custom_domain_status", "custom_domains", ["status"])


def downgrade() -> None:
    op.drop_index("ix_custom_domain_status", table_name="custom_domains")
    op.drop_index("ix_custom_domains_org_id", table_name="custom_domains")
    op.drop_table("custom_domains")
