"""Impact measurement service: SDG mapping, KPIs, carbon credits, additionality."""

import uuid
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CarbonVerificationStatus
from app.models.financial import CarbonCredit
from app.models.projects import Project, SignalScore
from app.modules.impact.schemas import (
    AdditionalityResponse,
    CarbonCreditCreateRequest,
    CarbonCreditListResponse,
    CarbonCreditResponse,
    CarbonCreditUpdateRequest,
    ImpactKPI,
    PortfolioImpactResponse,
    ProjectImpactResponse,
    SDGGoal,
    SDGMappingRequest,
    SDGSummary,
    SDG_METADATA,
)

logger = structlog.get_logger()

# ── KPI catalogue ─────────────────────────────────────────────────────────────

KPI_CATALOGUE: list[dict] = [
    {"key": "capacity_mw",             "label": "Installed Capacity",        "unit": "MW",    "category": "energy"},
    {"key": "energy_output_gwh",       "label": "Annual Energy Output",      "unit": "GWh",   "category": "energy"},
    {"key": "households_served",       "label": "Households Served",         "unit": "HH",    "category": "energy"},
    {"key": "co2_reduction_tco2e",     "label": "CO₂ Reduction",             "unit": "tCO₂e", "category": "environment"},
    {"key": "land_restored_ha",        "label": "Land Restored",             "unit": "ha",    "category": "environment"},
    {"key": "water_saved_m3",          "label": "Water Saved",               "unit": "m³",    "category": "environment"},
    {"key": "biodiversity_index",      "label": "Biodiversity Index",        "unit": "score", "category": "environment"},
    {"key": "jobs_created_direct",     "label": "Direct Jobs Created",       "unit": "jobs",  "category": "social"},
    {"key": "jobs_created_indirect",   "label": "Indirect Jobs",             "unit": "jobs",  "category": "social"},
    {"key": "women_employed_pct",      "label": "Women Employed",            "unit": "%",     "category": "social"},
    {"key": "local_content_pct",       "label": "Local Content",             "unit": "%",     "category": "social"},
    {"key": "community_fund_usd",      "label": "Community Fund",            "unit": "USD",   "category": "social"},
    {"key": "tax_revenue_usd",         "label": "Tax Revenue Generated",     "unit": "USD",   "category": "economic"},
    {"key": "local_procurement_pct",   "label": "Local Procurement",         "unit": "%",     "category": "economic"},
    {"key": "gdp_contribution_usd",    "label": "GDP Contribution",          "unit": "USD",   "category": "economic"},
]

KPI_MAP = {k["key"]: k for k in KPI_CATALOGUE}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _sdg_from_raw(raw_goals: list[dict]) -> list[SDGGoal]:
    result = []
    for g in raw_goals:
        n = g.get("number")
        if n in SDG_METADATA:
            result.append(
                SDGGoal(
                    number=n,
                    label=SDG_METADATA[n]["label"],
                    color=SDG_METADATA[n]["color"],
                    contribution_level=g.get("contribution_level", "secondary"),
                    description=g.get("description", ""),
                )
            )
    return result


def _kpis_from_raw(raw_kpis: dict[str, Any], capacity_mw: Decimal | None) -> list[ImpactKPI]:
    result = []
    # Seed capacity_mw from project field if not in raw_kpis
    if capacity_mw is not None and "capacity_mw" not in raw_kpis:
        raw_kpis = {**raw_kpis, "capacity_mw": float(capacity_mw)}
    for cat_entry in KPI_CATALOGUE:
        k = cat_entry["key"]
        result.append(
            ImpactKPI(
                key=k,
                label=cat_entry["label"],
                value=raw_kpis.get(k),
                unit=cat_entry["unit"],
                category=cat_entry["category"],
            )
        )
    return result


async def _get_project(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> Project:
    proj = await db.get(Project, project_id)
    if not proj or proj.is_deleted or proj.org_id != org_id:
        raise LookupError(f"Project {project_id} not found")
    return proj


def _tech(proj: Project) -> dict[str, Any]:
    return dict(proj.technology_details or {})


# ── SDG ───────────────────────────────────────────────────────────────────────


async def update_sdg_mapping(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    body: SDGMappingRequest,
) -> SDGSummary:
    proj = await _get_project(db, project_id, org_id)
    tech = _tech(proj)
    tech["sdg_goals"] = body.goals
    proj.technology_details = tech
    return SDGSummary(
        project_id=proj.id,
        project_name=proj.name,
        goals=_sdg_from_raw(body.goals),
    )


async def get_sdg_summary(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> SDGSummary:
    proj = await _get_project(db, project_id, org_id)
    tech = _tech(proj)
    goals = _sdg_from_raw(tech.get("sdg_goals", []))
    return SDGSummary(project_id=proj.id, project_name=proj.name, goals=goals)


# ── KPIs ──────────────────────────────────────────────────────────────────────


async def update_impact_kpis(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    kpis: dict[str, float | None],
) -> ProjectImpactResponse:
    proj = await _get_project(db, project_id, org_id)
    tech = _tech(proj)
    raw_kpis = dict(tech.get("impact_kpis", {}))
    for k, v in kpis.items():
        if k in KPI_MAP:
            if v is None:
                raw_kpis.pop(k, None)
            else:
                raw_kpis[k] = v
    tech["impact_kpis"] = raw_kpis
    proj.technology_details = tech
    return await _build_project_impact(proj)


async def get_project_impact(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> ProjectImpactResponse:
    proj = await _get_project(db, project_id, org_id)
    return await _build_project_impact(proj)


async def _build_project_impact(proj: Project) -> ProjectImpactResponse:
    tech = _tech(proj)
    raw_kpis: dict[str, Any] = tech.get("impact_kpis", {})
    raw_goals: list[dict] = tech.get("sdg_goals", [])
    additionality = _calc_additionality(proj, raw_kpis)
    return ProjectImpactResponse(
        project_id=proj.id,
        project_name=proj.name,
        project_type=proj.project_type.value,
        geography_country=proj.geography_country,
        kpis=_kpis_from_raw(raw_kpis, proj.capacity_mw),
        sdg_goals=_sdg_from_raw(raw_goals),
        additionality_score=additionality["score"],
        additionality_breakdown=additionality["breakdown"],
    )


# ── Portfolio impact ──────────────────────────────────────────────────────────


async def get_portfolio_impact(
    db: AsyncSession, org_id: uuid.UUID
) -> PortfolioImpactResponse:
    result = await db.execute(
        select(Project).where(
            Project.org_id == org_id,
            Project.is_deleted.is_(False),
        )
    )
    projects = list(result.scalars().all())

    items: list[ProjectImpactResponse] = []
    total_mw = 0.0
    total_co2 = 0.0
    total_jobs = 0
    total_hh = 0
    sdg_set: set[int] = set()

    for proj in projects:
        pi = await _build_project_impact(proj)
        items.append(pi)
        kpi_map = {k.key: k.value for k in pi.kpis if k.value is not None}
        total_mw += kpi_map.get("capacity_mw", 0.0) or 0.0
        total_co2 += kpi_map.get("co2_reduction_tco2e", 0.0) or 0.0
        total_jobs += int(kpi_map.get("jobs_created_direct", 0) or 0)
        total_hh += int(kpi_map.get("households_served", 0) or 0)
        for g in pi.sdg_goals:
            sdg_set.add(g.number)

    # Carbon credits
    cc_result = await db.execute(
        select(CarbonCredit).where(
            CarbonCredit.org_id == org_id,
            CarbonCredit.is_deleted.is_(False),
        )
    )
    credits = list(cc_result.scalars().all())
    total_cc = sum(float(c.quantity_tons) for c in credits)

    return PortfolioImpactResponse(
        total_projects=len(projects),
        total_capacity_mw=total_mw,
        total_co2_reduction_tco2e=total_co2,
        total_jobs_created=total_jobs,
        total_households_served=total_hh,
        total_carbon_credit_tons=total_cc,
        sdg_coverage=sorted(sdg_set),
        projects=items,
    )


# ── Carbon credits ────────────────────────────────────────────────────────────


async def list_carbon_credits(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
) -> CarbonCreditListResponse:
    stmt = select(CarbonCredit).where(
        CarbonCredit.org_id == org_id,
        CarbonCredit.is_deleted.is_(False),
    )
    if project_id:
        stmt = stmt.where(CarbonCredit.project_id == project_id)
    stmt = stmt.order_by(CarbonCredit.created_at.desc())
    result = await db.execute(stmt)
    credits = list(result.scalars().all())

    def tons(status: CarbonVerificationStatus) -> float:
        return sum(
            float(c.quantity_tons)
            for c in credits
            if c.verification_status == status
        )

    return CarbonCreditListResponse(
        items=[_credit_to_response(c) for c in credits],
        total=len(credits),
        total_estimated=tons(CarbonVerificationStatus.ESTIMATED),
        total_verified=tons(CarbonVerificationStatus.VERIFIED),
        total_issued=tons(CarbonVerificationStatus.ISSUED),
        total_retired=tons(CarbonVerificationStatus.RETIRED),
    )


def _credit_to_response(c: CarbonCredit) -> CarbonCreditResponse:
    return CarbonCreditResponse(
        id=c.id,
        project_id=c.project_id,
        org_id=c.org_id,
        registry=c.registry,
        methodology=c.methodology,
        vintage_year=c.vintage_year,
        quantity_tons=str(c.quantity_tons),
        price_per_ton=str(c.price_per_ton) if c.price_per_ton is not None else None,
        currency=c.currency,
        serial_number=c.serial_number,
        verification_status=c.verification_status,
        verification_body=c.verification_body,
        issuance_date=c.issuance_date,
        retirement_date=c.retirement_date,
        created_at=c.created_at,
    )


async def create_carbon_credit(
    db: AsyncSession, org_id: uuid.UUID, body: CarbonCreditCreateRequest
) -> CarbonCredit:
    # Verify project belongs to org
    proj = await db.get(Project, body.project_id)
    if not proj or proj.is_deleted or proj.org_id != org_id:
        raise LookupError(f"Project {body.project_id} not found")

    cc = CarbonCredit(
        project_id=body.project_id,
        org_id=org_id,
        registry=body.registry,
        methodology=body.methodology,
        vintage_year=body.vintage_year,
        quantity_tons=body.quantity_tons,
        price_per_ton=body.price_per_ton,
        currency=body.currency,
        serial_number=body.serial_number,
        verification_status=body.verification_status,
        verification_body=body.verification_body,
        issuance_date=body.issuance_date,
        retirement_date=body.retirement_date,
    )
    db.add(cc)
    return cc


async def update_carbon_credit(
    db: AsyncSession,
    org_id: uuid.UUID,
    credit_id: uuid.UUID,
    body: CarbonCreditUpdateRequest,
) -> CarbonCredit:
    result = await db.execute(
        select(CarbonCredit).where(
            CarbonCredit.id == credit_id,
            CarbonCredit.org_id == org_id,
            CarbonCredit.is_deleted.is_(False),
        )
    )
    cc = result.scalar_one_or_none()
    if not cc:
        raise LookupError(f"Carbon credit {credit_id} not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(cc, field, value)
    return cc


# ── Additionality ─────────────────────────────────────────────────────────────

# High-need geographies for private market investment
_HIGH_NEED_COUNTRIES = {
    "Nigeria", "Kenya", "Ethiopia", "Tanzania", "Uganda", "Ghana", "Senegal",
    "Rwanda", "Mozambique", "Zimbabwe", "Bangladesh", "Pakistan", "Nepal",
    "Cambodia", "Myanmar", "Laos", "Haiti", "Honduras", "Guatemala",
    "Bolivia", "Peru", "Colombia", "Indonesia", "Philippines", "Vietnam",
}

_RENEWABLE_TYPES = {
    "solar", "wind", "hydro", "geothermal", "biomass", "sustainable_agriculture",
}


def _calc_additionality(proj: Project, raw_kpis: dict[str, Any]) -> dict:
    breakdown: dict[str, dict] = {}
    score = 0

    # 1. Geographic need (25 pts): high-need developing country = 25, others = 15
    if proj.geography_country in _HIGH_NEED_COUNTRIES:
        geo_score = 25
        geo_rationale = "Project in high-need geography with strong private market investment potential."
    else:
        geo_score = 15
        geo_rationale = "Project in moderate-need geography."
    score += geo_score
    breakdown["geographic_need"] = {"score": geo_score, "max": 25, "rationale": geo_rationale}

    # 2. Technology type (20 pts): proven renewable = 20, efficiency/buildings = 15, other = 10
    ptype = proj.project_type.value
    if ptype in ("solar", "wind", "hydro", "geothermal"):
        tech_score = 20
        tech_rationale = "Proven renewable technology with measurable impact."
    elif ptype in ("energy_efficiency", "green_building", "biomass", "sustainable_agriculture"):
        tech_score = 15
        tech_rationale = "High-impact sustainability technology."
    else:
        tech_score = 10
        tech_rationale = "Technology type has moderate additionality."
    score += tech_score
    breakdown["technology_type"] = {"score": tech_score, "max": 20, "rationale": tech_rationale}

    # 3. Project stage (20 pts): earlier stage = more additional
    stage_scores = {
        "concept": 20, "pre_development": 18, "development": 15,
        "construction_ready": 10, "under_construction": 5, "operational": 2,
    }
    stage_val = proj.stage.value
    stage_score = stage_scores.get(stage_val, 10)
    if stage_score >= 15:
        stage_rationale = "Early-stage project demonstrates high additionality need for financing."
    else:
        stage_rationale = "Later-stage project has lower financing barrier."
    score += stage_score
    breakdown["project_stage"] = {"score": stage_score, "max": 20, "rationale": stage_rationale}

    # 4. CO₂ impact (20 pts): based on co2_reduction_tco2e KPI
    co2 = float(raw_kpis.get("co2_reduction_tco2e", 0) or 0)
    if co2 >= 50_000:
        co2_score = 20
    elif co2 >= 10_000:
        co2_score = 15
    elif co2 >= 1_000:
        co2_score = 10
    elif co2 > 0:
        co2_score = 5
    else:
        co2_score = 0
    co2_rationale = (
        f"CO₂ reduction of {co2:,.0f} tCO₂e." if co2 > 0 else "No CO₂ reduction data provided."
    )
    score += co2_score
    breakdown["co2_impact"] = {"score": co2_score, "max": 20, "rationale": co2_rationale}

    # 5. Social co-benefits (15 pts): jobs + households
    jobs = int(raw_kpis.get("jobs_created_direct", 0) or 0)
    hh = int(raw_kpis.get("households_served", 0) or 0)
    if jobs >= 100 or hh >= 10_000:
        social_score = 15
    elif jobs >= 20 or hh >= 1_000:
        social_score = 10
    elif jobs > 0 or hh > 0:
        social_score = 5
    else:
        social_score = 0
    social_rationale = f"{jobs} direct jobs; {hh:,} households served."
    score += social_score
    breakdown["social_co_benefits"] = {"score": social_score, "max": 15, "rationale": social_rationale}

    # Rating
    if score >= 70:
        rating = "high"
    elif score >= 45:
        rating = "medium"
    else:
        rating = "low"

    # Recommendations
    recs: list[str] = []
    if not raw_kpis.get("co2_reduction_tco2e"):
        recs.append("Add CO₂ reduction estimate to improve additionality score.")
    if not raw_kpis.get("jobs_created_direct"):
        recs.append("Document direct job creation for social co-benefit scoring.")
    if not raw_kpis.get("households_served"):
        recs.append("Estimate households served to strengthen social impact evidence.")
    if proj.stage.value in ("construction_ready", "under_construction", "operational"):
        recs.append("Consider documenting financing barriers overcome to evidence additionality.")

    return {"score": score, "rating": rating, "breakdown": breakdown, "recommendations": recs}


async def get_additionality(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> AdditionalityResponse:
    proj = await _get_project(db, project_id, org_id)
    tech = _tech(proj)
    raw_kpis: dict[str, Any] = tech.get("impact_kpis", {})
    result = _calc_additionality(proj, raw_kpis)
    return AdditionalityResponse(
        project_id=proj.id,
        score=result["score"],
        rating=result["rating"],
        breakdown=result["breakdown"],
        recommendations=result["recommendations"],
    )
