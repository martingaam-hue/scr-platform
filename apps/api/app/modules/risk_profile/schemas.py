"""Risk Profile API schemas."""

import uuid
from typing import Any

from pydantic import BaseModel, Field


class AssessmentRequest(BaseModel):
    experience_level: str = Field(..., pattern="^(none|limited|moderate|extensive)$")
    investment_horizon_years: int = Field(..., ge=1, le=30)
    loss_tolerance_percentage: int = Field(..., ge=1, le=100)
    liquidity_needs: str = Field(..., pattern="^(high|moderate|low)$")
    concentration_max_percentage: int = Field(..., ge=1, le=100)
    max_drawdown_tolerance: int = Field(..., ge=1, le=100)


class RiskProfileResponse(BaseModel):
    has_profile: bool
    risk_category: str | None = None
    sophistication_score: float | None = None
    risk_appetite_score: float | None = None
    recommended_allocation: dict[str, int] | None = None
    experience_level: str | None = None
    investment_horizon_years: int | None = None
    loss_tolerance_percentage: int | None = None
    liquidity_needs: str | None = None
    concentration_max_percentage: int | None = None
    max_drawdown_tolerance: int | None = None
