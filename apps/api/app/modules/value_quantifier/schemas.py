"""Value Quantifier schemas — deterministic financial KPIs."""

import uuid
from pydantic import BaseModel


class ValueQuantifierRequest(BaseModel):
    project_id: uuid.UUID
    # Overrides (if not provided, use project data)
    capex_usd: float | None = None            # Total capital expenditure
    opex_annual_usd: float | None = None      # Annual operating cost
    revenue_annual_usd: float | None = None   # Annual revenue
    project_lifetime_years: int = 25          # Default 25 years
    discount_rate: float = 0.10               # WACC / hurdle rate (10% default)
    debt_ratio: float = 0.70                  # 70% debt default
    interest_rate: float = 0.05              # 5% loan interest
    loan_term_years: int = 20                # Loan term
    capacity_factor: float | None = None     # Override capacity factor
    electricity_price_kwh: float = 0.08      # $/kWh
    jobs_created: int | None = None          # If provided, use directly


class ValueKPI(BaseModel):
    label: str
    value: str       # formatted string
    raw_value: float | None
    unit: str
    description: str
    quality: str     # "good", "warning", "bad", "neutral"


class ValueQuantifierResponse(BaseModel):
    project_id: uuid.UUID
    project_name: str
    irr: float | None          # Internal rate of return %
    npv: float | None          # Net present value USD
    payback_years: float | None
    dscr: float | None         # Debt service coverage ratio
    lcoe: float | None         # Levelized cost of energy $/MWh
    carbon_savings_tons: float | None  # Annual CO2e tons avoided
    jobs_created: int | None
    total_investment: float | None
    kpis: list[ValueKPI]
    assumptions: dict[str, float | int | str]
