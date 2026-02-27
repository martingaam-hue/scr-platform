"""Investor Persona service."""
import json
import uuid
from decimal import Decimal
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.advisory import InvestorPersona
from app.models.projects import Project, SignalScore
from app.modules.investor_personas.schemas import PersonaCreate, PersonaMatchResponse

logger = structlog.get_logger()


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_or_raise(
    db: AsyncSession,
    persona_id: uuid.UUID,
    org_id: uuid.UUID,
) -> InvestorPersona:
    stmt = select(InvestorPersona).where(
        InvestorPersona.id == persona_id,
        InvestorPersona.org_id == org_id,
    )
    result = await db.execute(stmt)
    persona = result.scalar_one_or_none()
    if not persona:
        raise LookupError(f"Investor persona {persona_id} not found for org {org_id}")
    return persona


def _list_from_jsonb(value: Any) -> list[str] | None:
    """Convert JSONB field (dict or list) to list[str] for response."""
    if value is None:
        return None
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, dict):
        return list(value.keys())
    return None


def _list_to_jsonb(values: list[str] | None) -> dict[str, bool] | None:
    """Convert list[str] to JSONB dict for storage."""
    if values is None:
        return None
    return {v: True for v in values}


async def _get_latest_signal_score(
    db: AsyncSession, project_id: uuid.UUID
) -> SignalScore | None:
    stmt = (
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ── Alignment scoring (deterministic) ────────────────────────────────────────


def _calc_persona_alignment(
    project: Project,
    persona: InvestorPersona,
    signal_score: SignalScore | None,
) -> tuple[int, list[str]]:
    """
    Score project alignment against investor persona (0-100).
    - Sector/asset type match: 30 pts
    - Geography match: 20 pts
    - Stage match: 20 pts
    - Ticket size in range: 20 pts
    - Signal score >= 60: 10 pts
    """
    score = 0
    reasons: list[str] = []

    # Asset type / sector match: 30 pts
    preferred_assets = _list_from_jsonb(persona.preferred_asset_types) or []
    if project.project_type.value in preferred_assets:
        score += 30
        reasons.append(f"Asset type match: {project.project_type.value}")

    # Geography match: 20 pts
    preferred_geos = _list_from_jsonb(persona.preferred_geographies) or []
    if project.geography_country in preferred_geos:
        score += 20
        reasons.append(f"Geography match: {project.geography_country}")

    # Stage match: 20 pts
    preferred_stages = _list_from_jsonb(persona.preferred_stages) or []
    if project.stage.value in preferred_stages:
        score += 20
        reasons.append(f"Stage match: {project.stage.value}")

    # Ticket size in range: 20 pts
    investment = project.total_investment_required
    t_min = persona.ticket_size_min
    t_max = persona.ticket_size_max
    if t_min is not None and t_max is not None:
        if t_min <= investment <= t_max:
            score += 20
            reasons.append("Investment size within ticket range")
    elif t_min is not None:
        if investment >= t_min:
            score += 20
            reasons.append("Investment size above minimum ticket")

    # Signal score >= 60: 10 pts
    if signal_score and signal_score.overall_score >= 60:
        score += 10
        reasons.append(f"Signal score {signal_score.overall_score}/100")

    return score, reasons


# ── Service functions ─────────────────────────────────────────────────────────


async def create_persona(
    db: AsyncSession,
    org_id: uuid.UUID,
    body: PersonaCreate,
) -> InvestorPersona:
    """Create a new investor persona."""
    from app.models.enums import InvestorPersonaStrategy

    try:
        strategy = InvestorPersonaStrategy(body.strategy_type.lower())
    except ValueError:
        strategy = InvestorPersonaStrategy.MODERATE

    persona = InvestorPersona(
        org_id=org_id,
        persona_name=body.persona_name,
        is_active=True,
        strategy_type=strategy,
        target_irr_min=Decimal(str(body.target_irr_min)) if body.target_irr_min is not None else None,
        target_irr_max=Decimal(str(body.target_irr_max)) if body.target_irr_max is not None else None,
        target_moic_min=Decimal(str(body.target_moic_min)) if body.target_moic_min is not None else None,
        preferred_asset_types=_list_to_jsonb(body.preferred_asset_types),
        preferred_geographies=_list_to_jsonb(body.preferred_geographies),
        preferred_stages=_list_to_jsonb(body.preferred_stages),
        ticket_size_min=Decimal(str(body.ticket_size_min)) if body.ticket_size_min is not None else None,
        ticket_size_max=Decimal(str(body.ticket_size_max)) if body.ticket_size_max is not None else None,
        esg_requirements=body.esg_requirements,
        risk_tolerance=body.risk_tolerance,
        co_investment_preference=body.co_investment_preference,
        fund_structure_preference=body.fund_structure_preference,
    )
    db.add(persona)
    await db.flush()
    await db.refresh(persona)
    return persona


async def generate_persona(
    db: AsyncSession,
    org_id: uuid.UUID,
    description: str,
) -> InvestorPersona:
    """
    Generate an investor persona from a natural language description via AI Gateway.
    Parse JSON from response. If AI fails, create a stub persona from the description.
    """
    from app.models.enums import InvestorPersonaStrategy

    prompt = (
        f'Extract investment persona from this description: "{description}"\n\n'
        "Respond ONLY with valid JSON:\n"
        '{"persona_name": "...", "strategy_type": "moderate|conservative|aggressive|impact_first", '
        '"target_irr_min": null, "target_irr_max": null, "target_moic_min": null, '
        '"preferred_asset_types": [...], "preferred_geographies": [...], "preferred_stages": [...], '
        '"ticket_size_min": null, "ticket_size_max": null, '
        '"esg_requirements": {"min_esg_score": null}, "risk_tolerance": {"level": "medium"}}'
    )

    extracted: dict[str, Any] = {}
    try:
        resp = httpx.post(
            f"{settings.AI_GATEWAY_URL}/v1/completions",
            json={
                "prompt": prompt,
                "task_type": "analysis",
                "max_tokens": 1000,
                "temperature": 0.7,
            },
            headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content", "")

        # Strip markdown code fences if present
        if "```" in content:
            lines = content.split("\n")
            json_lines = [
                ln for ln in lines if not ln.strip().startswith("```")
            ]
            content = "\n".join(json_lines)

        extracted = json.loads(content.strip())
        logger.info("persona_generated_from_ai", org_id=str(org_id))
    except Exception as exc:
        logger.warning("persona_ai_generation_failed", error=str(exc), org_id=str(org_id))
        # Fallback: create a stub persona using description as name
        extracted = {
            "persona_name": description[:200] if len(description) > 200 else description,
            "strategy_type": "moderate",
        }

    # Build persona_name: prefer AI output, fallback to description excerpt
    persona_name = extracted.get("persona_name") or description[:200]

    try:
        strategy = InvestorPersonaStrategy(
            (extracted.get("strategy_type") or "moderate").lower()
        )
    except ValueError:
        strategy = InvestorPersonaStrategy.MODERATE

    def _safe_decimal(val: Any) -> Decimal | None:
        if val is None:
            return None
        try:
            return Decimal(str(val))
        except Exception:
            return None

    def _safe_list_to_jsonb(val: Any) -> dict[str, bool] | None:
        if val is None:
            return None
        if isinstance(val, list):
            return {str(v): True for v in val if v}
        return None

    persona = InvestorPersona(
        org_id=org_id,
        persona_name=persona_name,
        is_active=True,
        strategy_type=strategy,
        target_irr_min=_safe_decimal(extracted.get("target_irr_min")),
        target_irr_max=_safe_decimal(extracted.get("target_irr_max")),
        target_moic_min=_safe_decimal(extracted.get("target_moic_min")),
        preferred_asset_types=_safe_list_to_jsonb(extracted.get("preferred_asset_types")),
        preferred_geographies=_safe_list_to_jsonb(extracted.get("preferred_geographies")),
        preferred_stages=_safe_list_to_jsonb(extracted.get("preferred_stages")),
        ticket_size_min=_safe_decimal(extracted.get("ticket_size_min")),
        ticket_size_max=_safe_decimal(extracted.get("ticket_size_max")),
        esg_requirements=extracted.get("esg_requirements"),
        risk_tolerance=extracted.get("risk_tolerance"),
        co_investment_preference=bool(extracted.get("co_investment_preference", False)),
        fund_structure_preference=extracted.get("fund_structure_preference"),
    )
    db.add(persona)
    await db.flush()
    await db.refresh(persona)
    return persona


async def list_personas(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[InvestorPersona]:
    """Return all active personas for org."""
    stmt = (
        select(InvestorPersona)
        .where(
            InvestorPersona.org_id == org_id,
            InvestorPersona.is_active.is_(True),
        )
        .order_by(InvestorPersona.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_persona(
    db: AsyncSession,
    persona_id: uuid.UUID,
    org_id: uuid.UUID,
) -> InvestorPersona:
    """Get single persona by id scoped to org."""
    return await _get_or_raise(db, persona_id, org_id)


async def update_persona(
    db: AsyncSession,
    persona_id: uuid.UUID,
    org_id: uuid.UUID,
    updates: dict[str, Any],
) -> InvestorPersona:
    """Apply partial updates to an investor persona."""
    from app.models.enums import InvestorPersonaStrategy

    persona = await _get_or_raise(db, persona_id, org_id)

    if "persona_name" in updates and updates["persona_name"] is not None:
        persona.persona_name = updates["persona_name"]

    if "strategy_type" in updates and updates["strategy_type"] is not None:
        try:
            persona.strategy_type = InvestorPersonaStrategy(updates["strategy_type"].lower())
        except ValueError:
            pass

    if "target_irr_min" in updates:
        val = updates["target_irr_min"]
        persona.target_irr_min = Decimal(str(val)) if val is not None else None

    if "target_irr_max" in updates:
        val = updates["target_irr_max"]
        persona.target_irr_max = Decimal(str(val)) if val is not None else None

    if "target_moic_min" in updates:
        val = updates["target_moic_min"]
        persona.target_moic_min = Decimal(str(val)) if val is not None else None

    if "preferred_asset_types" in updates:
        persona.preferred_asset_types = _list_to_jsonb(updates["preferred_asset_types"])

    if "preferred_geographies" in updates:
        persona.preferred_geographies = _list_to_jsonb(updates["preferred_geographies"])

    if "preferred_stages" in updates:
        persona.preferred_stages = _list_to_jsonb(updates["preferred_stages"])

    if "ticket_size_min" in updates:
        val = updates["ticket_size_min"]
        persona.ticket_size_min = Decimal(str(val)) if val is not None else None

    if "ticket_size_max" in updates:
        val = updates["ticket_size_max"]
        persona.ticket_size_max = Decimal(str(val)) if val is not None else None

    if "esg_requirements" in updates:
        persona.esg_requirements = updates["esg_requirements"]

    if "risk_tolerance" in updates:
        persona.risk_tolerance = updates["risk_tolerance"]

    if "co_investment_preference" in updates and updates["co_investment_preference"] is not None:
        persona.co_investment_preference = bool(updates["co_investment_preference"])

    if "fund_structure_preference" in updates:
        persona.fund_structure_preference = updates["fund_structure_preference"]

    if "is_active" in updates and updates["is_active"] is not None:
        persona.is_active = bool(updates["is_active"])

    await db.flush()
    await db.refresh(persona)
    return persona


async def get_persona_matches(
    db: AsyncSession,
    persona_id: uuid.UUID,
    org_id: uuid.UUID,
) -> list[PersonaMatchResponse]:
    """
    Load persona, load published projects, score each against persona,
    return top 20 sorted by alignment_score desc.
    """
    persona = await _get_or_raise(db, persona_id, org_id)

    stmt = select(Project).where(
        Project.is_published.is_(True),
        Project.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    projects = result.scalars().all()

    matches: list[PersonaMatchResponse] = []
    for project in projects:
        signal_score = await _get_latest_signal_score(db, project.id)
        alignment_score, alignment_reasons = _calc_persona_alignment(
            project, persona, signal_score
        )

        matches.append(
            PersonaMatchResponse(
                project_id=project.id,
                project_name=project.name,
                project_type=project.project_type.value,
                geography_country=project.geography_country,
                stage=project.stage.value,
                investment_required=str(project.total_investment_required),
                alignment_score=alignment_score,
                alignment_reasons=alignment_reasons,
            )
        )

    # Sort by alignment_score descending, return top 20
    matches.sort(key=lambda x: x.alignment_score, reverse=True)
    return matches[:20]
