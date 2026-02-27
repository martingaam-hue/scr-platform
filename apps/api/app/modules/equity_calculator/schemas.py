"""Equity Calculator schemas — all calculations are deterministic Python."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


class EquityScenarioRequest(BaseModel):
    scenario_name: str
    project_id: uuid.UUID | None = None
    description: str | None = None
    pre_money_valuation: float
    investment_amount: float
    security_type: str = "common_equity"  # common_equity, preferred_equity, convertible_note, safe
    shares_outstanding_before: int = 1_000_000
    liquidation_preference: float | None = None
    participation_cap: float | None = None
    anti_dilution_type: str = "none"  # none, broad_based, narrow_based, full_ratchet
    vesting_cliff_months: int | None = None
    vesting_total_months: int | None = None


class WaterfallScenario(BaseModel):
    multiple: float
    exit_value: float
    investor_proceeds: float
    founder_proceeds: float
    investor_moic: float
    investor_irr_estimate: float | None  # None if holding period unknown


class CapTableEntry(BaseModel):
    name: str
    shares: int
    percentage: float
    investment: float | None


class EquityScenarioResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID | None
    scenario_name: str
    description: str | None
    pre_money_valuation: float
    investment_amount: float
    security_type: str
    equity_percentage: float
    post_money_valuation: float
    shares_outstanding_before: int
    new_shares_issued: int
    price_per_share: float
    liquidation_preference: float | None
    participation_cap: float | None
    anti_dilution_type: str | None
    cap_table: list[CapTableEntry]
    waterfall: list[WaterfallScenario]
    dilution_impact: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompareRequest(BaseModel):
    scenario_ids: list[uuid.UUID]

    @field_validator("scenario_ids")
    @classmethod
    def validate_count(cls, v: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(v) < 2 or len(v) > 5:
            raise ValueError("Must compare 2-5 scenarios")
        return v


class CompareResponse(BaseModel):
    scenarios: list[dict[str, Any]]  # list of key metrics per scenario
    dimensions: list[str]
