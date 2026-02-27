"""Tax Credit Orchestrator schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, field_validator


# ── Inventory ─────────────────────────────────────────────────────────────────


class TaxCreditResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    org_id: uuid.UUID
    credit_type: str
    estimated_value: str  # Decimal as string
    claimed_value: str | None
    currency: str
    qualification: str  # TaxCreditQualification value
    qualification_details: dict[str, Any] | None
    effective_date: date | None
    expiry_date: date | None
    project_name: str | None = None
    created_at: datetime
    updated_at: datetime


class TaxCreditInventoryResponse(BaseModel):
    portfolio_id: uuid.UUID
    total_estimated: float
    total_claimed: float
    credits_by_type: dict[str, float]   # credit_type → total estimated
    credits: list[TaxCreditResponse]
    currency: str


# ── Identification ────────────────────────────────────────────────────────────


class IdentifiedCredit(BaseModel):
    credit_type: str                    # e.g. "ITC", "PTC", "45L"
    program_name: str                   # e.g. "Investment Tax Credit (IRA §48)"
    estimated_value: float
    qualification: Literal["qualified", "potential"]
    criteria_met: list[str]
    criteria_missing: list[str]
    notes: str
    expiry_year: int | None = None


class IdentificationResponse(BaseModel):
    project_id: uuid.UUID
    project_name: str
    identified: list[IdentifiedCredit]
    total_estimated_value: float
    currency: str


# ── Optimization ──────────────────────────────────────────────────────────────


class OptimizationRequest(BaseModel):
    portfolio_id: uuid.UUID


class OptimizationAction(BaseModel):
    credit_id: uuid.UUID
    project_name: str
    credit_type: str
    estimated_value: float
    action: Literal["claim", "transfer"]
    timing: str         # "immediate" | "upon_completion" | "pending_qualification"
    reason: str


class OptimizationResult(BaseModel):
    total_value: float
    claim_value: float
    transfer_value: float
    actions: list[OptimizationAction]
    summary: str
    currency: str


# ── Transfer Documentation ────────────────────────────────────────────────────


class TransferDocRequest(BaseModel):
    credit_id: uuid.UUID
    transferee_name: str
    transferee_ein: str | None = None
    transfer_price: float | None = None


class TransferDocResponse(BaseModel):
    report_id: uuid.UUID
    status: str
    message: str


# ── Summary ───────────────────────────────────────────────────────────────────


class TaxCreditSummaryResponse(BaseModel):
    entity_id: uuid.UUID
    entity_type: str    # "project" | "portfolio"
    total_estimated: float
    total_claimed: float
    total_transferred: float
    by_qualification: dict[str, float]  # qualification → total
    by_credit_type: dict[str, float]    # credit_type → total
    credits: list[TaxCreditResponse]
    currency: str
