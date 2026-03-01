"""Financial templates tied to taxonomy codes."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class FinancialTemplate(BaseModel):
    """A DCF/cashflow template for a specific taxonomy leaf node."""

    __tablename__ = "financial_templates"

    taxonomy_code: Mapped[str] = mapped_column(String(50), ForeignKey("industry_taxonomy.code", ondelete="CASCADE"), nullable=False, index=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)  # NULL = public/system template
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # Assumption sliders: {"capex_per_mw": {"default": 800000, "min": 500000, "max": 1200000, "unit": "EUR/MW"}, ...}
    assumptions: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Revenue formula as a JSON computation graph or formula string
    revenue_formula: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Cashflow model parameters
    cashflow_model: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_system: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        UniqueConstraint("taxonomy_code", "org_id", "name", name="uq_template_name_per_org"),
    )
