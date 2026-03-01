"""Carbon Credits service layer."""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CarbonVerificationStatus
from app.models.financial import CarbonCredit
from app.models.projects import Project
from app.modules.carbon_credits import estimator as est
from app.modules.carbon_credits.schemas import (
    CarbonCreditResponse,
    CarbonCreditUpdate,
    CarbonEstimateResult,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _to_response(cc: CarbonCredit, estimate_meta: dict | None = None) -> CarbonCreditResponse:
    meta = estimate_meta or {}
    return CarbonCreditResponse(
        id=cc.id,
        project_id=cc.project_id,
        registry=cc.registry,
        methodology=cc.methodology,
        vintage_year=cc.vintage_year,
        quantity_tons=float(cc.quantity_tons),
        price_per_ton=float(cc.price_per_ton) if cc.price_per_ton else None,
        currency=cc.currency,
        serial_number=cc.serial_number,
        verification_status=cc.verification_status.value,
        verification_body=cc.verification_body,
        issuance_date=cc.issuance_date,
        retirement_date=cc.retirement_date,
        estimated_annual_tons=meta.get("estimated_annual_tons"),
        suggested_methodology=meta.get("suggested_methodology"),
        revenue_projection=meta.get("revenue_projection"),
        created_at=cc.created_at,
        updated_at=cc.updated_at,
    )


async def _get_project_or_raise(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
) -> Project:
    stmt = select(Project).where(
        Project.id == project_id,
        Project.org_id == org_id,
        Project.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise LookupError(f"Project {project_id} not found")
    return project


async def _get_cc_or_raise(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
) -> CarbonCredit:
    stmt = select(CarbonCredit).where(
        CarbonCredit.project_id == project_id,
        CarbonCredit.org_id == org_id,
    )
    result = await db.execute(stmt)
    cc = result.scalar_one_or_none()
    if not cc:
        raise LookupError(f"No carbon credit record for project {project_id}")
    return cc


# ── Service functions ─────────────────────────────────────────────────────────


async def estimate_credits(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
) -> tuple[CarbonEstimateResult, CarbonCreditResponse]:
    """Deterministic carbon credit estimate for a project. Creates or updates the CC record."""
    project = await _get_project_or_raise(db, project_id, org_id)

    result = est.estimate_credits(
        project_type=project.project_type.value if project.project_type else "default",
        capacity_mw=float(project.capacity_mw) if project.capacity_mw else None,
        geography_country=project.geography_country or "default",
    )
    rev_proj = est.revenue_projection(result["annual_tons_co2e"])

    # Upsert CarbonCredit record
    stmt = select(CarbonCredit).where(
        CarbonCredit.project_id == project_id,
        CarbonCredit.org_id == org_id,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    import datetime
    if existing:
        cc = existing
        cc.registry = "Verra (estimated)"
        cc.methodology = result["methodology"]
        cc.vintage_year = datetime.date.today().year
        cc.quantity_tons = Decimal(str(result["annual_tons_co2e"]))
    else:
        cc = CarbonCredit(
            project_id=project_id,
            org_id=org_id,
            registry="Verra (estimated)",
            methodology=result["methodology"],
            vintage_year=datetime.date.today().year,
            quantity_tons=Decimal(str(result["annual_tons_co2e"])),
            currency="USD",
            verification_status=CarbonVerificationStatus.ESTIMATED,
        )
        db.add(cc)

    await db.flush()
    await db.commit()
    await db.refresh(cc)

    estimate_response = CarbonEstimateResult(
        annual_tons_co2e=result["annual_tons_co2e"],
        methodology=result["methodology"],
        methodology_label=result["methodology_label"],
        assumptions=result["assumptions"],
        confidence=result["confidence"],
        notes=result["notes"],
    )
    meta = {
        "estimated_annual_tons": result["annual_tons_co2e"],
        "suggested_methodology": result["methodology_label"],
        "revenue_projection": rev_proj,
    }
    return estimate_response, _to_response(cc, meta)


async def get_carbon_credit(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
) -> CarbonCreditResponse:
    cc = await _get_cc_or_raise(db, project_id, org_id)
    rev_proj = est.revenue_projection(float(cc.quantity_tons))
    meta = {
        "estimated_annual_tons": float(cc.quantity_tons),
        "suggested_methodology": cc.methodology,
        "revenue_projection": rev_proj,
    }
    return _to_response(cc, meta)


async def update_carbon_credit(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    body: CarbonCreditUpdate,
) -> CarbonCreditResponse:
    cc = await _get_cc_or_raise(db, project_id, org_id)
    if body.registry is not None:
        cc.registry = body.registry
    if body.methodology is not None:
        cc.methodology = body.methodology
    if body.vintage_year is not None:
        cc.vintage_year = body.vintage_year
    if body.quantity_tons is not None:
        cc.quantity_tons = Decimal(str(body.quantity_tons))
    if body.price_per_ton is not None:
        cc.price_per_ton = Decimal(str(body.price_per_ton))
    if body.currency is not None:
        cc.currency = body.currency
    if body.serial_number is not None:
        cc.serial_number = body.serial_number
    if body.verification_body is not None:
        cc.verification_body = body.verification_body

    await db.flush()
    await db.commit()
    await db.refresh(cc)
    return _to_response(cc)


async def update_verification_status(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    new_status: str,
    verification_body: str | None,
) -> CarbonCreditResponse:
    cc = await _get_cc_or_raise(db, project_id, org_id)
    try:
        cc.verification_status = CarbonVerificationStatus(new_status)
    except ValueError:
        raise ValueError(f"Invalid verification_status: {new_status}")
    if verification_body:
        cc.verification_body = verification_body
    await db.flush()
    await db.commit()
    await db.refresh(cc)
    return _to_response(cc)


async def list_on_marketplace(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
) -> CarbonCreditResponse:
    """Mark carbon credits as listed on marketplace (transitions from issued/verified → listed)."""
    cc = await _get_cc_or_raise(db, project_id, org_id)
    # Only progress forward: don't downgrade from verified/issued/retired
    if cc.verification_status not in (
        CarbonVerificationStatus.VERIFIED,
        CarbonVerificationStatus.ISSUED,
    ):
        raise ValueError(
            f"Credits must be verified or issued before listing. "
            f"Current status: {cc.verification_status.value}"
        )
    cc.verification_status = CarbonVerificationStatus.LISTED
    await db.flush()
    await db.commit()
    await db.refresh(cc)
    return _to_response(cc)


def get_pricing_trends() -> list[dict]:
    """Return synthetic pricing trend data (replace with real API in production)."""
    import datetime
    trends = []
    base_date = datetime.date(2023, 1, 1)
    for i in range(24):
        d = base_date.replace(month=(i % 12) + 1, year=base_date.year + (i // 12))
        trends.append({
            "date": d.isoformat(),
            "vcs_price": round(8.5 + i * 0.3 + (i % 3) * 0.5, 2),
            "gold_standard_price": round(12.0 + i * 0.4 + (i % 5) * 0.6, 2),
            "eu_ets_price": round(55.0 + i * 0.8 + (i % 4) * 2.0, 2),
        })
    return trends


def get_methodologies() -> list[dict]:
    return est.AVAILABLE_METHODOLOGIES
