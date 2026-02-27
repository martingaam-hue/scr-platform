"""patch2: expand project_type enum to include alternative investment asset classes

Revision ID: 7c4e82b31d09
Revises: f3a9d1e72b08
Create Date: 2026-02-27 13:00:00.000000

Adds 8 new values to the projecttype PostgreSQL enum:
  infrastructure, real_estate, private_equity, natural_resources,
  private_credit, digital_assets, impact, specialty

Existing data (solar, wind, hydro, etc.) is fully preserved.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "7c4e82b31d09"
down_revision: Union[str, None] = "f3a9d1e72b08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_TYPES = [
    "infrastructure",
    "real_estate",
    "private_equity",
    "natural_resources",
    "private_credit",
    "digital_assets",
    "impact",
    "specialty",
]


def upgrade() -> None:
    # PostgreSQL requires ALTER TYPE ... ADD VALUE for enum expansion.
    # Each ADD VALUE is a separate DDL statement and cannot run inside a transaction.
    for value in NEW_TYPES:
        op.execute(
            f"ALTER TYPE projecttype ADD VALUE IF NOT EXISTS '{value}'"
        )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type.
    # A full recreate would require migrating all affected rows; skip for safety.
    pass
