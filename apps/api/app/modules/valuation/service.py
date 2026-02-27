"""Valuation service — orchestrates engine, AI assistant, and DB persistence."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ValuationMethod, ValuationStatus
from app.models.financial import Valuation
from app.models.projects import Project
from app.models.reporting import GeneratedReport
from app.models.enums import ReportStatus
from app.modules.valuation.ai_assistant import ValuationAIAssistant
from app.modules.valuation.engine import ValuationEngine
from app.modules.valuation.schemas import (
    BlendedParams,
    ComparableParams,
    DCFParams,
    ReplacementCostParams,
    SensitivityMatrix,
    SensitivityRequest,
    ValuationCreateRequest,
    ValuationResponse,
    ValuationUpdateRequest,
)

logger = structlog.get_logger()

_engine = ValuationEngine()
_ai = ValuationAIAssistant()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_response(v: Valuation) -> ValuationResponse:
    return ValuationResponse(
        id=v.id,
        project_id=v.project_id,
        org_id=v.org_id,
        method=v.method.value,
        enterprise_value=str(v.enterprise_value),
        equity_value=str(v.equity_value),
        currency=v.currency,
        status=v.status.value,
        version=v.version,
        valued_at=v.valued_at,
        prepared_by=v.prepared_by,
        approved_by=v.approved_by,
        assumptions=v.assumptions or {},
        model_inputs=v.model_inputs or {},
        created_at=v.created_at,
        updated_at=v.updated_at,
    )


def _run_engine(
    method: str,
    dcf_params: DCFParams | None,
    comparable_params: ComparableParams | None,
    replacement_params: ReplacementCostParams | None,
    blended_params: BlendedParams | None,
) -> tuple[float, float, dict[str, Any], dict[str, Any]]:
    """Returns (enterprise_value, equity_value, assumptions_dict, model_inputs_dict)."""
    if method == "dcf" and dcf_params:
        result = _engine.dcf_valuation(dcf_params)
        return (
            result.enterprise_value,
            result.equity_value,
            {
                "method": "dcf",
                "discount_rate": result.discount_rate,
                "terminal_growth_rate": result.terminal_growth_rate,
                "terminal_method": dcf_params.terminal_method,
                "tv_as_pct_of_ev": result.tv_as_pct_of_ev,
                "npv": result.npv,
                "terminal_value": result.terminal_value,
            },
            {
                "dcf_params": dcf_params.model_dump(),
                "result": result.model_dump(),
            },
        )

    if method == "comparables" and comparable_params:
        result = _engine.comparable_valuation(comparable_params)
        return (
            result.enterprise_value,
            result.equity_value,
            {
                "method": "comparables",
                "range_min": result.range_min,
                "range_max": result.range_max,
                "multiples_used": list(result.by_multiple.keys()),
            },
            {
                "comparable_params": comparable_params.model_dump(),
                "result": result.model_dump(),
            },
        )

    if method == "replacement_cost" and replacement_params:
        result = _engine.replacement_cost(replacement_params)
        return (
            result.enterprise_value,
            result.equity_value,
            {
                "method": "replacement_cost",
                "gross_replacement_cost": result.gross_replacement_cost,
                "depreciation_pct": replacement_params.depreciation_pct,
            },
            {
                "replacement_params": replacement_params.model_dump(),
                "result": result.model_dump(),
            },
        )

    if method == "blended" and blended_params:
        result = _engine.blended_valuation(blended_params)
        return (
            result.enterprise_value,
            result.equity_value,
            {
                "method": "blended",
                "range_min": result.range_min,
                "range_max": result.range_max,
                "components": [c.model_dump() for c in result.breakdown],
            },
            {
                "blended_params": blended_params.model_dump(),
                "result": result.model_dump(),
            },
        )

    raise ValueError(f"Unsupported method or missing params: {method}")


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def create_valuation(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    body: ValuationCreateRequest,
) -> Valuation:
    # Verify project belongs to org
    proj = await db.get(Project, body.project_id)
    if not proj or proj.is_deleted or proj.org_id != org_id:
        raise LookupError(f"Project {body.project_id} not found")

    ev, eq, assumptions, model_inputs = _run_engine(
        body.method,
        body.dcf_params,
        body.comparable_params,
        body.replacement_params,
        body.blended_params,
    )

    # Increment version for same project + method
    existing = await db.execute(
        select(Valuation).where(
            Valuation.project_id == body.project_id,
            Valuation.org_id == org_id,
            Valuation.method == ValuationMethod(body.method),
            Valuation.is_deleted.is_(False),
        )
    )
    version = len(list(existing.scalars().all())) + 1

    val = Valuation(
        project_id=body.project_id,
        org_id=org_id,
        method=ValuationMethod(body.method),
        enterprise_value=Decimal(str(round(ev, 4))),
        equity_value=Decimal(str(round(eq, 4))),
        currency=body.currency,
        assumptions=assumptions,
        model_inputs=model_inputs,
        status=ValuationStatus.DRAFT,
        version=version,
        valued_at=date.today(),
        prepared_by=user_id,
    )
    db.add(val)
    return val


async def get_valuation(
    db: AsyncSession, valuation_id: uuid.UUID, org_id: uuid.UUID
) -> Valuation:
    result = await db.execute(
        select(Valuation).where(
            Valuation.id == valuation_id,
            Valuation.org_id == org_id,
            Valuation.is_deleted.is_(False),
        )
    )
    val = result.scalar_one_or_none()
    if not val:
        raise LookupError(f"Valuation {valuation_id} not found")
    return val


async def list_valuations(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
) -> list[Valuation]:
    stmt = select(Valuation).where(
        Valuation.org_id == org_id,
        Valuation.is_deleted.is_(False),
    )
    if project_id:
        stmt = stmt.where(Valuation.project_id == project_id)
    stmt = stmt.order_by(Valuation.valued_at.desc(), Valuation.version.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_valuation(
    db: AsyncSession,
    valuation_id: uuid.UUID,
    org_id: uuid.UUID,
    body: ValuationUpdateRequest,
) -> Valuation:
    val = await get_valuation(db, valuation_id, org_id)
    if val.status == ValuationStatus.APPROVED:
        raise ValueError("Approved valuations cannot be updated. Create a new version.")

    # Recalculate with new params (method stays the same)
    params_map = {
        "dcf": body.dcf_params,
        "comparables": body.comparable_params,
        "replacement_cost": body.replacement_params,
        "blended": body.blended_params,
    }
    new_params = params_map.get(val.method.value)
    if new_params is None:
        raise ValueError(f"Provide updated params for method '{val.method.value}'")

    # Rebuild using stored inputs merged with new params
    ev, eq, assumptions, model_inputs = _run_engine(
        val.method.value,
        body.dcf_params,
        body.comparable_params,
        body.replacement_params,
        body.blended_params,
    )

    val.enterprise_value = Decimal(str(round(ev, 4)))
    val.equity_value = Decimal(str(round(eq, 4)))
    val.assumptions = assumptions
    val.model_inputs = model_inputs
    val.valued_at = date.today()
    return val


async def approve_valuation(
    db: AsyncSession,
    valuation_id: uuid.UUID,
    org_id: uuid.UUID,
    approver_id: uuid.UUID,
) -> Valuation:
    val = await get_valuation(db, valuation_id, org_id)
    if val.status == ValuationStatus.APPROVED:
        raise ValueError("Valuation is already approved.")
    # Supersede any previously approved valuation for same project + method
    prev = await db.execute(
        select(Valuation).where(
            Valuation.project_id == val.project_id,
            Valuation.org_id == org_id,
            Valuation.method == val.method,
            Valuation.status == ValuationStatus.APPROVED,
            Valuation.id != val.id,
            Valuation.is_deleted.is_(False),
        )
    )
    for old in prev.scalars().all():
        old.status = ValuationStatus.SUPERSEDED

    val.status = ValuationStatus.APPROVED
    val.approved_by = approver_id
    return val


# ── Sensitivity ───────────────────────────────────────────────────────────────


async def run_sensitivity(
    db: AsyncSession,
    valuation_id: uuid.UUID,
    org_id: uuid.UUID,
    req: SensitivityRequest,
) -> SensitivityMatrix:
    # Confirm valuation exists and belongs to org
    val = await get_valuation(db, valuation_id, org_id)
    if val.method != ValuationMethod.DCF:
        raise ValueError("Sensitivity analysis is only supported for DCF valuations.")
    return _engine.sensitivity_analysis(req)


# ── Report ────────────────────────────────────────────────────────────────────


async def trigger_report(
    db: AsyncSession,
    valuation_id: uuid.UUID,
    org_id: uuid.UUID,
) -> GeneratedReport:
    val = await get_valuation(db, valuation_id, org_id)
    proj = await db.get(Project, val.project_id)
    project_name = proj.name if proj else "Project"

    report = GeneratedReport(
        org_id=org_id,
        title=f"Valuation Report — {project_name} ({val.method.value.upper()}) v{val.version}",
        status=ReportStatus.QUEUED,
        parameters={
            "valuation_id": str(val.id),
            "project_id": str(val.project_id),
            "project_name": project_name,
            "project_type": proj.project_type.value if proj else "unknown",
            "geography": proj.geography_country if proj else "unknown",
        },
    )
    db.add(report)
    return report


# ── AI helpers ────────────────────────────────────────────────────────────────


async def suggest_assumptions(project_type: str, geography: str, stage: str):
    return await _ai.suggest_assumptions(project_type, geography, stage)


async def find_comparables(project_type: str, geography: str, stage: str):
    return await _ai.find_comparables(project_type, geography, stage)
