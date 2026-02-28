"""add_professional_connections

Revision ID: a4b5c6d7e8f9
Revises: f6a7b8c9d0e1
Create Date: 2026-02-28 00:03:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a4b5c6d7e8f9"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "professional_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_type", sa.String(50), nullable=False),
        sa.Column("connected_org_name", sa.String(200), nullable=False),
        sa.Column("connected_person_name", sa.String(200), nullable=True),
        sa.Column("connected_person_email", sa.String(200), nullable=True),
        sa.Column("relationship_strength", sa.String(20), server_default="moderate", nullable=False),
        sa.Column("last_interaction_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_professional_connections_user_id", "professional_connections", ["user_id"])
    op.create_index("ix_professional_connections_org_id", "professional_connections", ["org_id"])

    op.create_table(
        "introduction_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requester_org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_investor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("warmth_score", sa.Float(), nullable=True),
        sa.Column("introduction_path", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_introduction_requests_requester_id", "introduction_requests", ["requester_id"])
    op.create_index("ix_introduction_requests_requester_org_id", "introduction_requests", ["requester_org_id"])


def downgrade() -> None:
    op.drop_index("ix_introduction_requests_requester_org_id", table_name="introduction_requests")
    op.drop_index("ix_introduction_requests_requester_id", table_name="introduction_requests")
    op.drop_table("introduction_requests")
    op.drop_index("ix_professional_connections_org_id", table_name="professional_connections")
    op.drop_index("ix_professional_connections_user_id", table_name="professional_connections")
    op.drop_table("professional_connections")
