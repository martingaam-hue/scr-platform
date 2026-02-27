"""Impact measurement schemas: SDG mapping, KPIs, carbon credits, additionality."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.models.enums import CarbonVerificationStatus


# ── SDG ──────────────────────────────────────────────────────────────────────

SDG_METADATA = {
    1:  {"label": "No Poverty",               "color": "#e5243b"},
    2:  {"label": "Zero Hunger",              "color": "#dda63a"},
    3:  {"label": "Good Health",              "color": "#4c9f38"},
    4:  {"label": "Quality Education",        "color": "#c5192d"},
    5:  {"label": "Gender Equality",          "color": "#ff3a21"},
    6:  {"label": "Clean Water",              "color": "#26bde2"},
    7:  {"label": "Affordable Energy",        "color": "#fcc30b"},
    8:  {"label": "Decent Work",              "color": "#a21942"},
    9:  {"label": "Industry & Innovation",    "color": "#fd6925"},
    10: {"label": "Reduced Inequalities",     "color": "#dd1367"},
    11: {"label": "Sustainable Cities",       "color": "#fd9d24"},
    12: {"label": "Responsible Consumption",  "color": "#bf8b2e"},
    13: {"label": "Climate Action",           "color": "#3f7e44"},
    14: {"label": "Life Below Water",         "color": "#0a97d9"},
    15: {"label": "Life on Land",             "color": "#56c02b"},
    16: {"label": "Peace & Justice",          "color": "#00689d"},
    17: {"label": "Partnerships",             "color": "#19486a"},
}


class SDGGoal(BaseModel):
    number: int
    label: str
    color: str
    contribution_level: str  # primary | secondary | co-benefit
    description: str = ""


class SDGMappingRequest(BaseModel):
    goals: list[dict]  # [{number, contribution_level, description}]

    @field_validator("goals")
    @classmethod
    def validate_goals(cls, v: list[dict]) -> list[dict]:
        for g in v:
            n = g.get("number")
            if not isinstance(n, int) or n < 1 or n > 17:
                raise ValueError(f"SDG number must be 1–17, got {n}")
            if g.get("contribution_level") not in ("primary", "secondary", "co-benefit"):
                raise ValueError("contribution_level must be primary | secondary | co-benefit")
        return v


class SDGSummary(BaseModel):
    project_id: uuid.UUID
    project_name: str
    goals: list[SDGGoal]


# ── Impact KPIs ───────────────────────────────────────────────────────────────


class ImpactKPI(BaseModel):
    key: str
    label: str
    value: float | None
    unit: str
    category: str  # energy | environment | social | economic


class ImpactKPIUpdateRequest(BaseModel):
    kpis: dict[str, float | None]  # key → value (None to clear)


class ProjectImpactResponse(BaseModel):
    project_id: uuid.UUID
    project_name: str
    project_type: str
    geography_country: str
    kpis: list[ImpactKPI]
    sdg_goals: list[SDGGoal]
    additionality_score: int
    additionality_breakdown: dict


# ── Portfolio impact ──────────────────────────────────────────────────────────


class PortfolioImpactResponse(BaseModel):
    total_projects: int
    total_capacity_mw: float
    total_co2_reduction_tco2e: float
    total_jobs_created: int
    total_households_served: int
    total_carbon_credit_tons: float
    sdg_coverage: list[int]          # SDG numbers covered across portfolio
    projects: list[ProjectImpactResponse]


# ── Carbon credits ────────────────────────────────────────────────────────────


class CarbonCreditResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    org_id: uuid.UUID
    registry: str
    methodology: str
    vintage_year: int
    quantity_tons: str
    price_per_ton: str | None
    currency: str
    serial_number: str | None
    verification_status: CarbonVerificationStatus
    verification_body: str | None
    issuance_date: date | None
    retirement_date: date | None
    created_at: datetime


class CarbonCreditListResponse(BaseModel):
    items: list[CarbonCreditResponse]
    total: int
    total_estimated: float
    total_verified: float
    total_issued: float
    total_retired: float


class CarbonCreditCreateRequest(BaseModel):
    project_id: uuid.UUID
    registry: str
    methodology: str
    vintage_year: int
    quantity_tons: Decimal
    price_per_ton: Decimal | None = None
    currency: str = "USD"
    serial_number: str | None = None
    verification_status: CarbonVerificationStatus = CarbonVerificationStatus.ESTIMATED
    verification_body: str | None = None
    issuance_date: date | None = None
    retirement_date: date | None = None


class CarbonCreditUpdateRequest(BaseModel):
    registry: str | None = None
    methodology: str | None = None
    vintage_year: int | None = None
    quantity_tons: Decimal | None = None
    price_per_ton: Decimal | None = None
    verification_status: CarbonVerificationStatus | None = None
    verification_body: str | None = None
    issuance_date: date | None = None
    retirement_date: date | None = None


# ── Additionality ─────────────────────────────────────────────────────────────


class AdditionalityResponse(BaseModel):
    project_id: uuid.UUID
    score: int           # 0–100
    rating: str          # high | medium | low
    breakdown: dict      # criterion → {score, max, rationale}
    recommendations: list[str]
