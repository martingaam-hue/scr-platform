"""Equity Calculator service."""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advisory import EquityScenario
from app.models.enums import AntiDilutionType, EquitySecurityType
from app.modules.equity_calculator import calculator
from app.modules.equity_calculator.schemas import (
    CapTableEntry,
    CompareResponse,
    EquityScenarioRequest,
    EquityScenarioResponse,
    WaterfallScenario,
)

# ── Security type mapping ─────────────────────────────────────────────────────

_SECURITY_TYPE_MAP: dict[str, EquitySecurityType] = {
    "common_equity": EquitySecurityType.COMMON_EQUITY,
    "preferred_equity": EquitySecurityType.PREFERRED_EQUITY,
    "convertible_note": EquitySecurityType.CONVERTIBLE_NOTE,
    "safe": EquitySecurityType.SAFE,
    "revenue_share": EquitySecurityType.REVENUE_SHARE,
}

_ANTI_DILUTION_MAP: dict[str, AntiDilutionType] = {
    "none": AntiDilutionType.NONE,
    "broad_based": AntiDilutionType.BROAD_BASED,
    "narrow_based": AntiDilutionType.NARROW_BASED,
    "full_ratchet": AntiDilutionType.FULL_RATCHET,
    # Legacy aliases used in prompts
    "weighted_average": AntiDilutionType.BROAD_BASED,
}

# Comparison dimensions surfaced in /compare
_COMPARE_DIMENSIONS = [
    "Pre-money Valuation",
    "Investment Amount",
    "Equity %",
    "Post-money Valuation",
    "Price per Share",
    "Investor Proceeds at 2x",
    "Investor Proceeds at 5x",
    "Dilution %",
]


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_or_raise(
    db: AsyncSession, scenario_id: uuid.UUID, org_id: uuid.UUID
) -> EquityScenario:
    result = await db.execute(
        select(EquityScenario).where(
            EquityScenario.id == scenario_id,
            EquityScenario.org_id == org_id,
        )
    )
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise LookupError("Equity scenario not found")
    return scenario


def _to_response(scenario: EquityScenario) -> EquityScenarioResponse:
    """Convert ORM model to response schema, unpacking JSONB blobs."""
    cap_table_raw: list[dict] = scenario.cap_table_snapshot or []
    waterfall_raw: list[dict] = scenario.waterfall_analysis or []
    dilution_raw: dict = scenario.dilution_impact or {}

    cap_table = [CapTableEntry(**entry) for entry in cap_table_raw]
    waterfall = [WaterfallScenario(**entry) for entry in waterfall_raw]

    security_type_str = (
        scenario.security_type.value
        if isinstance(scenario.security_type, EquitySecurityType)
        else str(scenario.security_type)
    )
    anti_dilution_str = (
        scenario.anti_dilution_type.value
        if isinstance(scenario.anti_dilution_type, AntiDilutionType)
        else (str(scenario.anti_dilution_type) if scenario.anti_dilution_type else None)
    )

    return EquityScenarioResponse(
        id=scenario.id,
        org_id=scenario.org_id,
        project_id=scenario.project_id,
        scenario_name=scenario.scenario_name,
        description=scenario.description,
        pre_money_valuation=float(scenario.pre_money_valuation),
        investment_amount=float(scenario.investment_amount),
        security_type=security_type_str,
        equity_percentage=float(scenario.equity_percentage),
        post_money_valuation=float(scenario.post_money_valuation),
        shares_outstanding_before=scenario.shares_outstanding_before,
        new_shares_issued=scenario.new_shares_issued,
        price_per_share=float(scenario.price_per_share),
        liquidation_preference=(
            float(scenario.liquidation_preference)
            if scenario.liquidation_preference is not None
            else None
        ),
        participation_cap=(
            float(scenario.participation_cap)
            if scenario.participation_cap is not None
            else None
        ),
        anti_dilution_type=anti_dilution_str,
        cap_table=cap_table,
        waterfall=waterfall,
        dilution_impact=dilution_raw,
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
    )


# ── Service functions ─────────────────────────────────────────────────────────


async def create_scenario(
    db: AsyncSession,
    org_id: uuid.UUID,
    body: EquityScenarioRequest,
) -> EquityScenarioResponse:
    """Calculate and persist a new equity scenario."""
    calc = calculator.calculate_scenario(
        pre_money_valuation=body.pre_money_valuation,
        investment_amount=body.investment_amount,
        shares_outstanding_before=body.shares_outstanding_before,
        security_type=body.security_type,
        liquidation_preference=body.liquidation_preference,
        participation_cap=body.participation_cap,
        anti_dilution_type=body.anti_dilution_type,
    )

    security_enum = _SECURITY_TYPE_MAP.get(
        body.security_type.lower(), EquitySecurityType.COMMON_EQUITY
    )
    anti_dilution_enum = _ANTI_DILUTION_MAP.get(
        body.anti_dilution_type.lower(), AntiDilutionType.NONE
    )

    # Build optional vesting schedule JSONB
    vesting_schedule: dict | None = None
    if body.vesting_cliff_months is not None or body.vesting_total_months is not None:
        vesting_schedule = {
            "cliff_months": body.vesting_cliff_months,
            "total_months": body.vesting_total_months,
        }

    scenario = EquityScenario(
        org_id=org_id,
        project_id=body.project_id,
        scenario_name=body.scenario_name,
        description=body.description,
        pre_money_valuation=Decimal(str(body.pre_money_valuation)),
        investment_amount=Decimal(str(body.investment_amount)),
        security_type=security_enum,
        equity_percentage=Decimal(str(calc["equity_percentage"])),
        post_money_valuation=Decimal(str(calc["post_money_valuation"])),
        shares_outstanding_before=body.shares_outstanding_before,
        new_shares_issued=calc["new_shares_issued"],
        price_per_share=Decimal(str(calc["price_per_share"])),
        liquidation_preference=(
            Decimal(str(body.liquidation_preference))
            if body.liquidation_preference is not None
            else None
        ),
        participation_cap=(
            Decimal(str(body.participation_cap))
            if body.participation_cap is not None
            else None
        ),
        anti_dilution_type=anti_dilution_enum,
        vesting_schedule=vesting_schedule,
        cap_table_snapshot=calc["cap_table"],
        waterfall_analysis=calc["waterfall"],
        dilution_impact=calc["dilution_impact"],
    )

    db.add(scenario)
    await db.flush()
    await db.refresh(scenario)
    return _to_response(scenario)


async def list_scenarios(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
) -> list[EquityScenarioResponse]:
    """List all equity scenarios for the org, optionally filtered by project."""
    stmt = select(EquityScenario).where(EquityScenario.org_id == org_id)
    if project_id is not None:
        stmt = stmt.where(EquityScenario.project_id == project_id)
    stmt = stmt.order_by(EquityScenario.created_at.desc())

    result = await db.execute(stmt)
    scenarios = result.scalars().all()
    return [_to_response(s) for s in scenarios]


async def get_scenario(
    db: AsyncSession,
    scenario_id: uuid.UUID,
    org_id: uuid.UUID,
) -> EquityScenarioResponse:
    """Get a single equity scenario by ID, scoped to org."""
    scenario = await _get_or_raise(db, scenario_id, org_id)
    return _to_response(scenario)


async def compare_scenarios(
    db: AsyncSession,
    scenario_ids: list[uuid.UUID],
    org_id: uuid.UUID,
) -> CompareResponse:
    """Build a side-by-side comparison table for multiple scenarios."""
    scenarios_data: list[dict] = []

    for sid in scenario_ids:
        try:
            scenario = await _get_or_raise(db, sid, org_id)
        except LookupError:
            continue

        waterfall = scenario.waterfall_analysis or []
        # Find proceeds at 2x and 5x multiples
        proceeds_2x = next(
            (w["investor_proceeds"] for w in waterfall if w.get("multiple") == 2.0), 0.0
        )
        proceeds_5x = next(
            (w["investor_proceeds"] for w in waterfall if w.get("multiple") == 5.0), 0.0
        )
        dilution = scenario.dilution_impact or {}

        anti_dilution_str = (
            scenario.anti_dilution_type.value
            if isinstance(scenario.anti_dilution_type, AntiDilutionType)
            else (str(scenario.anti_dilution_type) if scenario.anti_dilution_type else "none")
        )
        security_type_str = (
            scenario.security_type.value
            if isinstance(scenario.security_type, EquitySecurityType)
            else str(scenario.security_type)
        )

        scenarios_data.append({
            "id": str(scenario.id),
            "scenario_name": scenario.scenario_name,
            "security_type": security_type_str,
            "Pre-money Valuation": float(scenario.pre_money_valuation),
            "Investment Amount": float(scenario.investment_amount),
            "Equity %": float(scenario.equity_percentage),
            "Post-money Valuation": float(scenario.post_money_valuation),
            "Price per Share": float(scenario.price_per_share),
            "Investor Proceeds at 2x": float(proceeds_2x),
            "Investor Proceeds at 5x": float(proceeds_5x),
            "Dilution %": float(dilution.get("dilution_percentage", 0)),
            "Anti-dilution": anti_dilution_str,
        })

    return CompareResponse(scenarios=scenarios_data, dimensions=_COMPARE_DIMENSIONS)
