"""add_crm_sync

Revision ID: c5a2b3c4d5e6
Revises: aa1122334455, f1a2b3c4d5e6
Create Date: 2026-03-01 10:00:00.000000

Creates crm_connections, crm_sync_logs, and crm_entity_mappings tables
for the C05 CRM Sync (HubSpot) feature.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c5a2b3c4d5e6"
down_revision: Union[str, tuple[str, ...]] = ("aa1122334455", "f1a2b3c4d5e6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # crm_connections
    op.create_table(
        "crm_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("portal_id", sa.String(length=100), nullable=True),
        sa.Column("instance_url", sa.String(length=500), nullable=True),
        sa.Column("field_mappings", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("sync_frequency", sa.String(length=20), server_default="15min", nullable=False),
        sa.Column("sync_direction", sa.String(length=20), server_default="bidirectional", nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_connections_org_id", "crm_connections", ["org_id"])

    # crm_sync_logs
    op.create_table(
        "crm_sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("scr_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("crm_entity_id", sa.String(length=100), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["crm_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_sync_logs_connection_id", "crm_sync_logs", ["connection_id"])

    # crm_entity_mappings
    op.create_table(
        "crm_entity_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scr_entity_type", sa.String(length=50), nullable=False),
        sa.Column("scr_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("crm_entity_type", sa.String(length=50), nullable=False),
        sa.Column("crm_entity_id", sa.String(length=100), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["crm_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("connection_id", "scr_entity_type", "scr_entity_id", name="uq_crm_entity_mapping_scr"),
    )
    op.create_index("ix_crm_entity_mappings_connection_id", "crm_entity_mappings", ["connection_id"])


def downgrade() -> None:
    op.drop_index("ix_crm_entity_mappings_connection_id", table_name="crm_entity_mappings")
    op.drop_table("crm_entity_mappings")
    op.drop_index("ix_crm_sync_logs_connection_id", table_name="crm_sync_logs")
    op.drop_table("crm_sync_logs")
    op.drop_index("ix_crm_connections_org_id", table_name="crm_connections")
    op.drop_table("crm_connections")
