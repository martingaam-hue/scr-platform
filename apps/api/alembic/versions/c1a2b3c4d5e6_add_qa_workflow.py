"""add qa_workflow tables

Revision ID: c1a2b3c4d5e6
Revises: ("aa1122334455", "f1a2b3c4d5e6")
Create Date: 2026-03-01 12:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c1a2b3c4d5e6"
down_revision = ("aa1122334455", "f1a2b3c4d5e6")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "qa_questions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deal_room_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_number", sa.Integer, nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(20), server_default="normal", nullable=False),
        sa.Column("asked_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_team", sa.String(50), nullable=True),
        sa.Column("status", sa.String(30), server_default="open", nullable=False),
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sla_breached", sa.Boolean, server_default="false", nullable=False),
        sa.Column(
            "linked_documents",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
        sa.Column("tags", postgresql.ARRAY(sa.String), nullable=True),
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
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deal_room_id"], ["deal_rooms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asked_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qa_questions_org_id", "qa_questions", ["org_id"])
    op.create_index("ix_qa_questions_project_id", "qa_questions", ["project_id"])
    op.create_index("ix_qa_questions_org_project", "qa_questions", ["org_id", "project_id"])
    op.create_index("ix_qa_questions_status", "qa_questions", ["status"])
    op.create_index("ix_qa_questions_project_status", "qa_questions", ["project_id", "status"])

    op.create_table(
        "qa_answers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("answered_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_official", sa.Boolean, server_default="false", nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "linked_documents",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
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
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.ForeignKeyConstraint(
            ["question_id"], ["qa_questions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["answered_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qa_answers_question_id", "qa_answers", ["question_id"])
    op.create_index("ix_qa_answers_answered_by", "qa_answers", ["answered_by"])


def downgrade() -> None:
    op.drop_index("ix_qa_answers_answered_by", table_name="qa_answers")
    op.drop_index("ix_qa_answers_question_id", table_name="qa_answers")
    op.drop_table("qa_answers")

    op.drop_index("ix_qa_questions_project_status", table_name="qa_questions")
    op.drop_index("ix_qa_questions_status", table_name="qa_questions")
    op.drop_index("ix_qa_questions_org_project", table_name="qa_questions")
    op.drop_index("ix_qa_questions_project_id", table_name="qa_questions")
    op.drop_index("ix_qa_questions_org_id", table_name="qa_questions")
    op.drop_table("qa_questions")
