"""add deal stage transitions

Revision ID: a7b8c9d0e1f2
Revises: f3a9d1e72b08
Create Date: 2026-02-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f2"
down_revision = "f3a9d1e72b08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deal_stage_transitions",
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
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "investor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("from_stage", sa.String(50), nullable=True),
        sa.Column("to_stage", sa.String(50), nullable=False),
        sa.Column("reason", sa.String(100), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "transitioned_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_deal_flow_org_date",
        "deal_stage_transitions",
        ["org_id", "created_at"],
    )
    op.create_index(
        "ix_deal_flow_project",
        "deal_stage_transitions",
        ["project_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_deal_flow_project", table_name="deal_stage_transitions")
    op.drop_index("ix_deal_flow_org_date", table_name="deal_stage_transitions")
    op.drop_table("deal_stage_transitions")
