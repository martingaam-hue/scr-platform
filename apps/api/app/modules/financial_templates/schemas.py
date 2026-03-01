import uuid
from decimal import Decimal
from typing import Any
from pydantic import BaseModel

class TemplateComputeRequest(BaseModel):
    """Run DCF computation with override assumptions."""
    overrides: dict[str, Any] = {}  # e.g. {"capacity_mw": 100, "ppa_price_eur_mwh": 60}

class DCFResult(BaseModel):
    npv: Decimal
    irr: Decimal | None
    annual_cashflows: list[Decimal]
    levered_cashflows: list[Decimal]
    assumptions_used: dict[str, Any]
