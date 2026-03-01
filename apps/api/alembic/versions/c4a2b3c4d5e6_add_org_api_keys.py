"""Add org_api_keys table for per-org programmatic access credentials.

Revision ID: c4a2b3c4d5e6
Revises: aa1122334455, f1a2b3c4d5e6
Create Date: 2026-03-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4a2b3c4d5e6"
down_revision: Union[str, tuple[str, ...]] = ("aa1122334455", "f1a2b3c4d5e6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "org_api_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
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
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{read}",
        ),
        sa.Column(
            "rate_limit_per_min",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            ondelete="CASCADE",
            name="fk_org_api_keys_org_id",
        ),
        sa.UniqueConstraint("key_hash", name="uq_org_api_keys_key_hash"),
    )
    op.create_index("ix_org_api_keys_org_id", "org_api_keys", ["org_id"])
    op.create_index("ix_org_api_keys_key_hash", "org_api_keys", ["key_hash"])


def downgrade() -> None:
    op.drop_index("ix_org_api_keys_key_hash", table_name="org_api_keys")
    op.drop_index("ix_org_api_keys_org_id", table_name="org_api_keys")
    op.drop_table("org_api_keys")
