"""Capital Efficiency schemas."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, computed_field


class EfficiencyMetricsResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    portfolio_id: uuid.UUID | None
    period_start: date
    period_end: date
    due_diligence_savings: float
    legal_automation_savings: float
    risk_analytics_savings: float
    tax_credit_value_captured: float
    time_saved_hours: float
    deals_screened: int
    deals_closed: int
    avg_time_to_close_days: float
    portfolio_irr_improvement: float | None
    industry_avg_dd_cost: float
    industry_avg_time_to_close: float
    platform_efficiency_score: float
    total_savings: float  # computed: sum of 4 savings categories
    breakdown: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    is_demo: bool = False

    model_config = {"from_attributes": True}


class EfficiencyBreakdownResponse(BaseModel):
    categories: list[dict[str, Any]]  # [{name, value, percentage, vs_industry}]
    totals: dict[str, float]


class BenchmarkResponse(BaseModel):
    platform: dict[str, float]
    industry_avg: dict[str, float]
    percentile: int  # 0-100
    outperforming: list[str]  # dimensions where platform beats industry
