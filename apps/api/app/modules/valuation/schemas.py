"""Valuation module schemas — DCF, Comparables, Replacement Cost, Blended, Sensitivity."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, field_validator, model_validator


# ── DCF ──────────────────────────────────────────────────────────────────────


class DCFParams(BaseModel):
    cash_flows: list[float]           # yearly amounts in valuation currency
    discount_rate: float              # 0.0–1.0  (e.g. 0.10 = 10 %)
    terminal_growth_rate: float = 0.02
    terminal_method: Literal["gordon", "exit_multiple"] = "gordon"
    exit_multiple: float | None = None
    net_debt: float = 0.0             # subtracted from EV to get equity value

    @field_validator("discount_rate")
    @classmethod
    def dr_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("discount_rate must be positive")
        return v

    @field_validator("cash_flows")
    @classmethod
    def cf_not_empty(cls, v: list[float]) -> list[float]:
        if not v:
            raise ValueError("At least one cash flow is required")
        return v

    @model_validator(mode="after")
    def exit_multiple_required(self) -> DCFParams:
        if self.terminal_method == "exit_multiple" and self.exit_multiple is None:
            raise ValueError("exit_multiple is required when terminal_method='exit_multiple'")
        return self


class YearlyPV(BaseModel):
    year: int
    cash_flow: float
    pv: float


class DCFResult(BaseModel):
    enterprise_value: float
    equity_value: float
    npv: float
    terminal_value: float
    terminal_pv: float
    tv_as_pct_of_ev: float
    year_by_year_pv: list[YearlyPV]
    discount_rate: float
    terminal_growth_rate: float


# ── Comparables ───────────────────────────────────────────────────────────────


class ComparableCompany(BaseModel):
    name: str
    ev_ebitda: float | None = None    # EV / EBITDA multiple
    ev_mw: float | None = None        # EV / MW for power assets (USD per MW)
    ev_revenue: float | None = None   # EV / Revenue multiple
    transaction_date: str | None = None
    geography: str | None = None
    notes: str | None = None


class ComparableParams(BaseModel):
    comparables: list[ComparableCompany]
    subject_ebitda: float | None = None
    subject_capacity_mw: float | None = None
    subject_revenue: float | None = None
    net_debt: float = 0.0
    multiple_types: list[Literal["ev_ebitda", "ev_mw", "ev_revenue"]] = [
        "ev_ebitda", "ev_mw", "ev_revenue"
    ]

    @field_validator("comparables")
    @classmethod
    def comps_not_empty(cls, v: list[ComparableCompany]) -> list[ComparableCompany]:
        if not v:
            raise ValueError("At least one comparable is required")
        return v


class MultipleResult(BaseModel):
    implied_values: list[float]
    mean: float
    median: float
    min_val: float
    max_val: float


class ComparableResult(BaseModel):
    enterprise_value: float    # = weighted_average_value
    equity_value: float
    by_multiple: dict[str, MultipleResult]
    weighted_average_value: float
    range_min: float
    range_max: float


# ── Replacement Cost ──────────────────────────────────────────────────────────


class ReplacementCostParams(BaseModel):
    component_costs: dict[str, float]  # label → amount in valuation currency
    land_value: float = 0.0
    development_costs: float = 0.0
    depreciation_pct: float = 0.0      # 0–100 %
    net_debt: float = 0.0

    @field_validator("depreciation_pct")
    @classmethod
    def dep_valid(cls, v: float) -> float:
        if not 0 <= v <= 100:
            raise ValueError("depreciation_pct must be between 0 and 100")
        return v

    @field_validator("component_costs")
    @classmethod
    def costs_not_empty(cls, v: dict[str, float]) -> dict[str, float]:
        if not v:
            raise ValueError("At least one component cost is required")
        return v


class ReplacementResult(BaseModel):
    enterprise_value: float
    equity_value: float
    gross_replacement_cost: float
    depreciated_value: float
    component_breakdown: dict[str, float]


# ── Blended ───────────────────────────────────────────────────────────────────


class BlendedComponent(BaseModel):
    method: str           # "dcf" | "comparables" | "replacement_cost" | custom label
    enterprise_value: float
    weight: float         # will be normalised to sum to 1


class BlendedParams(BaseModel):
    components: list[BlendedComponent]
    net_debt: float = 0.0

    @field_validator("components")
    @classmethod
    def at_least_two(cls, v: list[BlendedComponent]) -> list[BlendedComponent]:
        if len(v) < 2:
            raise ValueError("Blended valuation requires at least 2 components")
        return v


class BlendedBreakdownItem(BaseModel):
    method: str
    enterprise_value: float
    weight: float           # normalised
    weighted_value: float


class BlendedResult(BaseModel):
    enterprise_value: float
    equity_value: float
    blended_value: float
    range_min: float
    range_max: float
    breakdown: list[BlendedBreakdownItem]


# ── Sensitivity ───────────────────────────────────────────────────────────────


class SensitivityRequest(BaseModel):
    base_params: DCFParams
    row_variable: Literal["discount_rate", "terminal_growth_rate"]
    row_values: list[float]   # 3–7 values
    col_variable: Literal["discount_rate", "terminal_growth_rate"]
    col_values: list[float]   # 3–7 values

    @model_validator(mode="after")
    def vars_differ(self) -> SensitivityRequest:
        if self.row_variable == self.col_variable:
            raise ValueError("row_variable and col_variable must be different")
        return self

    @field_validator("row_values", "col_values")
    @classmethod
    def values_not_empty(cls, v: list[float]) -> list[float]:
        if not v:
            raise ValueError("Must provide at least one value")
        return v


class SensitivityMatrix(BaseModel):
    row_variable: str
    col_variable: str
    row_values: list[float]
    col_values: list[float]
    matrix: list[list[float | None]]
    base_value: float
    min_value: float
    max_value: float


# ── AI suggestions ────────────────────────────────────────────────────────────


class SuggestAssumptionsRequest(BaseModel):
    project_type: str
    geography: str
    stage: str


class AssumptionSuggestion(BaseModel):
    discount_rate: float
    terminal_growth_rate: float
    terminal_method: str
    projection_years: int
    comparable_multiples: dict[str, float]
    reasoning: dict[str, str]


# ── Valuation CRUD ────────────────────────────────────────────────────────────


ValuationMethod = Literal["dcf", "comparables", "replacement_cost", "blended"]


class ValuationCreateRequest(BaseModel):
    project_id: uuid.UUID
    method: ValuationMethod
    currency: str = "USD"
    dcf_params: DCFParams | None = None
    comparable_params: ComparableParams | None = None
    replacement_params: ReplacementCostParams | None = None
    blended_params: BlendedParams | None = None

    @model_validator(mode="after")
    def params_required(self) -> ValuationCreateRequest:
        required = {
            "dcf": self.dcf_params,
            "comparables": self.comparable_params,
            "replacement_cost": self.replacement_params,
            "blended": self.blended_params,
        }
        if required[self.method] is None:
            raise ValueError(f"{self.method}_params is required for method '{self.method}'")
        return self


class ValuationUpdateRequest(BaseModel):
    dcf_params: DCFParams | None = None
    comparable_params: ComparableParams | None = None
    replacement_params: ReplacementCostParams | None = None
    blended_params: BlendedParams | None = None


class ValuationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    org_id: uuid.UUID
    method: str
    enterprise_value: str   # Decimal as string
    equity_value: str
    currency: str
    status: str
    version: int
    valued_at: date
    prepared_by: uuid.UUID
    approved_by: uuid.UUID | None
    assumptions: dict[str, Any]
    model_inputs: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ValuationListResponse(BaseModel):
    items: list[ValuationResponse]
    total: int


class ValuationReportResponse(BaseModel):
    report_id: uuid.UUID
    status: str
    message: str


# ── Batch Valuations ──────────────────────────────────────────────────────────


class BatchValuationRequest(BaseModel):
    project_ids: list[uuid.UUID]
    method: ValuationMethod = "dcf"
    currency: str = "USD"
    dcf_params: DCFParams | None = None
    comparable_params: ComparableParams | None = None
    replacement_params: ReplacementCostParams | None = None
    blended_params: BlendedParams | None = None


class BatchValuationItem(BaseModel):
    project_id: uuid.UUID
    valuation_id: uuid.UUID | None
    status: str


class BatchValuationResponse(BaseModel):
    queued: int
    failed: int
    items: list[BatchValuationItem]
    errors: list[dict]
