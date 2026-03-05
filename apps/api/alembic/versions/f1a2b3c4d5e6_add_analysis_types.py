"""Add cross-module analysis types to document_extractions

Revision ID: f1a2b3c4d5e6
Revises: d5e6f7a8b9c0
Create Date: 2026-02-28 14:00:00.000000

Adds new extraction_type enum values for the cross-module document analysis cache.
Enum additions are additive-only in PostgreSQL and cannot be rolled back.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE extractiontype ADD VALUE IF NOT EXISTS 'quality_assessment'")
    op.execute("ALTER TYPE extractiontype ADD VALUE IF NOT EXISTS 'risk_flags'")
    op.execute("ALTER TYPE extractiontype ADD VALUE IF NOT EXISTS 'deal_relevance'")
    op.execute("ALTER TYPE extractiontype ADD VALUE IF NOT EXISTS 'completeness_check'")
    op.execute("ALTER TYPE extractiontype ADD VALUE IF NOT EXISTS 'key_figures'")
    op.execute("ALTER TYPE extractiontype ADD VALUE IF NOT EXISTS 'entity_extraction'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values — this migration is additive only
    pass
