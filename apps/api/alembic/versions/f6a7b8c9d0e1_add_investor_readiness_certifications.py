"""add investor readiness certifications

Revision ID: f6a7b8c9d0e1
Revises: f3a9d1e72b08
Create Date: 2026-02-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f6a7b8c9d0e1"
down_revision = "f3a9d1e72b08"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "investor_readiness_certifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="not_certified"),
        sa.Column("certified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("certification_score", sa.Float, nullable=True),
        sa.Column("dimension_scores", postgresql.JSONB, nullable=True),
        sa.Column("tier", sa.String(20), nullable=True),
        sa.Column("certification_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("consecutive_months_certified", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_certification_project", "investor_readiness_certifications", ["project_id"])
    op.create_index("ix_certification_org_status", "investor_readiness_certifications", ["org_id", "status"])
    op.create_unique_constraint("uq_certification_project", "investor_readiness_certifications", ["project_id"])


def downgrade():
    op.drop_table("investor_readiness_certifications")
