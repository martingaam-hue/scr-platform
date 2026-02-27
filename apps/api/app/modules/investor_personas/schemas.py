"""Investor Persona schemas."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class PersonaCreate(BaseModel):
    persona_name: str
    strategy_type: str = "moderate"  # conservative, moderate, aggressive, impact_first
    target_irr_min: float | None = None
    target_irr_max: float | None = None
    target_moic_min: float | None = None
    preferred_asset_types: list[str] | None = None
    preferred_geographies: list[str] | None = None
    preferred_stages: list[str] | None = None
    ticket_size_min: float | None = None
    ticket_size_max: float | None = None
    esg_requirements: dict[str, Any] | None = None
    risk_tolerance: dict[str, Any] | None = None
    co_investment_preference: bool = False
    fund_structure_preference: dict[str, Any] | None = None


class PersonaGenerateRequest(BaseModel):
    description: str  # natural language description


class PersonaResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    persona_name: str
    is_active: bool
    strategy_type: str
    target_irr_min: float | None
    target_irr_max: float | None
    target_moic_min: float | None
    preferred_asset_types: list[str] | None
    preferred_geographies: list[str] | None
    preferred_stages: list[str] | None
    ticket_size_min: float | None
    ticket_size_max: float | None
    esg_requirements: dict[str, Any] | None
    risk_tolerance: dict[str, Any] | None
    co_investment_preference: bool
    fund_structure_preference: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PersonaMatchResponse(BaseModel):
    project_id: uuid.UUID
    project_name: str
    project_type: str
    geography_country: str
    stage: str
    investment_required: str
    alignment_score: int
    alignment_reasons: list[str]
