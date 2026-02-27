"""Risk Analysis & Compliance service.

All financial / scoring calculations are deterministic Python.
AI Gateway is used ONLY for compliance narrative generation.
"""

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant import tenant_filter
from app.models.advisory import MonitoringAlert
from app.models.core import AuditLog
from app.models.enums import (
    HoldingStatus,
    MonitoringAlertDomain,
    MonitoringAlertSeverity,
    MonitoringAlertType,
    RiskAssessmentStatus,
    RiskEntityType,
    RiskProbability,
    RiskSeverity,
    RiskType,
    SFDRClassification,
)
from app.models.investors import Portfolio, PortfolioHolding, PortfolioMetrics, RiskAssessment
from app.models.projects import Project, SignalScore
from app.modules.portfolio.service import _get_portfolio_or_raise
from app.modules.risk.schemas import (
    AlertResolveRequest,
    AuditEntry,
    AuditTrailResponse,
    AutoRiskItem,
    ComplianceStatusResponse,
    ConcentrationAnalysisResponse,
    ConcentrationItem,
    DNSHCheck,
    ESGDimensionScore,
    ESGScoreResponse,
    FiveDomainRiskResponse,
    HeatmapCell,
    HoldingImpact,
    MitigationResponse,
    MonitoringAlertListResponse,
    MonitoringAlertResponse,
    PAIIndicator,
    RiskAssessmentResponse,
    RiskAssessmentCreate,
    RiskDashboardResponse,
    RiskDomainScore,
    RiskHeatmapResponse,
    RiskTrendPoint,
    ScenarioResult,
    TaxonomyResult,
)

logger = structlog.get_logger()

# ── Severity / Probability numeric weights ────────────────────────────────────

_SEVERITY_WEIGHT: dict[str, float] = {
    "low": 1, "medium": 2, "high": 3, "critical": 4,
}
_PROB_WEIGHT: dict[str, float] = {
    "unlikely": 1, "possible": 2, "likely": 3, "very_likely": 4,
}

# Climate risk per project type
_CLIMATE_RISK: dict[str, dict[str, str]] = {
    "solar":                  {"physical": "medium",  "transition": "low"},
    "wind":                   {"physical": "medium",  "transition": "low"},
    "hydro":                  {"physical": "high",    "transition": "low"},
    "biomass":                {"physical": "low",     "transition": "medium"},
    "geothermal":             {"physical": "low",     "transition": "low"},
    "energy_efficiency":      {"physical": "low",     "transition": "low"},
    "green_building":         {"physical": "medium",  "transition": "low"},
    "sustainable_agriculture":{"physical": "high",    "transition": "medium"},
    "other":                  {"physical": "medium",  "transition": "medium"},
}

# Regulatory risk: high-scrutiny jurisdictions
_HIGH_REG_COUNTRIES = {"CN", "RU", "BR", "IN", "NG", "PK"}

# EU Taxonomy eligible project types and their economic activity descriptions
_TAXONOMY_ACTIVITIES: dict[str, str] = {
    "solar":                  "4.1 Electricity generation using solar photovoltaic technology",
    "wind":                   "4.3 Electricity generation from wind power",
    "hydro":                  "4.5 Electricity generation from hydropower",
    "biomass":                "4.6 Electricity generation from bioenergy",
    "geothermal":             "4.7 Electricity generation from geothermal energy",
    "energy_efficiency":      "7.2 Renovation of existing buildings",
    "green_building":         "7.1 Construction of new buildings",
    "sustainable_agriculture":"1.1 Crop production",
}

# PAI indicator definitions (14 mandatory SFDR indicators)
_PAI_INDICATORS = [
    (1,  "GHG emissions scope 1",             "Climate",      "tCO2e/year"),
    (2,  "GHG emissions scope 2",             "Climate",      "tCO2e/year"),
    (3,  "GHG emissions scope 3",             "Climate",      "tCO2e/year"),
    (4,  "Carbon footprint",                  "Climate",      "tCO2e/€M invested"),
    (5,  "GHG intensity of investee companies","Climate",     "tCO2e/€M revenue"),
    (6,  "Fossil fuel exposure",              "Climate",      "%"),
    (7,  "Carbon-intensive energy consumption",  "Climate",    "%"),
    (8,  "Energy consumption intensity",      "Climate",      "MWh/€M revenue"),
    (9,  "Biodiversity-sensitive areas",      "Biodiversity", "Yes/No"),
    (10, "Water emissions",                   "Water",        "m³/year"),
    (11, "Hazardous waste ratio",             "Waste",        "%"),
    (12, "Anti-corruption policy violations", "Social",       "Number"),
    (13, "Unadjusted gender pay gap",         "Social",       "%"),
    (14, "Board gender diversity",            "Social",       "%"),
]

_DNSH_OBJECTIVES = [
    "Climate change mitigation",
    "Climate change adaptation",
    "Water and marine resources",
    "Circular economy",
    "Pollution prevention",
    "Biodiversity and ecosystems",
]


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _load_active_holdings(
    db: AsyncSession, portfolio_id: uuid.UUID
) -> list[PortfolioHolding]:
    stmt = select(PortfolioHolding).where(
        PortfolioHolding.portfolio_id == portfolio_id,
        PortfolioHolding.status == HoldingStatus.ACTIVE,
        PortfolioHolding.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _assessment_to_response(a: RiskAssessment) -> RiskAssessmentResponse:
    return RiskAssessmentResponse(
        id=a.id,
        entity_type=a.entity_type.value,
        entity_id=a.entity_id,
        risk_type=a.risk_type.value,
        severity=a.severity.value,
        probability=a.probability.value,
        description=a.description,
        mitigation=a.mitigation,
        status=a.status.value,
        assessed_by=a.assessed_by,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


def _risk_score(severity: str, probability: str) -> float:
    """0–16 score (severity × probability weight)."""
    return _SEVERITY_WEIGHT.get(severity, 1) * _PROB_WEIGHT.get(probability, 1)


# ── Risk Mapper ───────────────────────────────────────────────────────────────


class RiskMapper:
    """Automatically identifies risks from portfolio composition (pure/deterministic)."""

    def identify_risks(
        self,
        holdings: list[PortfolioHolding],
        projects: dict[uuid.UUID, Project],
    ) -> list[AutoRiskItem]:
        risks: list[AutoRiskItem] = []
        total_invested = sum(float(h.investment_amount) for h in holdings) or 1.0

        # ── Concentration ─────────────────────────────────────────
        sector_totals: dict[str, float] = defaultdict(float)
        geo_totals: dict[str, float] = defaultdict(float)
        currency_totals: dict[str, float] = defaultdict(float)

        for h in holdings:
            amt = float(h.investment_amount)
            proj = projects.get(h.project_id) if h.project_id else None
            if proj:
                sector_totals[proj.project_type.value] += amt
                geo_totals[proj.geography_country] += amt
            currency_totals[h.currency] += amt

        for sector, amt in sector_totals.items():
            if amt / total_invested > 0.25:
                risks.append(AutoRiskItem(
                    risk_type="concentration",
                    severity="high",
                    probability="likely",
                    description=f"Sector concentration: {sector} represents "
                                f"{amt / total_invested * 100:.1f}% of portfolio",
                ))

        for geo, amt in geo_totals.items():
            if amt / total_invested > 0.25:
                risks.append(AutoRiskItem(
                    risk_type="concentration",
                    severity="medium",
                    probability="possible",
                    description=f"Geographic concentration: {geo} represents "
                                f"{amt / total_invested * 100:.1f}% of portfolio",
                ))

        # ── Currency risk ─────────────────────────────────────────
        non_base_pct = sum(v for k, v in currency_totals.items() if k != "USD") / total_invested
        if non_base_pct > 0.1:
            risks.append(AutoRiskItem(
                risk_type="market",
                severity="medium",
                probability="possible",
                description=f"Currency risk: {non_base_pct * 100:.1f}% of holdings in non-USD currencies",
            ))

        # ── Liquidity risk ────────────────────────────────────────
        illiquid_pct = len(holdings) / max(len(holdings), 1)  # all infra is illiquid
        if illiquid_pct >= 0.8:
            risks.append(AutoRiskItem(
                risk_type="liquidity",
                severity="medium",
                probability="likely",
                description="High illiquidity: portfolio concentrated in illiquid infrastructure assets",
            ))

        # ── Climate risk ──────────────────────────────────────────
        climate_exposed = 0.0
        for h in holdings:
            proj = projects.get(h.project_id) if h.project_id else None
            if proj:
                cr = _CLIMATE_RISK.get(proj.project_type.value, {})
                if cr.get("physical") in ("high", "medium"):
                    climate_exposed += float(h.investment_amount)

        if climate_exposed / total_invested > 0.3:
            risks.append(AutoRiskItem(
                risk_type="climate",
                severity="high",
                probability="possible",
                description=f"Physical climate risk: {climate_exposed / total_invested * 100:.1f}% "
                            "of portfolio exposed to high/medium physical climate risk",
            ))

        # ── Regulatory risk ───────────────────────────────────────
        reg_exposed = 0.0
        for h in holdings:
            proj = projects.get(h.project_id) if h.project_id else None
            if proj and proj.geography_country in _HIGH_REG_COUNTRIES:
                reg_exposed += float(h.investment_amount)

        if reg_exposed > 0:
            risks.append(AutoRiskItem(
                risk_type="regulatory",
                severity="medium",
                probability="possible",
                description=f"Regulatory risk: {reg_exposed / total_invested * 100:.1f}% of portfolio "
                            "in high-scrutiny jurisdictions",
            ))

        # ── Counterparty risk ─────────────────────────────────────
        counterparty_totals: dict[uuid.UUID, float] = defaultdict(float)
        for h in holdings:
            if h.project_id:
                counterparty_totals[h.project_id] += float(h.investment_amount)

        for _pid, amt in counterparty_totals.items():
            if amt / total_invested > 0.25:
                risks.append(AutoRiskItem(
                    risk_type="counterparty",
                    severity="high",
                    probability="unlikely",
                    description=f"Counterparty concentration: single project represents "
                                f"{amt / total_invested * 100:.1f}% of portfolio",
                ))

        return risks


# ── Scenario Engine ───────────────────────────────────────────────────────────


class ScenarioEngine:
    """Deterministic scenario modelling on portfolio holdings."""

    def run_scenario(
        self,
        holdings: list[PortfolioHolding],
        latest_metrics: PortfolioMetrics | None,
        scenario_type: str,
        parameters: dict[str, Any],
    ) -> ScenarioResult:
        nav_before = sum(float(h.current_value) for h in holdings)
        irr_before = float(latest_metrics.irr_net) if latest_metrics and latest_metrics.irr_net else None

        holding_impacts: list[HoldingImpact] = []
        waterfall: list[dict[str, Any]] = [{"label": "Baseline NAV", "value": nav_before}]

        for h in holdings:
            cv = float(h.current_value)
            stressed = self._stress_holding(h, cv, scenario_type, parameters)
            delta = stressed - cv
            delta_pct = (delta / cv * 100) if cv else 0.0
            holding_impacts.append(HoldingImpact(
                holding_id=h.id,
                asset_name=h.asset_name,
                current_value=cv,
                stressed_value=round(stressed, 2),
                delta_value=round(delta, 2),
                delta_pct=round(delta_pct, 2),
            ))
            if abs(delta) > 0.01:
                waterfall.append({"label": h.asset_name, "value": round(delta, 2)})

        nav_after = sum(i.stressed_value for i in holding_impacts)
        waterfall.append({"label": "Stressed NAV", "value": round(nav_after, 2)})

        nav_delta = nav_after - nav_before
        nav_delta_pct = (nav_delta / nav_before * 100) if nav_before else 0.0

        # Approximate stressed IRR: shift proportionally
        irr_after: float | None = None
        if irr_before is not None and nav_before > 0:
            irr_shift = (nav_delta / nav_before) * irr_before * 0.5
            irr_after = round(irr_before + irr_shift, 4)

        narrative = self._build_narrative(scenario_type, parameters, nav_delta_pct)

        return ScenarioResult(
            scenario_type=scenario_type,
            parameters=parameters,
            nav_before=round(nav_before, 2),
            irr_before=round(irr_before, 4) if irr_before is not None else None,
            nav_after=round(nav_after, 2),
            irr_after=irr_after,
            nav_delta=round(nav_delta, 2),
            nav_delta_pct=round(nav_delta_pct, 2),
            holding_impacts=holding_impacts,
            waterfall=waterfall,
            narrative=narrative,
        )

    def _stress_holding(
        self,
        holding: PortfolioHolding,
        current_value: float,
        scenario_type: str,
        parameters: dict[str, Any],
    ) -> float:
        if scenario_type == "interest_rate_shock":
            bps = float(parameters.get("basis_points", 200))
            duration = float(parameters.get("duration_years", 10))
            # Modified duration approximation: ΔP/P ≈ -D × Δr
            delta_r = bps / 10000
            haircut = min(duration * delta_r, 0.5)
            return current_value * (1 - haircut)

        elif scenario_type == "carbon_price_change":
            pct = float(parameters.get("pct_change", -30)) / 100
            # Only carbon-revenue projects affected
            if holding.asset_type.value in ("equity", "debt"):
                exposure = float(parameters.get("carbon_revenue_pct", 0.15))
                return current_value * (1 + pct * exposure)
            return current_value

        elif scenario_type == "technology_disruption":
            sectors = parameters.get("sectors", [])
            haircut_pct = float(parameters.get("haircut_pct", 15)) / 100
            # We can't filter by project type here (no DB in engine);
            # apply haircut to all holdings (conservative)
            if sectors:
                return current_value * (1 - haircut_pct)
            return current_value

        elif scenario_type == "regulatory_change":
            compliance_cost_pct = float(parameters.get("compliance_cost_pct", 5)) / 100
            return current_value * (1 - compliance_cost_pct)

        elif scenario_type == "climate_event":
            damage_pct = float(parameters.get("damage_pct", 20)) / 100
            affected_pct = float(parameters.get("portfolio_affected_pct", 0.3))
            # Apply damage to a fraction of each holding's value
            return current_value * (1 - damage_pct * affected_pct)

        elif scenario_type == "custom":
            nav_change_pct = float(parameters.get("nav_change_pct", 0)) / 100
            return current_value * (1 + nav_change_pct)

        return current_value

    def _build_narrative(
        self, scenario_type: str, parameters: dict[str, Any], nav_delta_pct: float
    ) -> str:
        direction = "decrease" if nav_delta_pct < 0 else "increase"
        magnitude = abs(round(nav_delta_pct, 1))
        labels = {
            "interest_rate_shock": f"an interest rate shock of {parameters.get('basis_points', '?')} basis points",
            "carbon_price_change": f"a {parameters.get('pct_change', '?')}% change in carbon price",
            "technology_disruption": "technology disruption",
            "regulatory_change": "a regulatory change scenario",
            "climate_event": "a physical climate event",
            "custom": "a custom scenario",
        }
        label = labels.get(scenario_type, scenario_type)
        return (
            f"Under {label}, the portfolio NAV would {direction} by {magnitude}%. "
            f"This analysis uses deterministic cash-flow modelling applied to current holding valuations."
        )


# ── ESG Scoring Engine ────────────────────────────────────────────────────────


class ESGScoringEngine:
    """
    Deterministic ESG scoring.
    Environment 40% | Social 30% | Governance 30%.
    All formulas are rule-based Python. AI used only for data extraction.
    """

    def score_esg(
        self,
        project: Project,
        signal_score: SignalScore | None,
        esg_data: dict[str, Any],  # extracted from documents or project metadata
    ) -> ESGScoreResponse:
        env_sub = self._score_environment(project, signal_score, esg_data)
        soc_sub = self._score_social(project, esg_data)
        gov_sub = self._score_governance(project, esg_data)

        e_score = sum(env_sub.values()) / len(env_sub)
        s_score = sum(soc_sub.values()) / len(soc_sub)
        g_score = sum(gov_sub.values()) / len(gov_sub)
        overall = round(e_score * 0.4 + s_score * 0.3 + g_score * 0.3, 1)

        return ESGScoreResponse(
            project_id=project.id,
            overall_score=overall,
            environment=ESGDimensionScore(
                label="Environment",
                weight=0.4,
                score=round(e_score, 1),
                sub_scores=env_sub,
            ),
            social=ESGDimensionScore(
                label="Social",
                weight=0.3,
                score=round(s_score, 1),
                sub_scores=soc_sub,
            ),
            governance=ESGDimensionScore(
                label="Governance",
                weight=0.3,
                score=round(g_score, 1),
                sub_scores=gov_sub,
            ),
            methodology="Deterministic rule-based scoring v1.0",
        )

    # -- sub-dimension scorers --

    def _score_environment(
        self, project: Project, signal_score: SignalScore | None, esg: dict
    ) -> dict[str, float]:
        carbon_score = 100.0
        if project.project_type.value in ("biomass", "sustainable_agriculture"):
            carbon_score = 60.0
        elif project.project_type.value == "energy_efficiency":
            carbon_score = 90.0

        energy_score = 80.0
        if signal_score:
            energy_score = min(100, signal_score.technical_score * 1.1)

        biodiversity_score = float(esg.get("biodiversity_score", 70))
        water_score = float(esg.get("water_score", 70))

        return {
            "Carbon Footprint": round(carbon_score, 1),
            "Energy Efficiency": round(energy_score, 1),
            "Biodiversity Impact": round(biodiversity_score, 1),
            "Water & Waste": round(water_score, 1),
        }

    def _score_social(self, project: Project, esg: dict) -> dict[str, float]:
        jobs_score = min(100, float(esg.get("jobs_created", 0)) * 2)
        community_score = float(esg.get("community_score", 65))
        safety_score = float(esg.get("safety_score", 75))
        diversity_score = float(esg.get("diversity_score", 60))
        return {
            "Job Creation": round(jobs_score, 1),
            "Community Impact": round(community_score, 1),
            "Health & Safety": round(safety_score, 1),
            "Diversity & Inclusion": round(diversity_score, 1),
        }

    def _score_governance(self, project: Project, esg: dict) -> dict[str, float]:
        board_score = float(esg.get("board_score", 65))
        transparency = float(esg.get("transparency_score", 70))
        anti_corruption = float(esg.get("anti_corruption_score", 80))
        stakeholder = float(esg.get("stakeholder_score", 65))
        return {
            "Board Structure": round(board_score, 1),
            "Transparency": round(transparency, 1),
            "Anti-Corruption": round(anti_corruption, 1),
            "Stakeholder Engagement": round(stakeholder, 1),
        }


# ── Taxonomy Alignment Checker ────────────────────────────────────────────────


class TaxonomyAlignmentChecker:
    """EU Taxonomy alignment check (deterministic rule engine)."""

    def check_alignment(
        self, holding: PortfolioHolding, project: Project | None
    ) -> TaxonomyResult:
        if not project:
            return TaxonomyResult(
                holding_id=holding.id,
                asset_name=holding.asset_name,
                eligible=False,
                aligned=False,
                eligible_pct=0.0,
                aligned_pct=0.0,
                economic_activity="Unknown",
                dnsh_checks=[],
            )

        pt = project.project_type.value
        activity = _TAXONOMY_ACTIVITIES.get(pt, "")
        eligible = bool(activity)

        dnsh_checks: list[DNSHCheck] = []
        for obj in _DNSH_OBJECTIVES:
            if obj == "Climate change mitigation":
                status = "compliant" if pt in (
                    "solar", "wind", "hydro", "geothermal", "energy_efficiency"
                ) else "needs_assessment"
            elif obj == "Biodiversity and ecosystems":
                status = "needs_assessment"
            else:
                status = "compliant"
            dnsh_checks.append(DNSHCheck(
                objective=obj,
                status=status,
                notes=f"Assessment based on project type '{pt}'.",
            ))

        all_dnsh_ok = all(c.status != "non_compliant" for c in dnsh_checks)
        aligned = eligible and all_dnsh_ok

        return TaxonomyResult(
            holding_id=holding.id,
            asset_name=holding.asset_name,
            eligible=eligible,
            aligned=aligned,
            eligible_pct=100.0 if eligible else 0.0,
            aligned_pct=100.0 if aligned else 0.0,
            economic_activity=activity or "Not eligible",
            dnsh_checks=dnsh_checks,
        )


# ── Compliance Service ────────────────────────────────────────────────────────


class ComplianceService:
    """SFDR / EU Taxonomy compliance checks."""

    async def get_sfdr_status(
        self,
        db: AsyncSession,
        portfolio: Portfolio,
        holdings: list[PortfolioHolding],
        projects: dict[uuid.UUID, Project],
    ) -> ComplianceStatusResponse:
        checker = TaxonomyAlignmentChecker()

        taxonomy_results: list[TaxonomyResult] = []
        sustainable_value = 0.0
        total_value = sum(float(h.current_value) for h in holdings) or 1.0

        for h in holdings:
            proj = projects.get(h.project_id) if h.project_id else None
            result = checker.check_alignment(h, proj)
            taxonomy_results.append(result)
            if result.aligned:
                sustainable_value += float(h.current_value)

        eligible_value = sum(
            float(h.current_value)
            for h, r in zip(holdings, taxonomy_results)
            if r.eligible
        )

        sustainable_pct = round(sustainable_value / total_value * 100, 1)
        eligible_pct = round(eligible_value / total_value * 100, 1)
        aligned_pct = sustainable_pct  # same as aligned in our model

        pai_indicators = self._build_pai_indicators(holdings, projects)

        # Overall compliance status
        sfdr = portfolio.sfdr_classification
        if sfdr == SFDRClassification.ARTICLE_9:
            overall = "compliant" if sustainable_pct >= 80 else "needs_attention"
        elif sfdr == SFDRClassification.ARTICLE_8:
            overall = "compliant" if sustainable_pct >= 50 else "needs_attention"
        else:
            overall = "compliant"

        return ComplianceStatusResponse(
            portfolio_id=portfolio.id,
            sfdr_classification=sfdr.value,
            sustainable_investment_pct=sustainable_pct,
            taxonomy_eligible_pct=eligible_pct,
            taxonomy_aligned_pct=aligned_pct,
            pai_indicators=pai_indicators,
            taxonomy_results=taxonomy_results,
            overall_status=overall,
            last_assessed=datetime.now(timezone.utc),
        )

    def _build_pai_indicators(
        self,
        holdings: list[PortfolioHolding],
        projects: dict[uuid.UUID, Project],
    ) -> list[PAIIndicator]:
        indicators: list[PAIIndicator] = []
        for pai_id, name, category, unit in _PAI_INDICATORS:
            value, status = self._compute_pai(pai_id, holdings, projects)
            indicators.append(PAIIndicator(
                id=pai_id,
                name=name,
                category=category,
                value=value,
                unit=unit,
                status=status,
            ))
        return indicators

    def _compute_pai(
        self,
        pai_id: int,
        holdings: list[PortfolioHolding],
        projects: dict[uuid.UUID, Project],
    ) -> tuple[str | None, str]:
        """Return (value_str, status) for a PAI indicator."""
        # Deterministic estimates based on project types
        if pai_id == 6:  # Fossil fuel exposure
            fossil_value = sum(
                float(h.investment_amount)
                for h in holdings
                if projects.get(h.project_id, None) and
                projects[h.project_id].project_type.value in ("biomass",)
            )
            total = sum(float(h.investment_amount) for h in holdings) or 1.0
            pct = round(fossil_value / total * 100, 1)
            return str(pct), "met"
        elif pai_id == 9:  # Biodiversity-sensitive areas
            return "Under assessment", "needs_data"
        elif pai_id in (12, 13, 14):  # Social indicators
            return "Not reported", "needs_data"
        elif pai_id in (1, 2, 3):  # GHG scope 1/2/3
            # Estimate: renewable projects have ~0 scope 1/2 operational
            clean_types = {"solar", "wind", "hydro", "geothermal", "energy_efficiency"}
            clean_value = sum(
                float(h.investment_amount)
                for h in holdings
                if projects.get(h.project_id) and
                projects[h.project_id].project_type.value in clean_types
            )
            total = sum(float(h.investment_amount) for h in holdings) or 1.0
            clean_pct = clean_value / total
            if clean_pct >= 0.8:
                return "< 100 tCO2e", "met"
            return "Pending measurement", "needs_data"
        else:
            return "Pending data collection", "needs_data"


# ── Public service functions ──────────────────────────────────────────────────


async def get_risk_dashboard(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    org_id: uuid.UUID,
) -> RiskDashboardResponse:
    portfolio = await _get_portfolio_or_raise(db, portfolio_id, org_id)
    holdings = await _load_active_holdings(db, portfolio_id)

    # Load projects
    project_ids = {h.project_id for h in holdings if h.project_id}
    projects: dict[uuid.UUID, Project] = {}
    if project_ids:
        stmt = select(Project).where(Project.id.in_(project_ids))
        result = await db.execute(stmt)
        projects = {p.id: p for p in result.scalars().all()}

    # Load manual risk assessments
    stmt = select(RiskAssessment).where(
        RiskAssessment.org_id == org_id,
        RiskAssessment.entity_id == portfolio_id,
        RiskAssessment.is_deleted.is_(False),
    ).order_by(RiskAssessment.updated_at.desc()).limit(50)
    result = await db.execute(stmt)
    assessments = list(result.scalars().all())

    # Build heatmap from manual assessments
    cell_map: dict[tuple[str, str], list[uuid.UUID]] = defaultdict(list)
    for a in assessments:
        cell_map[(a.severity.value, a.probability.value)].append(a.id)

    heatmap_cells = [
        HeatmapCell(
            severity=sev,
            probability=prob,
            count=len(ids),
            risk_ids=ids,
        )
        for (sev, prob), ids in cell_map.items()
    ]

    # Top 5 risks (highest risk score first)
    sorted_assessments = sorted(
        assessments,
        key=lambda a: _risk_score(a.severity.value, a.probability.value),
        reverse=True,
    )
    top_risks = [_assessment_to_response(a) for a in sorted_assessments[:5]]

    # Auto-identified risks
    mapper = RiskMapper()
    auto_risks = mapper.identify_risks(holdings, projects)

    # Overall risk score: weighted average of all risks
    all_scores: list[float] = [
        _risk_score(a.severity.value, a.probability.value) * 100 / 16
        for a in assessments
    ] + [
        _risk_score(r.severity, r.probability) * 100 / 16
        for r in auto_risks
    ]
    overall = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0

    concentration = await get_concentration_analysis(db, portfolio_id, org_id)

    # Risk trend (stub: would come from historical snapshots in production)
    risk_trend = [
        RiskTrendPoint(date="2025-09", risk_score=max(0, overall - 8)),
        RiskTrendPoint(date="2025-10", risk_score=max(0, overall - 5)),
        RiskTrendPoint(date="2025-11", risk_score=max(0, overall - 3)),
        RiskTrendPoint(date="2025-12", risk_score=max(0, overall - 1)),
        RiskTrendPoint(date="2026-01", risk_score=max(0, overall)),
        RiskTrendPoint(date="2026-02", risk_score=overall),
    ]

    return RiskDashboardResponse(
        portfolio_id=portfolio_id,
        overall_risk_score=overall,
        heatmap=RiskHeatmapResponse(cells=heatmap_cells, total_risks=len(assessments)),
        top_risks=top_risks,
        auto_identified=auto_risks,
        concentration=concentration,
        risk_trend=risk_trend,
    )


async def create_risk_assessment(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    data: RiskAssessmentCreate,
) -> RiskAssessment:
    try:
        entity_type = RiskEntityType(data.entity_type)
        risk_type = RiskType(data.risk_type)
        severity = RiskSeverity(data.severity)
        probability = RiskProbability(data.probability)
        status = RiskAssessmentStatus(data.status)
    except ValueError as exc:
        raise ValueError(str(exc))

    assessment = RiskAssessment(
        org_id=org_id,
        entity_type=entity_type,
        entity_id=data.entity_id,
        risk_type=risk_type,
        severity=severity,
        probability=probability,
        description=data.description,
        mitigation=data.mitigation,
        status=status,
        assessed_by=user_id,
    )
    db.add(assessment)
    await db.flush()
    return assessment


async def get_risk_assessments(
    db: AsyncSession,
    org_id: uuid.UUID,
    entity_type: str | None,
    entity_id: uuid.UUID | None,
) -> list[RiskAssessment]:
    stmt = select(RiskAssessment).where(
        RiskAssessment.org_id == org_id,
        RiskAssessment.is_deleted.is_(False),
    )
    if entity_type:
        try:
            et = RiskEntityType(entity_type)
            stmt = stmt.where(RiskAssessment.entity_type == et)
        except ValueError:
            pass
    if entity_id:
        stmt = stmt.where(RiskAssessment.entity_id == entity_id)
    stmt = stmt.order_by(RiskAssessment.updated_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def run_scenario_analysis(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    org_id: uuid.UUID,
    scenario_type: str,
    parameters: dict[str, Any],
) -> ScenarioResult:
    await _get_portfolio_or_raise(db, portfolio_id, org_id)
    holdings = await _load_active_holdings(db, portfolio_id)

    metrics_stmt = (
        select(PortfolioMetrics)
        .where(PortfolioMetrics.portfolio_id == portfolio_id)
        .order_by(PortfolioMetrics.as_of_date.desc())
        .limit(1)
    )
    metrics_result = await db.execute(metrics_stmt)
    latest_metrics = metrics_result.scalar_one_or_none()

    engine = ScenarioEngine()
    return engine.run_scenario(holdings, latest_metrics, scenario_type, parameters)


async def get_concentration_analysis(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    org_id: uuid.UUID,
) -> ConcentrationAnalysisResponse:
    await _get_portfolio_or_raise(db, portfolio_id, org_id)
    holdings = await _load_active_holdings(db, portfolio_id)

    project_ids = {h.project_id for h in holdings if h.project_id}
    projects: dict[uuid.UUID, Project] = {}
    if project_ids:
        stmt = select(Project).where(Project.id.in_(project_ids))
        result = await db.execute(stmt)
        projects = {p.id: p for p in result.scalars().all()}

    total = sum(float(h.investment_amount) for h in holdings) or 1.0

    sector_map: dict[str, float] = defaultdict(float)
    geo_map: dict[str, float] = defaultdict(float)
    currency_map: dict[str, float] = defaultdict(float)
    counterparty_map: dict[str, float] = defaultdict(float)

    for h in holdings:
        amt = float(h.investment_amount)
        proj = projects.get(h.project_id) if h.project_id else None
        if proj:
            sector_map[proj.project_type.value] += amt
            geo_map[proj.geography_country] += amt
        counterparty_map[h.asset_name] += amt
        currency_map[h.currency] += amt

    def _items(mapping: dict[str, float]) -> list[ConcentrationItem]:
        return sorted(
            [
                ConcentrationItem(
                    label=k,
                    value=round(v, 2),
                    pct=round(v / total * 100, 1),
                    is_concentrated=v / total > 0.25,
                )
                for k, v in mapping.items()
            ],
            key=lambda x: x.value,
            reverse=True,
        )

    flags: list[str] = []
    for label, mapping in [
        ("Sector", sector_map),
        ("Geography", geo_map),
        ("Counterparty", counterparty_map),
    ]:
        for k, v in mapping.items():
            if v / total > 0.25:
                flags.append(
                    f"{label} concentration: {k} at {v / total * 100:.1f}%"
                )

    return ConcentrationAnalysisResponse(
        portfolio_id=portfolio_id,
        total_invested=round(total, 2),
        by_sector=_items(sector_map),
        by_geography=_items(geo_map),
        by_counterparty=_items(counterparty_map),
        by_currency=_items(currency_map),
        concentration_flags=flags,
    )


async def get_compliance_status(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    org_id: uuid.UUID,
) -> ComplianceStatusResponse:
    portfolio = await _get_portfolio_or_raise(db, portfolio_id, org_id)
    holdings = await _load_active_holdings(db, portfolio_id)

    project_ids = {h.project_id for h in holdings if h.project_id}
    projects: dict[uuid.UUID, Project] = {}
    if project_ids:
        stmt = select(Project).where(Project.id.in_(project_ids))
        result = await db.execute(stmt)
        projects = {p.id: p for p in result.scalars().all()}

    compliance_svc = ComplianceService()
    return await compliance_svc.get_sfdr_status(db, portfolio, holdings, projects)


async def get_audit_trail(
    db: AsyncSession,
    org_id: uuid.UUID,
    entity_type: str | None,
    entity_id: uuid.UUID | None,
    page: int = 1,
    page_size: int = 50,
) -> AuditTrailResponse:
    stmt = select(AuditLog).where(AuditLog.org_id == org_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(AuditLog.timestamp.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    items = [
        AuditEntry(
            id=log.id,
            timestamp=log.timestamp,
            user_id=log.user_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            changes=log.changes,
            ip_address=log.ip_address,
        )
        for log in logs
    ]

    return AuditTrailResponse(items=items, total=total)


# ── 5-Domain Risk Framework ───────────────────────────────────────────────────


def _domain_label(score: float | None) -> str:
    if score is None:
        return "Unknown"
    if score >= 75:
        return "Critical"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Medium"
    return "Low"


async def get_five_domain_scores(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    org_id: uuid.UUID,
) -> FiveDomainRiskResponse:
    """Return 5-domain risk scores for a portfolio.

    Loads from stored RiskAssessment domain scores if available,
    otherwise derives a deterministic estimate from portfolio assessments.
    """
    portfolio = await _get_portfolio_or_raise(db, portfolio_id, org_id)

    # Load the most recent RiskAssessment for this portfolio
    stmt = (
        select(RiskAssessment)
        .where(
            RiskAssessment.entity_type == RiskEntityType.PORTFOLIO,
            RiskAssessment.entity_id == portfolio_id,
            RiskAssessment.org_id == org_id,
        )
        .order_by(RiskAssessment.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    assessment = result.scalar_one_or_none()

    # Active alert count for this portfolio
    alert_count_stmt = select(func.count(MonitoringAlert.id)).where(
        MonitoringAlert.org_id == org_id,
        MonitoringAlert.portfolio_id == portfolio_id,
        MonitoringAlert.is_actioned.is_(False),
    )
    active_alerts = (await db.execute(alert_count_stmt)).scalar() or 0

    if assessment and assessment.overall_risk_score is not None:
        # Use stored domain scores from P01 schema
        domains = [
            RiskDomainScore(
                domain="market",
                score=float(assessment.market_risk_score) if assessment.market_risk_score else None,
                label=_domain_label(float(assessment.market_risk_score) if assessment.market_risk_score else None),
                details=assessment.market_risk_details,
                mitigation=assessment.market_risk_mitigation,
            ),
            RiskDomainScore(
                domain="climate",
                score=float(assessment.climate_risk_score) if assessment.climate_risk_score else None,
                label=_domain_label(float(assessment.climate_risk_score) if assessment.climate_risk_score else None),
                details=assessment.climate_risk_details,
                mitigation=assessment.climate_risk_mitigation,
            ),
            RiskDomainScore(
                domain="regulatory",
                score=float(assessment.regulatory_risk_score) if assessment.regulatory_risk_score else None,
                label=_domain_label(float(assessment.regulatory_risk_score) if assessment.regulatory_risk_score else None),
                details=assessment.regulatory_risk_details,
                mitigation=assessment.regulatory_risk_mitigation,
            ),
            RiskDomainScore(
                domain="technology",
                score=float(assessment.technology_risk_score) if assessment.technology_risk_score else None,
                label=_domain_label(float(assessment.technology_risk_score) if assessment.technology_risk_score else None),
                details=assessment.technology_risk_details,
                mitigation=assessment.technology_risk_mitigation,
            ),
            RiskDomainScore(
                domain="liquidity",
                score=float(assessment.liquidity_risk_score) if assessment.liquidity_risk_score else None,
                label=_domain_label(float(assessment.liquidity_risk_score) if assessment.liquidity_risk_score else None),
                details=assessment.liquidity_risk_details,
                mitigation=assessment.liquidity_risk_mitigation,
            ),
        ]
        return FiveDomainRiskResponse(
            portfolio_id=portfolio_id,
            overall_risk_score=float(assessment.overall_risk_score),
            domains=domains,
            monitoring_enabled=assessment.monitoring_enabled,
            last_monitoring_check=assessment.last_monitoring_check,
            active_alerts_count=active_alerts,
            source="stored",
        )

    # Fallback: derive estimates from auto-identified risks
    all_assessments_stmt = select(RiskAssessment).where(
        RiskAssessment.entity_type == RiskEntityType.PORTFOLIO,
        RiskAssessment.entity_id == portfolio_id,
        RiskAssessment.org_id == org_id,
    )
    all_result = await db.execute(all_assessments_stmt)
    all_assessments = list(all_result.scalars().all())

    # Map legacy risk types to domains
    domain_map: dict[str, str] = {
        "concentration": "market",
        "counterparty": "market",
        "currency": "market",
        "interest_rate": "market",
        "climate": "climate",
        "environmental": "climate",
        "regulatory": "regulatory",
        "compliance": "regulatory",
        "legal": "regulatory",
        "technology": "technology",
        "liquidity": "liquidity",
        "other": "market",
    }
    sev_weights = {"low": 15, "medium": 35, "high": 60, "critical": 85}
    domain_scores: dict[str, list[float]] = {d: [] for d in ["market", "climate", "regulatory", "technology", "liquidity"]}

    for a in all_assessments:
        domain = domain_map.get(a.risk_type.value if hasattr(a.risk_type, "value") else str(a.risk_type), "market")
        sev = a.severity.value if hasattr(a.severity, "value") else str(a.severity)
        domain_scores[domain].append(sev_weights.get(sev, 35))

    domains = []
    computed_scores = []
    for d in ["market", "climate", "regulatory", "technology", "liquidity"]:
        scores_for_domain = domain_scores[d]
        score: float | None = max(scores_for_domain) if scores_for_domain else None
        if score is not None:
            computed_scores.append(score)
        domains.append(
            RiskDomainScore(
                domain=d,
                score=score,
                label=_domain_label(score),
                details=None,
                mitigation=None,
            )
        )

    overall = round(sum(computed_scores) / len(computed_scores), 1) if computed_scores else None

    return FiveDomainRiskResponse(
        portfolio_id=portfolio_id,
        overall_risk_score=overall,
        domains=domains,
        monitoring_enabled=True,
        last_monitoring_check=None,
        active_alerts_count=active_alerts,
        source="computed",
    )


# ── Monitoring Alerts ─────────────────────────────────────────────────────────


async def get_monitoring_alerts(
    db: AsyncSession,
    org_id: uuid.UUID,
    portfolio_id: uuid.UUID | None = None,
    unread_only: bool = False,
) -> MonitoringAlertListResponse:
    """List monitoring alerts for an org, optionally filtered by portfolio."""
    stmt = select(MonitoringAlert).where(MonitoringAlert.org_id == org_id)
    if portfolio_id:
        stmt = stmt.where(MonitoringAlert.portfolio_id == portfolio_id)
    if unread_only:
        stmt = stmt.where(MonitoringAlert.is_read.is_(False))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(MonitoringAlert.created_at.desc()).limit(50)
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    items = [
        MonitoringAlertResponse(
            id=a.id,
            org_id=a.org_id,
            portfolio_id=a.portfolio_id,
            project_id=a.project_id,
            alert_type=a.alert_type.value,
            severity=a.severity.value,
            domain=a.domain.value,
            title=a.title,
            description=a.description,
            source_name=a.source_name,
            is_read=a.is_read,
            is_actioned=a.is_actioned,
            action_taken=a.action_taken,
            created_at=a.created_at,
        )
        for a in alerts
    ]
    return MonitoringAlertListResponse(items=items, total=total)


async def trigger_monitoring_check(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    org_id: uuid.UUID,
) -> dict[str, Any]:
    """Stub: generate sample alerts from heuristic thresholds.

    In production this would call external data providers.
    """
    portfolio = await _get_portfolio_or_raise(db, portfolio_id, org_id)

    # Check concentration risk
    holdings_stmt = select(PortfolioHolding).where(
        PortfolioHolding.portfolio_id == portfolio_id,
        PortfolioHolding.org_id == org_id,
        PortfolioHolding.status == HoldingStatus.ACTIVE,
    )
    holdings_result = await db.execute(holdings_stmt)
    holdings = list(holdings_result.scalars().all())

    alerts_created = 0

    if holdings:
        total_value = sum(float(h.current_value) for h in holdings)
        if total_value > 0:
            for h in holdings:
                pct = float(h.current_value) / total_value
                if pct > 0.30:
                    alert = MonitoringAlert(
                        org_id=org_id,
                        portfolio_id=portfolio_id,
                        alert_type=MonitoringAlertType.RISK_THRESHOLD,
                        severity=MonitoringAlertSeverity.WARNING,
                        domain=MonitoringAlertDomain.MARKET,
                        title=f"Concentration risk: {h.asset_name}",
                        description=(
                            f"{h.asset_name} represents {pct*100:.1f}% of portfolio value, "
                            f"exceeding the 30% concentration threshold."
                        ),
                        source_name="SCR Risk Monitor",
                        affected_entities={"holding_id": str(h.id), "asset_name": h.asset_name},
                    )
                    db.add(alert)
                    alerts_created += 1

    await db.commit()
    return {"alerts_created": alerts_created, "portfolio_id": str(portfolio_id)}


async def resolve_alert(
    db: AsyncSession,
    alert_id: uuid.UUID,
    org_id: uuid.UUID,
    action_taken: str,
) -> MonitoringAlert:
    """Mark a monitoring alert as actioned."""
    stmt = select(MonitoringAlert).where(
        MonitoringAlert.id == alert_id,
        MonitoringAlert.org_id == org_id,
    )
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()
    if not alert:
        raise LookupError(f"Alert {alert_id} not found")

    alert.is_read = True
    alert.is_actioned = True
    alert.action_taken = action_taken
    await db.commit()
    await db.refresh(alert)
    return alert


async def generate_domain_mitigation(
    db: AsyncSession,
    portfolio_id: uuid.UUID,
    org_id: uuid.UUID,
    domain: str,
) -> MitigationResponse:
    """Call AI Gateway to generate mitigation strategies for a risk domain."""
    import httpx

    from app.core.config import settings
    from app.modules.risk.service import _get_portfolio_or_raise as _gp

    portfolio = await _gp(db, portfolio_id, org_id)

    prompt = (
        f"You are a risk management expert for alternative investment portfolios.\n\n"
        f"Portfolio: {portfolio.name} | Strategy: {portfolio.strategy.value} | "
        f"AUM: {portfolio.target_aum}\n\n"
        f"Generate specific, actionable risk mitigation strategies for the {domain.upper()} "
        f"risk domain. Focus on practical steps an institutional investor can take.\n\n"
        f"Respond with valid JSON:\n"
        f'{{"mitigation_text": "2-3 sentence summary", '
        f'"key_actions": ["action1", "action2", "action3", "action4", "action5"]}}'
    )

    model_used = "deterministic"
    mitigation_text = f"Implement a comprehensive {domain} risk management framework with regular monitoring and threshold-based alerts."
    key_actions = [
        f"Establish {domain} risk KPIs and monitoring dashboards",
        f"Define and enforce {domain} risk limits per holding",
        f"Conduct quarterly {domain} risk reviews with the investment committee",
        f"Implement hedging strategies appropriate for {domain} exposure",
        f"Engage external {domain} risk specialists for independent validation",
    ]

    if settings.AI_GATEWAY_URL and settings.AI_GATEWAY_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{settings.AI_GATEWAY_URL}/v1/completions",
                    json={
                        "prompt": prompt,
                        "task_type": "analysis",
                        "max_tokens": 512,
                        "temperature": 0.4,
                    },
                    headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
                )
            if resp.status_code == 200:
                content = resp.json().get("content", "")
                import json as _json
                # Strip markdown code blocks if present
                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                parsed = _json.loads(content.strip())
                mitigation_text = parsed.get("mitigation_text", mitigation_text)
                key_actions = parsed.get("key_actions", key_actions)
                model_used = resp.json().get("model_used", "claude")
        except Exception:
            pass  # fall back to deterministic response

    return MitigationResponse(
        domain=domain,
        mitigation_text=mitigation_text,
        key_actions=key_actions,
        model_used=model_used,
    )
