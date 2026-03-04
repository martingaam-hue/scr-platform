"""add risk_mitigation_statuses table

Revision ID: j1a2b3c4d5e6
Revises: 8d141fa29a9e
Create Date: 2026-03-04 12:00:00.000000

"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'j1a2b3c4d5e6'
down_revision = '8d141fa29a9e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'risk_mitigation_statuses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('risk_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='unaddressed'),
        sa.Column('evidence_document_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('notes', sa.String(2000), nullable=True),
        sa.Column('guidance', sa.String(2000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_risk_mitigation_statuses_project_id', 'risk_mitigation_statuses', ['project_id'])
    op.create_index('ix_risk_mitigation_statuses_org_id', 'risk_mitigation_statuses', ['org_id'])
    op.create_index('ix_risk_mitigation_statuses_risk_item_id', 'risk_mitigation_statuses', ['risk_item_id'])


def downgrade() -> None:
    op.drop_index('ix_risk_mitigation_statuses_risk_item_id', 'risk_mitigation_statuses')
    op.drop_index('ix_risk_mitigation_statuses_org_id', 'risk_mitigation_statuses')
    op.drop_index('ix_risk_mitigation_statuses_project_id', 'risk_mitigation_statuses')
    op.drop_table('risk_mitigation_statuses')
