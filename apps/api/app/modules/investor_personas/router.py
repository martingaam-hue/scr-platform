"""Investor Personas API router."""

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.investor_personas import service
from app.modules.investor_personas.schemas import (
    PersonaCreate,
    PersonaGenerateRequest,
    PersonaMatchResponse,
    PersonaResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/investor-personas", tags=["investor-personas"])


# ── Fixed paths (MUST come before /{persona_id}) ─────────────────────────────


@router.get("", response_model=list[PersonaResponse])
async def list_personas(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active investor personas for the current org."""
    personas = await service.list_personas(db, current_user.org_id)
    return [_serialize_persona(p) for p in personas]


@router.post(
    "",
    response_model=PersonaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_persona(
    body: PersonaCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new investor persona manually."""
    persona = await service.create_persona(db, current_user.org_id, body)
    await db.commit()
    await db.refresh(persona)
    return _serialize_persona(persona)


@router.post(
    "/generate",
    response_model=PersonaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_persona(
    body: PersonaGenerateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an investor persona from a natural language description using AI."""
    persona = await service.generate_persona(db, current_user.org_id, body.description)
    await db.commit()
    await db.refresh(persona)
    return _serialize_persona(persona)


# ── Parameterised endpoints ───────────────────────────────────────────────────


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single investor persona by ID."""
    try:
        persona = await service.get_persona(db, persona_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_persona(persona)


@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: uuid.UUID,
    body: dict[str, Any],
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Partially update an investor persona."""
    try:
        persona = await service.update_persona(
            db, persona_id, current_user.org_id, body
        )
        await db.commit()
        await db.refresh(persona)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_persona(persona)


@router.get("/{persona_id}/matches", response_model=list[PersonaMatchResponse])
async def get_persona_matches(
    persona_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get matching published projects for a given investor persona."""
    try:
        matches = await service.get_persona_matches(db, persona_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return matches


# ── Serialization helper ──────────────────────────────────────────────────────


def _serialize_persona(persona: Any) -> PersonaResponse:
    """Convert InvestorPersona ORM to PersonaResponse, handling JSONB list fields."""
    from app.modules.investor_personas.service import _list_from_jsonb

    return PersonaResponse(
        id=persona.id,
        org_id=persona.org_id,
        persona_name=persona.persona_name,
        is_active=persona.is_active,
        strategy_type=persona.strategy_type.value
        if hasattr(persona.strategy_type, "value")
        else str(persona.strategy_type),
        target_irr_min=float(persona.target_irr_min) if persona.target_irr_min is not None else None,
        target_irr_max=float(persona.target_irr_max) if persona.target_irr_max is not None else None,
        target_moic_min=float(persona.target_moic_min) if persona.target_moic_min is not None else None,
        preferred_asset_types=_list_from_jsonb(persona.preferred_asset_types),
        preferred_geographies=_list_from_jsonb(persona.preferred_geographies),
        preferred_stages=_list_from_jsonb(persona.preferred_stages),
        ticket_size_min=float(persona.ticket_size_min) if persona.ticket_size_min is not None else None,
        ticket_size_max=float(persona.ticket_size_max) if persona.ticket_size_max is not None else None,
        esg_requirements=persona.esg_requirements,
        risk_tolerance=persona.risk_tolerance,
        co_investment_preference=persona.co_investment_preference,
        fund_structure_preference=persona.fund_structure_preference,
        created_at=persona.created_at,
        updated_at=persona.updated_at,
    )
