"""Investor Signal Score Engine — multi-source deterministic scoring.

Scores investor readiness across 6 dimensions using real platform data:
portfolios, mandates, risk assessments, personas, org profile, activity.
All logic is pure Python — no LLM, no external calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

DIMENSION_WEIGHTS: dict[str, float] = {
    "financial_capacity": 0.20,
    "risk_management": 0.20,
    "investment_strategy": 0.15,
    "team_experience": 0.15,
    "esg_commitment": 0.15,
    "platform_readiness": 0.15,
}

DIMENSION_ICONS: dict[str, str] = {
    "financial_capacity": "DollarSign",
    "risk_management": "ShieldCheck",
    "investment_strategy": "Target",
    "team_experience": "Users",
    "esg_commitment": "Leaf",
    "platform_readiness": "BarChart3",
}

DIMENSION_DESCRIPTIONS: dict[str, str] = {
    "financial_capacity": "Capital availability, deployment pace, fund lifecycle stage, and follow-on capability",
    "risk_management": "Risk framework sophistication, diversification quality, and compliance processes",
    "investment_strategy": "Strategy clarity, thesis documentation, track record, and mandate specificity",
    "team_experience": "Team size, years of experience, sector expertise, and deal flow quality",
    "esg_commitment": "ESG policy existence, SFDR classification, impact measurement, and UN PRI alignment",
    "platform_readiness": "Profile completeness, document uploads, mandate specification, and engagement level",
}


@dataclass
class CriterionResult:
    name: str
    description: str
    points: int  # points awarded
    max_points: int
    met: bool
    details: str = ""


@dataclass
class DimensionResult:
    score: float
    weight: float
    criteria: list[CriterionResult] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImprovementAction:
    title: str
    description: str
    estimated_impact: float  # points that would be added to overall score
    effort_level: str  # low, medium, high
    category: str  # dimension key
    link_to: str | None  # frontend route


@dataclass
class ScoreFactorItem:
    label: str
    impact: str  # positive | negative
    value: str
    dimension: str


@dataclass
class EngineResult:
    overall_score: float
    dimensions: dict[str, DimensionResult]
    gaps: list[str]
    recommendations: list[str]
    improvement_actions: list[ImprovementAction]
    score_factors: list[ScoreFactorItem]
    data_sources: dict[str, Any]


class InvestorSignalScoreEngine:
    """Calculates investor signal scores from real platform data."""

    def __init__(self, db: AsyncSession, org_id: uuid.UUID) -> None:
        self.db = db
        self.org_id = org_id

    async def calculate(self) -> EngineResult:
        # Load all data sources
        org = await self._get_org()
        portfolios = await self._get_portfolios()
        mandates = await self._get_mandates()
        holdings = await self._get_holdings(portfolios)
        risk_assessments = await self._get_risk_assessments()
        personas = await self._get_personas()
        users = await self._get_users()
        recent_notifications = await self._get_recent_notifications()
        recent_matches = await self._get_recent_matches()

        ctx = {
            "org": org,
            "portfolios": portfolios,
            "mandates": mandates,
            "holdings": holdings,
            "risk_assessments": risk_assessments,
            "personas": personas,
            "users": users,
            "recent_notifications": recent_notifications,
            "recent_matches": recent_matches,
        }

        # Score each dimension
        financial = self._score_financial_capacity(ctx)
        risk_mgmt = self._score_risk_management(ctx)
        strategy = self._score_investment_strategy(ctx)
        team = self._score_team_experience(ctx)
        esg = self._score_esg_commitment(ctx)
        readiness = self._score_platform_readiness(ctx)

        dimensions = {
            "financial_capacity": financial,
            "risk_management": risk_mgmt,
            "investment_strategy": strategy,
            "team_experience": team,
            "esg_commitment": esg,
            "platform_readiness": readiness,
        }

        overall = sum(
            dim.score * DIMENSION_WEIGHTS[key]
            for key, dim in dimensions.items()
        )

        # Aggregate gaps and recs
        all_gaps = [g for d in dimensions.values() for g in d.gaps]
        all_recs = [r for d in dimensions.values() for r in d.recommendations]

        # Build improvement actions from unmet criteria
        actions = self._build_improvement_actions(dimensions)
        factors = self._build_score_factors(dimensions, ctx)

        return EngineResult(
            overall_score=round(overall, 2),
            dimensions=dimensions,
            gaps=all_gaps,
            recommendations=all_recs,
            improvement_actions=sorted(actions, key=lambda a: a.estimated_impact, reverse=True),
            score_factors=factors,
            data_sources={
                "portfolios": len(portfolios),
                "mandates": len(mandates),
                "holdings": len(holdings),
                "risk_assessments": len(risk_assessments),
                "personas": len(personas),
                "users": len(users),
            },
        )

    # ── Dimension scorers ─────────────────────────────────────────────────────

    def _score_financial_capacity(self, ctx: dict) -> DimensionResult:
        portfolios = ctx["portfolios"]
        holdings = ctx["holdings"]
        mandates = ctx["mandates"]
        criteria: list[CriterionResult] = []
        pts = 0

        # AUM documentation (+20)
        has_aum = any(float(p.current_aum) > 0 for p in portfolios)
        c = CriterionResult("AUM Documentation", "Current AUM recorded in portfolio", 20 if has_aum else 0, 20, has_aum)
        criteria.append(c); pts += c.points

        # Fund size evidence (+15)
        has_target = any(float(p.target_aum) > 0 for p in portfolios)
        c = CriterionResult("Fund Size Evidence", "Target AUM / fund size documented", 15 if has_target else 0, 15, has_target)
        criteria.append(c); pts += c.points

        # Deployment history (+15)
        has_holdings = len(holdings) >= 1
        c = CriterionResult("Deployment History", "At least one active portfolio holding", 15 if has_holdings else 0, 15, has_holdings)
        criteria.append(c); pts += c.points

        # Reserve documentation (+10)
        has_reserve = len(portfolios) > 0 and any(
            float(p.target_aum) > float(p.current_aum) * 1.1 for p in portfolios
        )
        c = CriterionResult("Reserve Documentation", "Target AUM exceeds current (reserve capacity visible)", 10 if has_reserve else 0, 10, has_reserve)
        criteria.append(c); pts += c.points

        # Follow-on track record (+10)
        has_followon = len(holdings) >= 3
        c = CriterionResult("Follow-on Track Record", "3+ portfolio holdings (demonstrates follow-on activity)", 10 if has_followon else 0, 10, has_followon)
        criteria.append(c); pts += c.points

        # LP commitment / IRR targets (+15)
        has_irr = any(getattr(m, "target_irr_min", None) is not None for m in mandates)
        c = CriterionResult("Return Targets (LP Commitment)", "Target IRR specified in mandate", 15 if has_irr else 0, 15, has_irr)
        criteria.append(c); pts += c.points

        # Capital call history (+15)
        has_cap_calls = len(holdings) >= 5
        c = CriterionResult("Capital Call History", "5+ holdings indicate active capital deployment", 15 if has_cap_calls else 0, 15, has_cap_calls)
        criteria.append(c); pts += c.points

        return self._build_dim_result("financial_capacity", pts, criteria)

    def _score_risk_management(self, ctx: dict) -> DimensionResult:
        risk_assessments = ctx["risk_assessments"]
        portfolios = ctx["portfolios"]
        holdings = ctx["holdings"]
        criteria: list[CriterionResult] = []
        pts = 0

        # Written risk policy (+20)
        has_risk_policy = len(risk_assessments) >= 1
        c = CriterionResult("Written Risk Policy", "At least one risk assessment created", 20 if has_risk_policy else 0, 20, has_risk_policy)
        criteria.append(c); pts += c.points

        # Insurance portfolio (+15)
        # Proxy: org has an approved/active risk assessment with insurance risk category
        has_insurance = any(
            getattr(r, "output_data", None) and isinstance(r.output_data, dict)
            and "insurance" in str(r.output_data).lower()
            for r in risk_assessments
        )
        c = CriterionResult("Insurance Portfolio", "Insurance coverage documented in risk assessment", 15 if has_insurance else 0, 15, has_insurance)
        criteria.append(c); pts += c.points

        # Hedging documentation (+15)
        has_hedging = len(risk_assessments) >= 2
        c = CriterionResult("Hedging Documentation", "Multiple risk assessments (indicates risk strategy breadth)", 15 if has_hedging else 0, 15, has_hedging)
        criteria.append(c); pts += c.points

        # Portfolio diversification metrics (+15)
        asset_types = {h.asset_type for h in holdings}
        has_diversification = len(asset_types) >= 2
        c = CriterionResult("Portfolio Diversification", "Holdings span 2+ asset types", 15 if has_diversification else 0, 15, has_diversification)
        criteria.append(c); pts += c.points

        # Risk committee existence (+10)
        has_risk_committee = len(risk_assessments) >= 1
        c = CriterionResult("Risk Committee Existence", "Risk assessments suggest governance process", 10 if has_risk_committee else 0, 10, has_risk_committee)
        criteria.append(c); pts += c.points

        # Stress test results (+15)
        has_stress = any(
            getattr(r, "output_data", None) and isinstance(r.output_data, dict)
            and "scenario" in str(r.output_data).lower()
            for r in risk_assessments
        )
        c = CriterionResult("Stress Test Results", "Scenario analysis found in risk assessment output", 15 if has_stress else 0, 15, has_stress)
        criteria.append(c); pts += c.points

        # Compliance framework (+10)
        from app.models.enums import SFDRClassification
        has_compliance = any(
            p.sfdr_classification != SFDRClassification.NOT_APPLICABLE
            for p in portfolios
        )
        c = CriterionResult("Compliance Framework", "SFDR classification applied to portfolio", 10 if has_compliance else 0, 10, has_compliance)
        criteria.append(c); pts += c.points

        return self._build_dim_result("risk_management", pts, criteria)

    def _score_investment_strategy(self, ctx: dict) -> DimensionResult:
        mandates = ctx["mandates"]
        holdings = ctx["holdings"]
        portfolios = ctx["portfolios"]
        criteria: list[CriterionResult] = []
        pts = 0

        active_mandates = [m for m in mandates if getattr(m, "is_active", False)]
        best = active_mandates[0] if active_mandates else (mandates[0] if mandates else None)

        # Written thesis (+20)
        has_thesis = best is not None and len(getattr(best, "name", "") or "") >= 5
        c = CriterionResult("Written Investment Thesis", "Mandate has a descriptive name (thesis proxy)", 20 if has_thesis else 0, 20, has_thesis)
        criteria.append(c); pts += c.points

        # Mandate specification (+15)
        sectors = getattr(best, "sectors", None) or [] if best else []
        stages = getattr(best, "stages", None) or [] if best else []
        has_spec = bool(sectors) and bool(stages)
        c = CriterionResult("Mandate Specification", "Both sectors and stages specified in mandate", 15 if has_spec else 0, 15, has_spec)
        criteria.append(c); pts += c.points

        # Track record documentation (+20)
        from app.models.enums import HoldingStatus
        exited = [h for h in holdings if h.status == HoldingStatus.EXITED]
        has_track = len(exited) >= 1
        c = CriterionResult("Track Record Documentation", "At least one exited investment (proves track record)", 20 if has_track else 0, 20, has_track)
        criteria.append(c); pts += c.points

        # Sector focus clarity (+10)
        has_sector_focus = len(sectors) >= 2
        c = CriterionResult("Sector Focus Clarity", "2+ sectors defined in mandate", 10 if has_sector_focus else 0, 10, has_sector_focus)
        criteria.append(c); pts += c.points

        # Stage preference definition (+10)
        has_stages = len(stages) >= 1
        c = CriterionResult("Stage Preference Definition", "Investment stage preference specified", 10 if has_stages else 0, 10, has_stages)
        criteria.append(c); pts += c.points

        # Co-investment framework (+10)
        geos = getattr(best, "geographies", None) or [] if best else []
        has_geo = len(geos) >= 2
        c = CriterionResult("Geographic Scope (Co-investment Framework)", "2+ geographies defined — signals co-investment readiness", 10 if has_geo else 0, 10, has_geo)
        criteria.append(c); pts += c.points

        # Portfolio construction rules (+15)
        has_construction = len(portfolios) >= 1 and any(
            getattr(p, "strategy", None) is not None for p in portfolios
        )
        c = CriterionResult("Portfolio Construction Rules", "Portfolio strategy type defined", 15 if has_construction else 0, 15, has_construction)
        criteria.append(c); pts += c.points

        return self._build_dim_result("investment_strategy", pts, criteria)

    def _score_team_experience(self, ctx: dict) -> DimensionResult:
        users = ctx["users"]
        mandates = ctx["mandates"]
        holdings = ctx["holdings"]
        criteria: list[CriterionResult] = []
        pts = 0

        # Team bios / members (+15)
        has_team = len(users) >= 2
        c = CriterionResult("Team Members", "2+ users registered in the organisation", 15 if has_team else 0, 15, has_team)
        criteria.append(c); pts += c.points

        # Combined years of experience (+15)
        # Proxy: org has been around (oldest created_at among users) — or just portfolio vintage
        best_mandate = mandates[0] if mandates else None
        has_experience = best_mandate is not None
        c = CriterionResult("Investment Experience Evidence", "Mandate exists — signals prior investment experience", 15 if has_experience else 0, 15, has_experience)
        criteria.append(c); pts += c.points

        # Sector expertise evidence (+15)
        sectors = []
        for m in mandates:
            sectors.extend(getattr(m, "sectors", None) or [])
        has_sector_expertise = len(set(sectors)) >= 3
        c = CriterionResult("Sector Expertise Evidence", "3+ distinct sectors across all mandates", 15 if has_sector_expertise else 0, 15, has_sector_expertise)
        criteria.append(c); pts += c.points

        # Board positions held (+10)
        # Proxy: org has board advisor profiles linked
        has_board = len(holdings) >= 2  # having significant holdings implies board involvement
        c = CriterionResult("Board Position Track Record", "2+ holdings (implies governance participation)", 10 if has_board else 0, 10, has_board)
        criteria.append(c); pts += c.points

        # Deal sourcing track record (+15)
        has_deals = len(holdings) >= 3
        c = CriterionResult("Deal Sourcing Track Record", "3+ portfolio holdings (demonstrates active deal sourcing)", 15 if has_deals else 0, 15, has_deals)
        criteria.append(c); pts += c.points

        # References / testimonials (+10)
        has_references = len(users) >= 3
        c = CriterionResult("Team References", "3+ team members (larger teams typically have testimonials)", 10 if has_references else 0, 10, has_references)
        criteria.append(c); pts += c.points

        # Organizational chart (+10)
        has_org_chart = len(users) >= 4
        c = CriterionResult("Organisational Structure", "4+ users — sufficient team size for structure documentation", 10 if has_org_chart else 0, 10, has_org_chart)
        criteria.append(c); pts += c.points

        # Key person identification (+10)
        from app.models.enums import UserRole
        has_key_person = any(
            getattr(u, "role", None) == UserRole.ADMIN for u in users
        )
        c = CriterionResult("Key Person Identification", "Admin role assigned — identifies key decision maker", 10 if has_key_person else 0, 10, has_key_person)
        criteria.append(c); pts += c.points

        return self._build_dim_result("team_experience", pts, criteria)

    def _score_esg_commitment(self, ctx: dict) -> DimensionResult:
        mandates = ctx["mandates"]
        portfolios = ctx["portfolios"]
        criteria: list[CriterionResult] = []
        pts = 0

        from app.models.enums import SFDRClassification

        best_mandate = next((m for m in mandates if getattr(m, "is_active", False)), mandates[0] if mandates else None)

        # ESG policy document (+20)
        esg_reqs = getattr(best_mandate, "esg_requirements", None) if best_mandate else None
        has_esg_policy = bool(esg_reqs) and (isinstance(esg_reqs, dict) and len(esg_reqs) > 0)
        c = CriterionResult("ESG Policy Document", "ESG requirements defined in mandate", 20 if has_esg_policy else 0, 20, has_esg_policy)
        criteria.append(c); pts += c.points

        # SFDR classification (+15)
        article_portfolios = [
            p for p in portfolios
            if p.sfdr_classification in (
                SFDRClassification.ARTICLE_6,
                SFDRClassification.ARTICLE_8,
                SFDRClassification.ARTICLE_9,
            )
        ]
        has_sfdr = len(article_portfolios) >= 1
        c = CriterionResult("SFDR Classification", "At least one portfolio classified under SFDR Article 6/8/9", 15 if has_sfdr else 0, 15, has_sfdr)
        criteria.append(c); pts += c.points

        # Impact measurement framework (+20)
        has_impact = any(
            getattr(p, "sfdr_classification", None) in (
                SFDRClassification.ARTICLE_8, SFDRClassification.ARTICLE_9
            )
            for p in portfolios
        )
        c = CriterionResult("Impact Measurement Framework", "SFDR Article 8/9 classification implies impact measurement", 20 if has_impact else 0, 20, has_impact)
        criteria.append(c); pts += c.points

        # UN PRI membership (+15)
        esg_str = str(esg_reqs).lower() if esg_reqs else ""
        has_pri = "pri" in esg_str or "un " in esg_str or "principles for responsible" in esg_str
        c = CriterionResult("UN PRI Membership", "PRI / UN Principles referenced in ESG requirements", 15 if has_pri else 0, 15, has_pri)
        criteria.append(c); pts += c.points

        # SDG alignment documentation (+15)
        has_sdg = "sdg" in esg_str or "sustainable development" in esg_str
        c = CriterionResult("SDG Alignment Documentation", "SDG goals referenced in ESG requirements", 15 if has_sdg else 0, 15, has_sdg)
        criteria.append(c); pts += c.points

        # ESG reporting history (+15)
        has_esg_history = any(
            getattr(pm, "esg_metrics", None) for p in portfolios
            for pm in getattr(p, "metrics", []) or []
        )
        # Fallback: if portfolio has exclusions set, indicates ongoing ESG practice
        if not has_esg_history:
            exclusions = getattr(best_mandate, "exclusions", None) if best_mandate else None
            has_esg_history = bool(exclusions) and isinstance(exclusions, dict) and len(exclusions) > 0
        c = CriterionResult("ESG Reporting History", "ESG metrics in portfolio or exclusion criteria set", 15 if has_esg_history else 0, 15, has_esg_history)
        criteria.append(c); pts += c.points

        return self._build_dim_result("esg_commitment", pts, criteria)

    def _score_platform_readiness(self, ctx: dict) -> DimensionResult:
        org = ctx["org"]
        mandates = ctx["mandates"]
        personas = ctx["personas"]
        recent_notifications = ctx["recent_notifications"]
        recent_matches = ctx["recent_matches"]
        criteria: list[CriterionResult] = []
        pts = 0

        # Profile 100% complete (+20)
        has_complete_profile = (
            bool(getattr(org, "name", ""))
            and bool(getattr(org, "logo_url", None))
        )
        c = CriterionResult("Profile Complete", "Organisation has name and logo uploaded", 20 if has_complete_profile else 0, 20, has_complete_profile)
        criteria.append(c); pts += c.points

        # 5+ documents (+15) — proxy: recent notification count (uploads generate notifications)
        has_docs = len(recent_notifications) >= 5
        c = CriterionResult("Documents Uploaded", "5+ platform notifications (proxy for document activity)", 15 if has_docs else 0, 15, has_docs)
        criteria.append(c); pts += c.points

        # Mandate fully specified (+15)
        best = next((m for m in mandates if getattr(m, "is_active", False)), mandates[0] if mandates else None)
        has_full_mandate = (
            best is not None
            and bool(getattr(best, "sectors", None))
            and bool(getattr(best, "geographies", None))
            and bool(getattr(best, "stages", None))
            and float(getattr(best, "ticket_size_min", 0) or 0) > 0
            and float(getattr(best, "ticket_size_max", 0) or 0) > 0
        )
        c = CriterionResult("Mandate Fully Specified", "Active mandate with all required fields populated", 15 if has_full_mandate else 0, 15, has_full_mandate)
        criteria.append(c); pts += c.points

        # 3+ personas created (+10)
        has_personas = len(personas) >= 3
        c = CriterionResult("3+ Investor Personas", "3 or more investor personas created", 10 if has_personas else 0, 10, has_personas)
        criteria.append(c); pts += c.points

        # Weekly platform activity (+15)
        has_activity = len(recent_notifications) >= 1
        c = CriterionResult("Recent Platform Activity", "Platform activity in the last 7 days", 15 if has_activity else 0, 15, has_activity)
        criteria.append(c); pts += c.points

        # Engagement with deals (+15)
        has_engagement = len(recent_matches) >= 1
        c = CriterionResult("Deal Engagement", "Active engagement with matching recommendations", 15 if has_engagement else 0, 15, has_engagement)
        criteria.append(c); pts += c.points

        # Response rate to matches (+10)
        from app.models.enums import MatchStatus
        active_matches = [
            m for m in recent_matches
            if getattr(m, "status", None) in (MatchStatus.INTERESTED, MatchStatus.ENGAGED, MatchStatus.INTRO_REQUESTED)
        ]
        has_responses = len(active_matches) >= 1
        c = CriterionResult("Match Response Rate", "Responded to at least one match (interested/engaged)", 10 if has_responses else 0, 10, has_responses)
        criteria.append(c); pts += c.points

        return self._build_dim_result("platform_readiness", pts, criteria)

    # ── Improvement plan ──────────────────────────────────────────────────────

    def _build_improvement_actions(self, dimensions: dict[str, DimensionResult]) -> list[ImprovementAction]:
        actions: list[ImprovementAction] = []
        LINKS: dict[str, str] = {
            "financial_capacity": "/investor/portfolio",
            "risk_management": "/investor/risk",
            "investment_strategy": "/investor/matching",
            "team_experience": "/settings/team",
            "esg_commitment": "/investor/matching",
            "platform_readiness": "/investor/matching",
        }
        EFFORT: dict[int, str] = {
            10: "low",
            15: "medium",
            20: "high",
        }

        for dim_key, dim in dimensions.items():
            weight = DIMENSION_WEIGHTS[dim_key]
            for crit in dim.criteria:
                if not crit.met:
                    # Estimate overall impact: criterion points / 100 * dimension weight * 100
                    impact = round(crit.max_points / 100 * weight * 100, 1)
                    effort = EFFORT.get(crit.max_points, "medium")
                    actions.append(ImprovementAction(
                        title=crit.name,
                        description=crit.description,
                        estimated_impact=impact,
                        effort_level=effort,
                        category=dim_key,
                        link_to=LINKS.get(dim_key),
                    ))

        return actions

    # ── Score factors ─────────────────────────────────────────────────────────

    def _build_score_factors(
        self, dimensions: dict[str, DimensionResult], ctx: dict
    ) -> list[ScoreFactorItem]:
        factors: list[ScoreFactorItem] = []

        for dim_key, dim in dimensions.items():
            for crit in dim.criteria:
                if crit.met:
                    factors.append(ScoreFactorItem(
                        label=crit.name,
                        impact="positive",
                        value=f"+{crit.points} pts",
                        dimension=dim_key,
                    ))
                elif crit.max_points >= 15:
                    factors.append(ScoreFactorItem(
                        label=crit.name,
                        impact="negative",
                        value=f"−{crit.max_points} pts",
                        dimension=dim_key,
                    ))

        return factors

    # ── Deal alignment ────────────────────────────────────────────────────────

    async def calculate_deal_alignment(self, project_id: uuid.UUID) -> dict[str, Any]:
        """
        Calculate alignment between investor and a specific project.
        Returns 0-100 alignment score with per-factor breakdown.
        """
        from app.models.projects import Project, SignalScore as ProjectSignalScore

        mandates = await self._get_mandates()
        project_stmt = select(Project).where(
            Project.id == project_id,
            Project.is_deleted.is_(False),
        )
        project_result = await self.db.execute(project_stmt)
        project = project_result.scalar_one_or_none()
        if project is None:
            raise LookupError(f"Project {project_id} not found")

        # Load project signal score
        ss_stmt = (
            select(ProjectSignalScore)
            .where(ProjectSignalScore.project_id == project_id)
            .order_by(ProjectSignalScore.calculated_at.desc())
            .limit(1)
        )
        ss_result = await self.db.execute(ss_stmt)
        project_ss = ss_result.scalar_one_or_none()

        # Find best matching mandate
        best_mandate = next(
            (m for m in mandates if getattr(m, "is_active", False)),
            mandates[0] if mandates else None,
        )

        factors: dict[str, float] = {}

        # 1. Asset type match
        project_type = getattr(project, "project_type", None)
        mandate_sectors = getattr(best_mandate, "sectors", None) or [] if best_mandate else []
        asset_match = 100.0 if (project_type and project_type.value in mandate_sectors) else 40.0
        factors["asset_type_match"] = asset_match

        # 2. Geography match
        project_country = getattr(project, "geography_country", "") or ""
        mandate_geos = getattr(best_mandate, "geographies", None) or [] if best_mandate else []
        geo_match = 100.0 if any(
            g.lower() in project_country.lower() or project_country.lower() in g.lower()
            for g in mandate_geos
        ) else 40.0
        factors["geography_match"] = geo_match

        # 3. Ticket size match
        project_investment = float(getattr(project, "total_investment_required", 0) or 0)
        tick_min = float(getattr(best_mandate, "ticket_size_min", 0) or 0) if best_mandate else 0
        tick_max = float(getattr(best_mandate, "ticket_size_max", float("inf")) or float("inf")) if best_mandate else float("inf")
        if tick_min <= project_investment <= tick_max:
            ticket_match = 100.0
        elif project_investment < tick_min:
            ratio = project_investment / tick_min if tick_min > 0 else 0
            ticket_match = max(20.0, 100.0 * ratio)
        else:
            ratio = tick_max / project_investment if project_investment > 0 else 0
            ticket_match = max(20.0, 100.0 * ratio)
        factors["ticket_size_match"] = round(ticket_match, 1)

        # 4. Risk tolerance match
        project_viability = 50.0
        if project_ss and project_ss.scoring_details:
            dims = project_ss.scoring_details.get("dimensions", {})
            project_viability = float(dims.get("risk_assessment", {}).get("score", 50))
        from app.models.enums import RiskTolerance
        mandate_risk = getattr(best_mandate, "risk_tolerance", RiskTolerance.MODERATE) if best_mandate else RiskTolerance.MODERATE
        risk_score_map = {RiskTolerance.CONSERVATIVE: 30, RiskTolerance.MODERATE: 60, RiskTolerance.AGGRESSIVE: 90}
        investor_risk_score = risk_score_map.get(mandate_risk, 60)
        risk_gap = abs(investor_risk_score - project_viability)
        risk_match = max(20.0, 100.0 - risk_gap)
        factors["risk_tolerance_match"] = round(risk_match, 1)

        # 5. ESG alignment
        esg_reqs = getattr(best_mandate, "esg_requirements", None) if best_mandate else None
        has_esg_mandate = bool(esg_reqs) and isinstance(esg_reqs, dict) and len(esg_reqs) > 0
        project_esg_score = 50.0
        if project_ss and project_ss.scoring_details:
            dims = project_ss.scoring_details.get("dimensions", {})
            project_esg_score = float(dims.get("esg", {}).get("score", 50))
        esg_match = (project_esg_score * 0.6 + (80 if has_esg_mandate else 40) * 0.4)
        factors["esg_alignment"] = round(esg_match, 1)

        # 6. IRR target match
        mandate_irr = float(getattr(best_mandate, "target_irr_min", 0) or 0) if best_mandate else 0
        project_irr = float(getattr(project, "target_irr_min", mandate_irr) or mandate_irr)
        if mandate_irr > 0:
            irr_ratio = min(project_irr / mandate_irr, mandate_irr / project_irr) if project_irr > 0 else 0.4
            irr_match = max(20.0, min(100.0, irr_ratio * 100))
        else:
            irr_match = 70.0  # no IRR target set — neutral
        factors["irr_target_match"] = round(irr_match, 1)

        overall = sum(factors.values()) / len(factors)

        if overall >= 80:
            recommendation = "strong_fit"
        elif overall >= 65:
            recommendation = "good_fit"
        elif overall >= 45:
            recommendation = "marginal_fit"
        else:
            recommendation = "poor_fit"

        return {
            "project_id": str(project_id),
            "project_name": getattr(project, "name", ""),
            "alignment_score": round(overall),
            "factors": [
                {
                    "name": k,
                    "label": k.replace("_", " ").title(),
                    "score": round(v),
                }
                for k, v in factors.items()
            ],
            "recommendation": recommendation,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_dim_result(
        self,
        dim_key: str,
        total_pts: int,
        criteria: list[CriterionResult],
    ) -> DimensionResult:
        score = min(100.0, float(total_pts))
        gaps = [c.description for c in criteria if not c.met and c.max_points >= 10]
        recs = []
        for c in criteria:
            if not c.met:
                recs.append(f"Add {c.name.lower()} to gain up to {c.max_points} points")

        return DimensionResult(
            score=score,
            weight=DIMENSION_WEIGHTS[dim_key],
            criteria=criteria,
            gaps=gaps,
            recommendations=recs,
            details={
                "criteria_met": sum(1 for c in criteria if c.met),
                "criteria_total": len(criteria),
                "points_earned": total_pts,
                "points_max": sum(c.max_points for c in criteria),
                "icon": DIMENSION_ICONS[dim_key],
                "description": DIMENSION_DESCRIPTIONS[dim_key],
            },
        )

    # ── Data loaders ──────────────────────────────────────────────────────────

    async def _get_org(self):
        from app.models.core import Organization
        result = await self.db.execute(
            select(Organization).where(Organization.id == self.org_id)
        )
        return result.scalar_one_or_none()

    async def _get_portfolios(self):
        from app.models.investors import Portfolio
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(
            select(Portfolio)
            .where(Portfolio.org_id == self.org_id, Portfolio.is_deleted.is_(False))
            .options(selectinload(Portfolio.metrics))
        )
        return list(result.scalars().all())

    async def _get_mandates(self):
        from app.models.investors import InvestorMandate
        result = await self.db.execute(
            select(InvestorMandate)
            .where(InvestorMandate.org_id == self.org_id, InvestorMandate.is_deleted.is_(False))
            .order_by(InvestorMandate.updated_at.desc())
        )
        return list(result.scalars().all())

    async def _get_holdings(self, portfolios):
        if not portfolios:
            return []
        from app.models.investors import PortfolioHolding
        portfolio_ids = [p.id for p in portfolios]
        from sqlalchemy import and_
        result = await self.db.execute(
            select(PortfolioHolding)
            .where(
                PortfolioHolding.portfolio_id.in_(portfolio_ids),
                PortfolioHolding.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def _get_risk_assessments(self):
        from app.models.investors import RiskAssessment
        result = await self.db.execute(
            select(RiskAssessment)
            .where(RiskAssessment.org_id == self.org_id, RiskAssessment.is_deleted.is_(False))
            .limit(20)
        )
        return list(result.scalars().all())

    async def _get_personas(self):
        from app.models.advisory import InvestorPersona
        result = await self.db.execute(
            select(InvestorPersona)
            .where(InvestorPersona.org_id == self.org_id, InvestorPersona.is_deleted.is_(False))
        )
        return list(result.scalars().all())

    async def _get_users(self):
        from app.models.core import User
        result = await self.db.execute(
            select(User)
            .where(
                User.org_id == self.org_id,
                User.is_active.is_(True),
                User.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def _get_recent_notifications(self):
        from app.models.core import Notification
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        result = await self.db.execute(
            select(Notification)
            .where(
                Notification.org_id == self.org_id,
                Notification.created_at >= cutoff,
            )
            .limit(50)
        )
        return list(result.scalars().all())

    async def _get_recent_matches(self):
        from app.models.matching import MatchResult
        result = await self.db.execute(
            select(MatchResult)
            .where(
                MatchResult.investor_org_id == self.org_id,
                MatchResult.is_deleted.is_(False),
            )
            .limit(30)
        )
        return list(result.scalars().all())
