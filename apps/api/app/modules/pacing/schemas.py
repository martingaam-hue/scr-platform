"""Pydantic schemas for cashflow pacing endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CreateAssumptionRequest(BaseModel):
    portfolio_id: uuid.UUID
    committed_capital: Decimal
    investment_period_years: int = 5
    fund_life_years: int = 10
    optimistic_modifier: Decimal = Decimal("1.20")
    pessimistic_modifier: Decimal = Decimal("0.80")
    label: str | None = None


class UpdateActualsRequest(BaseModel):
    year: int
    actual_contributions: Decimal | None = None
    actual_distributions: Decimal | None = None
    actual_nav: Decimal | None = None


class ProjectionRow(BaseModel):
    scenario: str
    year: int
    projected_contributions: Decimal | None
    projected_distributions: Decimal | None
    projected_nav: Decimal | None
    projected_net_cashflow: Decimal | None
    actual_contributions: Decimal | None
    actual_distributions: Decimal | None
    actual_nav: Decimal | None
    actual_net_cashflow: Decimal | None

    class Config:
        from_attributes = True


class AssumptionSummary(BaseModel):
    assumption_id: str
    portfolio_id: str
    committed_capital: Decimal
    fund_life_years: int
    investment_period_years: int
    optimistic_modifier: Decimal
    pessimistic_modifier: Decimal
    label: str | None
    is_active: bool

    class Config:
        from_attributes = True


class PacingResponse(BaseModel):
    assumption_id: str
    portfolio_id: str
    committed_capital: Decimal
    fund_life_years: int
    trough_year: int | None
    trough_value: Decimal | None
    projections: list[ProjectionRow]

    class Config:
        from_attributes = True
