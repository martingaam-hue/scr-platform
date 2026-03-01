"""Industry taxonomy — NACE/GICS aligned hierarchical codes."""

from __future__ import annotations

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class IndustryTaxonomy(BaseModel):
    """Hierarchical taxonomy node. Leaf nodes have full dot-separated codes."""

    __tablename__ = "industry_taxonomy"

    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    parent_code: Mapped[str | None] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    level: Mapped[int] = mapped_column(nullable=False, default=1)  # 1=sector, 2=industry, 3=sub-industry
    is_leaf: Mapped[bool] = mapped_column(default=False)
    nace_code: Mapped[str | None] = mapped_column(String(20))
    gics_code: Mapped[str | None] = mapped_column(String(20))
    # Extra metadata (unit hints, regulatory refs, etc.)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
