"""Insurance module service — AI-powered coverage analysis and recommendations."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.investors import RiskAssessment
from app.models.projects import Project, SignalScore
from app.modules.insurance.schemas import (
    CoverageRecommendation,
    InsuranceImpactResponse,
    InsuranceSummaryResponse,
)

logger = structlog.get_logger()

_TIMEOUT = 60.0

# ── Coverage type → human label mapping ──────────────────────────────────────

_COVERAGE_LABELS: dict[str, str] = {
    "construction_all_risk": "Construction All-Risk (CAR)",
    "operational_all_risk": "Operational All-Risk (OAR)",
    "third_party_liability": "Third-Party Liability",
    "business_interruption": "Business Interruption",
    "political_risk": "Political Risk",
    "environmental_liability": "Environmental Liability",
    "directors_officers": "Directors & Officers (D&O)",
    "cyber_liability": "Cyber Liability",
    "machinery_breakdown": "Machinery Breakdown",
    "weather_parametric": "Weather / Parametric",
}

# ── Project-type baseline premiums (% of total investment, annual) ────────────

_BASE_PREMIUM_PCT: dict[str, float] = {
    "solar": 0.45,
    "wind": 0.55,
    "hydro": 0.60,
    "geothermal": 0.80,
    "biomass": 0.70,
    "real_estate": 0.30,
    "infrastructure": 0.50,
    "agribusiness": 0.65,
    "sustainable_agriculture": 0.65,
    "water": 0.55,
    "waste": 0.60,
}

# ── High-risk geography premium surcharge (%) ─────────────────────────────────

_HIGH_RISK_GEOS: set[str] = {
    "Nigeria", "Ethiopia", "Tanzania", "Kenya", "Bangladesh",
    "Pakistan", "Myanmar", "Cambodia", "Haiti", "Sudan",
}


def _geo_premium_multiplier(country: str) -> float:
    return 1.40 if country in _HIGH_RISK_GEOS else 1.0


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_project_or_raise(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> Project:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.org_id == org_id,
            Project.is_deleted.is_(False),
        )
    )
    proj = result.scalar_one_or_none()
    if not proj:
        raise LookupError(f"Project {project_id} not found")
    return proj


async def _get_latest_signal_score(
    db: AsyncSession, project_id: uuid.UUID
) -> SignalScore | None:
    result = await db.execute(
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.calculated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ── Deterministic fallback logic ──────────────────────────────────────────────


def _build_fallback_recommendations(
    project_type: str, stage: str, geography: str
) -> list[CoverageRecommendation]:
    """Return rule-based coverage recommendations."""
    recs: list[CoverageRecommendation] = []

    is_construction = stage in {"concept", "development", "pre_construction", "construction"}
    is_operational = stage in {"operational", "asset_management"}
    is_high_risk_geo = geography in _HIGH_RISK_GEOS

    if is_construction:
        recs.append(CoverageRecommendation(
            policy_type="construction_all_risk",
            label=_COVERAGE_LABELS["construction_all_risk"],
            is_mandatory=True,
            typical_coverage_pct=100.0,
            rationale="Mandatory lender requirement covering physical damage during construction.",
            priority="critical",
        ))
        recs.append(CoverageRecommendation(
            policy_type="third_party_liability",
            label=_COVERAGE_LABELS["third_party_liability"],
            is_mandatory=True,
            typical_coverage_pct=10.0,
            rationale="Required by EPC contractors and lenders for bodily injury and property damage claims.",
            priority="critical",
        ))

    if is_operational:
        recs.append(CoverageRecommendation(
            policy_type="operational_all_risk",
            label=_COVERAGE_LABELS["operational_all_risk"],
            is_mandatory=True,
            typical_coverage_pct=100.0,
            rationale="Core operational coverage for physical damage to the asset.",
            priority="critical",
        ))
        recs.append(CoverageRecommendation(
            policy_type="business_interruption",
            label=_COVERAGE_LABELS["business_interruption"],
            is_mandatory=True,
            typical_coverage_pct=18.0,
            rationale="Covers revenue loss during unplanned outages; typically 18-month indemnity period.",
            priority="critical",
        ))
        recs.append(CoverageRecommendation(
            policy_type="machinery_breakdown",
            label=_COVERAGE_LABELS["machinery_breakdown"],
            is_mandatory=False,
            typical_coverage_pct=50.0,
            rationale="Covers sudden mechanical breakdown not covered by OAR policy.",
            priority="high",
        ))

    if is_high_risk_geo:
        recs.append(CoverageRecommendation(
            policy_type="political_risk",
            label=_COVERAGE_LABELS["political_risk"],
            is_mandatory=True,
            typical_coverage_pct=100.0,
            rationale=f"Required for investments in {geography} to cover expropriation, currency inconvertibility, and political violence.",
            priority="critical",
        ))

    if project_type in {"geothermal", "hydro", "wind"}:
        recs.append(CoverageRecommendation(
            policy_type="weather_parametric",
            label=_COVERAGE_LABELS["weather_parametric"],
            is_mandatory=False,
            typical_coverage_pct=30.0,
            rationale="Parametric cover protecting against below-P90 resource yield years.",
            priority="medium",
        ))

    recs.append(CoverageRecommendation(
        policy_type="environmental_liability",
        label=_COVERAGE_LABELS["environmental_liability"],
        is_mandatory=False,
        typical_coverage_pct=20.0,
        rationale="Covers environmental clean-up costs and third-party claims.",
        priority="medium",
    ))

    recs.append(CoverageRecommendation(
        policy_type="directors_officers",
        label=_COVERAGE_LABELS["directors_officers"],
        is_mandatory=False,
        typical_coverage_pct=5.0,
        rationale="Protects management against personal liability from investment decisions.",
        priority="low",
    ))

    return recs


def _compute_financial_impact(
    total_investment: float,
    annual_premium_pct: float,
    discount_rate: float = 0.10,
    project_life_years: int = 20,
) -> tuple[int, float]:
    """Return (irr_impact_bps, npv_premium_cost)."""
    # IRR impact: rough proxy — annual premium as % of equity (assume 30% equity)
    equity = total_investment * 0.30
    annual_premium = total_investment * (annual_premium_pct / 100)
    irr_impact_bps = -int((annual_premium / equity) * 10_000) if equity > 0 else 0

    # NPV of premium stream (annuity)
    if discount_rate > 0:
        annuity_factor = (1 - (1 + discount_rate) ** (-project_life_years)) / discount_rate
    else:
        annuity_factor = project_life_years
    npv_premium_cost = annual_premium * annuity_factor

    return irr_impact_bps, npv_premium_cost


# ── AI narrative generation ───────────────────────────────────────────────────


async def _generate_ai_narrative(
    project_name: str,
    project_type: str,
    geography: str,
    stage: str,
    total_investment: float,
    currency: str,
    recommendations: list[CoverageRecommendation],
    risk_reduction_score: int,
) -> str:
    """Generate an LP-ready insurance narrative via AI Gateway."""
    rec_summary = ", ".join(r.label for r in recommendations if r.is_mandatory)
    prompt = f"""You are a senior infrastructure insurance advisor writing an insurance section for an LP investment memo.

Project: {project_name} ({project_type.replace("_", " ").title()})
Geography: {geography}
Stage: {stage.replace("_", " ").title()}
Total Investment: {currency} {total_investment:,.0f}
Mandatory Coverage: {rec_summary}
Risk Reduction Score: {risk_reduction_score}/100

Write 2-3 concise sentences describing the insurance programme for this project. Be specific about coverage types and their role in protecting investor returns. Use professional investment banking style. Output plain prose only."""

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={
                    "prompt": prompt,
                    "task_type": "analysis",
                    "max_tokens": 200,
                    "temperature": 0.3,
                },
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
            )
            resp.raise_for_status()
            return resp.json().get("content", "").strip()
    except Exception as exc:
        logger.warning("insurance_narrative_failed", error=str(exc))
        return (
            f"The {project_name} insurance programme includes {rec_summary}, "
            f"providing comprehensive risk transfer across the project lifecycle. "
            f"The coverage structure achieves a risk reduction score of {risk_reduction_score}/100, "
            f"materially protecting investor returns against insurable loss events."
        )


# ── Main service functions ────────────────────────────────────────────────────


async def get_insurance_impact(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
) -> InsuranceImpactResponse:
    """Generate comprehensive insurance impact analysis for a project."""
    proj = await _get_project_or_raise(db, project_id, org_id)
    signal = await _get_latest_signal_score(db, project_id)

    project_type = proj.project_type.value
    geography = proj.geography_country
    stage = proj.stage.value
    total_investment = float(proj.total_investment_required)
    currency = proj.currency

    # Recommendations
    recommendations = _build_fallback_recommendations(project_type, stage, geography)

    # Premium estimate
    base_pct = _BASE_PREMIUM_PCT.get(project_type, 0.50)
    multiplier = _geo_premium_multiplier(geography)
    annual_premium_pct = base_pct * multiplier
    annual_premium = total_investment * (annual_premium_pct / 100)

    # Coverage adequacy
    mandatory_count = sum(1 for r in recommendations if r.is_mandatory)
    if mandatory_count >= 3:
        coverage_adequacy = "good"
    elif mandatory_count >= 2:
        coverage_adequacy = "partial"
    else:
        coverage_adequacy = "insufficient"

    # Risk reduction
    base_signal = float(signal.overall_score) if signal else 50.0
    risk_reduction_score = min(85, int(mandatory_count * 15 + base_signal * 0.3))

    # Uncovered risk areas
    covered = {r.policy_type for r in recommendations}
    potential_gaps = {
        "cyber_liability": "Cyber and data security risk not covered",
        "weather_parametric": "Resource variability risk not transferred",
        "directors_officers": "Management liability not covered",
    }
    uncovered_risk_areas = [
        v for k, v in potential_gaps.items() if k not in covered
    ]

    # Financial impact
    irr_impact_bps, npv_premium_cost = _compute_financial_impact(
        total_investment, annual_premium_pct
    )

    # AI narrative
    ai_narrative = await _generate_ai_narrative(
        proj.name, project_type, geography, stage,
        total_investment, currency, recommendations, risk_reduction_score,
    )

    return InsuranceImpactResponse(
        project_id=project_id,
        project_name=proj.name,
        project_type=project_type,
        geography=geography,
        total_investment=total_investment,
        currency=currency,
        recommended_coverage_types=[r.policy_type for r in recommendations],
        estimated_annual_premium_pct=round(annual_premium_pct, 2),
        estimated_annual_premium=round(annual_premium, 2),
        risk_reduction_score=risk_reduction_score,
        coverage_adequacy=coverage_adequacy,
        uncovered_risk_areas=uncovered_risk_areas,
        irr_impact_bps=irr_impact_bps,
        npv_premium_cost=round(npv_premium_cost, 2),
        recommendations=recommendations,
        ai_narrative=ai_narrative,
        analyzed_at=datetime.now(timezone.utc),
    )


async def get_insurance_summary(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
) -> InsuranceSummaryResponse:
    """Lightweight summary without full AI narrative."""
    proj = await _get_project_or_raise(db, project_id, org_id)
    signal = await _get_latest_signal_score(db, project_id)

    project_type = proj.project_type.value
    geography = proj.geography_country
    stage = proj.stage.value
    total_investment = float(proj.total_investment_required)

    recommendations = _build_fallback_recommendations(project_type, stage, geography)
    mandatory_count = sum(1 for r in recommendations if r.is_mandatory)
    base_pct = _BASE_PREMIUM_PCT.get(project_type, 0.50)
    multiplier = _geo_premium_multiplier(geography)
    annual_premium = total_investment * (base_pct * multiplier / 100)

    base_signal = float(signal.overall_score) if signal else 50.0
    risk_reduction_score = min(85, int(mandatory_count * 15 + base_signal * 0.3))

    covered = {r.policy_type for r in recommendations}
    gaps = [
        _COVERAGE_LABELS.get(k, k) for k in ["cyber_liability", "weather_parametric"]
        if k not in covered
    ]

    if mandatory_count >= 3:
        adequacy = "good"
    elif mandatory_count >= 2:
        adequacy = "partial"
    else:
        adequacy = "insufficient"

    top_rec = recommendations[0].label if recommendations else None

    return InsuranceSummaryResponse(
        project_id=project_id,
        coverage_adequacy=adequacy,
        risk_reduction_score=risk_reduction_score,
        estimated_annual_premium=round(annual_premium, 2),
        currency=proj.currency,
        coverage_gaps=gaps,
        top_recommendation=top_rec,
    )


# ── Ralph AI compatibility shim (called as risk_service.get_insurance_impact_analysis) ──

async def get_insurance_impact_analysis(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
) -> InsuranceImpactResponse:
    """Alias used by ralph_ai/tools.py via risk service."""
    return await get_insurance_impact(db, org_id, project_id)
