"""fix_projecttype_enum_casing

Revision ID: ff0011223344
Revises: a0b1c2d3e4f5, b1c2d3e4f5a6, c2d3e4f5a6b7, d3e4f5a6b7c8, e4f5a6b7c8d9, e8f9a0b1c2d3, f9a0b1c2d3e4
Create Date: 2026-02-28 20:00:00.000000

"""
from __future__ import annotations

from alembic import op

revision = "ff0011223344"
down_revision = (
    "a0b1c2d3e4f5",
    "b1c2d3e4f5a6",
    "c2d3e4f5a6b7",
    "d3e4f5a6b7c8",
    "e4f5a6b7c8d9",
    "e8f9a0b1c2d3",
    "f9a0b1c2d3e4",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename lowercase projecttype enum values to match SQLAlchemy's uppercase NAME convention
    op.execute("ALTER TYPE projecttype RENAME VALUE 'infrastructure' TO 'INFRASTRUCTURE'")
    op.execute("ALTER TYPE projecttype RENAME VALUE 'real_estate' TO 'REAL_ESTATE'")
    op.execute("ALTER TYPE projecttype RENAME VALUE 'private_equity' TO 'PRIVATE_EQUITY'")
    op.execute("ALTER TYPE projecttype RENAME VALUE 'natural_resources' TO 'NATURAL_RESOURCES'")
    op.execute("ALTER TYPE projecttype RENAME VALUE 'private_credit' TO 'PRIVATE_CREDIT'")
    op.execute("ALTER TYPE projecttype RENAME VALUE 'digital_assets' TO 'DIGITAL_ASSETS'")
    op.execute("ALTER TYPE projecttype RENAME VALUE 'impact' TO 'IMPACT'")
    op.execute("ALTER TYPE projecttype RENAME VALUE 'specialty' TO 'SPECIALTY'")


def downgrade() -> None:
    op.execute("ALTER TYPE projecttype RENAME VALUE 'INFRASTRUCTURE' TO 'infrastructure'")
    op.execute("ALTER TYPE projecttype RENAME VALUE 'REAL_ESTATE' TO 'real_estate'")
    op.execute("ALTER TYPE projecttype RENAME VALUE 'PRIVATE_EQUITY' TO 'private_equity'")
    op.execute("ALTER TYPE projecttype RENAME VALUE 'NATURAL_RESOURCES' TO 'natural_resources'")
    op.execute("ALTER TYPE projecttype RENAME VALUE 'PRIVATE_CREDIT' TO 'private_credit'")
    op.execute("ALTER TYPE projecttype RENAME VALUE 'DIGITAL_ASSETS' TO 'digital_assets'")
    op.execute("ALTER TYPE projecttype RENAME VALUE 'IMPACT' TO 'impact'")
    op.execute("ALTER TYPE projecttype RENAME VALUE 'SPECIALTY' TO 'specialty'")
