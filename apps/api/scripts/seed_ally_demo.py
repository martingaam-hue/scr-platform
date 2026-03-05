#!/usr/bin/env python3
"""Demo seed script for the ALLY (developer) side of SCR Platform.

Creates org "Greenfield Development Partners" (OrgType.ALLY) with 3 complete
projects and all associated ally-side data:
  - Helios Solar Portfolio Iberia (Operational, Solar PV, Spain)
  - Nordvik Wind Farm II (Construction, Onshore Wind, Norway)
  - Adriatic Infrastructure Holdings (Operational, Core Infra, Croatia/Slovenia)

Each project gets: milestones, budget items, risks, KPIs, ESG metrics,
documents, legal documents, investor readiness certification, and matching
records linked to the PAMP Infrastructure Partners (investor) org.

Usage (from apps/api directory):
    poetry run python scripts/seed_ally_demo.py
    poetry run python scripts/seed_ally_demo.py --dry-run
    poetry run python scripts/seed_ally_demo.py --wipe

Idempotent — safe to run multiple times.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

_api_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _api_root not in sys.path:
    sys.path.insert(0, _api_root)

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base
from app.models.certification import InvestorReadinessCertification
from app.models.core import Organization, User
from app.models.dataroom import Document
from app.models.enums import (
    BudgetItemStatus,
    DocumentStatus,
    LegalDocumentStatus,
    LegalDocumentType,
    MatchInitiator,
    MatchStatus,
    MilestoneStatus,
    OrgType,
    ProjectStage,
    ProjectStatus,
    ProjectType,
    RiskAssessmentStatus,
    RiskEntityType,
    RiskProbability,
    RiskSeverity,
    RiskType,
    SubscriptionStatus,
    SubscriptionTier,
    UserRole,
)
from app.models.esg import ESGMetrics
from app.models.investors import RiskAssessment
from app.models.legal import LegalDocument
from app.models.matching import MatchResult
from app.models.monitoring import Covenant, KPIActual, KPITarget
from app.models.projects import Project, ProjectBudgetItem, ProjectMilestone, SignalScore

# ── Constants ──────────────────────────────────────────────────────────────

ALLY_ORG_SLUG = "greenfield-dev-partners"
ALLY_USER_EMAIL = "demo@greenfield-dev.com"
INVESTOR_ORG_SLUG = "pamp-infra-partners"
REPORTING_DATE = date(2026, 3, 1)


def get_engine():
    sync_url = settings.DATABASE_URL_SYNC
    if "localhost" in sync_url or "127.0.0.1" in sync_url:
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    return create_engine(sync_url, echo=False)


def _uid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(UTC)


# ── Org & User ─────────────────────────────────────────────────────────────


def ensure_org_user(session: Session, dry_run: bool) -> tuple[uuid.UUID, uuid.UUID]:
    org = session.execute(
        select(Organization).where(Organization.slug == ALLY_ORG_SLUG)
    ).scalar_one_or_none()

    if org:
        org_id = org.id
        print(f"  [ok] Org: {org.name} ({org_id})")
    else:
        org_id = _uid()
        if not dry_run:
            o = Organization(
                id=org_id,
                name="Greenfield Development Partners",
                slug=ALLY_ORG_SLUG,
                type=OrgType.ALLY,
                subscription_tier=SubscriptionTier.PRO,
                subscription_status=SubscriptionStatus.ACTIVE,
                settings={
                    "base_currency": "EUR",
                    "reporting_date": "2026-03-01",
                    "sectors": ["solar", "wind", "infrastructure"],
                    "primary_geography": "Southern & Northern Europe",
                    "development_focus": "greenfield + late-stage development",
                },
            )
            session.add(o)
            session.flush()
        print(f"  [+] Created ally org ({org_id})")

    user = session.execute(select(User).where(User.email == ALLY_USER_EMAIL)).scalar_one_or_none()

    if user:
        user_id = user.id
        print(f"  [ok] User: {user.full_name} ({user_id})")
    else:
        user_id = _uid()
        if not dry_run:
            u = User(
                id=user_id,
                org_id=org_id,
                email=ALLY_USER_EMAIL,
                full_name="Alex Greenfield",
                role=UserRole.ADMIN,
                external_auth_id=f"ally_{user_id}",
                is_active=True,
                preferences={
                    "onboarding_completed": True,
                    "tour_completed": True,
                    "org_type": "ally",
                },
            )
            session.add(u)
            session.flush()
        print(f"  [+] Created user {ALLY_USER_EMAIL} ({user_id})")

    return org_id, user_id


# ── Projects ───────────────────────────────────────────────────────────────

PROJECTS = [
    {
        "slug": "helios-solar-portfolio-iberia",
        "name": "Helios Solar Portfolio Iberia",
        "description": (
            "420 MWp ground-mounted solar PV portfolio across 6 plants in Andalucía, "
            "Extremadura and Castilla-La Mancha. Bi-facial mono-PERC with single-axis trackers. "
            "COD Q2 2024. Contracted cash-flow with merchant upside in Iberian power market."
        ),
        "project_type": ProjectType.SOLAR,
        "status": ProjectStatus.ACTIVE,
        "stage": ProjectStage.OPERATIONAL,
        "geography_country": "Spain",
        "geography_region": "Andalucía / Extremadura / Castilla-La Mancha",
        "geography_coordinates": {"lat": 37.8, "lng": -4.8},
        "capacity_mw": Decimal("420.0"),
        "total_investment_required": Decimal("312000000"),
        "currency": "EUR",
        "technology_details": {
            "technology": "Bi-facial mono-PERC + single-axis trackers",
            "asset_life_years": 35,
            "cod": "2024-Q2",
            "sponsor": "Greenfield Development Partners",
            "spv": "Helios Solar HoldCo S.à r.l. (Luxembourg)",
            "annual_p50_yield_gwh": 768.5,
            "contracted_pct": 56.0,
            "financial_model": {
                "total_investment_eur_m": 312.0,
                "senior_debt_eur_m": 218.4,
                "equity_eur_m": 93.6,
                "project_irr_pct": 9.8,
                "equity_irr_pct": 13.2,
            },
        },
    },
    {
        "slug": "nordvik-wind-farm-ii",
        "name": "Nordvik Wind Farm II",
        "description": (
            "210 MW onshore wind farm (35 × Vestas V162-6.0 MW) in Trøndelag, Norway. "
            "85% construction complete, COD targeted Q4 2026. "
            "Nordpool exposure with ElCert upside; strong wind regime NCF >38%."
        ),
        "project_type": ProjectType.WIND,
        "status": ProjectStatus.ACTIVE,
        "stage": ProjectStage.UNDER_CONSTRUCTION,
        "geography_country": "Norway",
        "geography_region": "Trøndelag county",
        "geography_coordinates": {"lat": 63.5, "lng": 11.2},
        "capacity_mw": Decimal("210.0"),
        "total_investment_required": Decimal("410000000"),
        "currency": "EUR",
        "technology_details": {
            "technology": "Vestas V162-6.0 MW, 166m hub height",
            "turbine_count": 35,
            "ncf_p50_pct": 38.5,
            "aep_p50_gwh": 708,
            "cod_target": "2026-Q4",
            "construction_progress_pct": 85,
            "financial_model": {
                "total_investment_eur_m": 410.0,
                "senior_debt_eur_m": 287.0,
                "equity_eur_m": 123.0,
                "project_irr_pct": 10.1,
                "equity_irr_pct": 14.7,
            },
        },
    },
    {
        "slug": "adriatic-infrastructure-holdings",
        "name": "Adriatic Infrastructure Holdings",
        "description": (
            "Core infrastructure portfolio comprising motorway PPP (A1-ext, 87 km), "
            "municipal water utility (Zadar region, 340k connections), "
            "and district heating network (Ljubljana South, 42 MW). "
            "Diversified cash-flow, 85% regulated/contracted."
        ),
        "project_type": ProjectType.INFRASTRUCTURE,
        "status": ProjectStatus.ACTIVE,
        "stage": ProjectStage.OPERATIONAL,
        "geography_country": "Croatia",
        "geography_region": "Adriatic Coast / Slovenia",
        "geography_coordinates": {"lat": 44.1, "lng": 15.2},
        "capacity_mw": None,
        "total_investment_required": Decimal("485000000"),
        "currency": "EUR",
        "technology_details": {
            "assets": [
                "Motorway PPP A1-ext (87 km)",
                "Zadar Water Utility",
                "Ljubljana District Heating",
            ],
            "regulated_pct": 85,
            "avg_concession_years_remaining": 18,
            "financial_model": {
                "total_investment_eur_m": 485.0,
                "senior_debt_eur_m": 339.5,
                "equity_eur_m": 145.5,
                "project_irr_pct": 8.9,
                "equity_irr_pct": 12.4,
            },
        },
    },
]


def ensure_projects(
    session: Session, org_id: uuid.UUID, user_id: uuid.UUID, dry_run: bool
) -> dict[str, uuid.UUID]:
    """Return {slug: project_id}."""
    project_ids: dict[str, uuid.UUID] = {}

    for p_data in PROJECTS:
        existing = session.execute(
            select(Project).where(
                Project.org_id == org_id,
                Project.slug == p_data["slug"],
                Project.is_deleted == False,  # noqa: E712
            )
        ).scalar_one_or_none()

        if existing:
            project_ids[p_data["slug"]] = existing.id
            print(f"  [ok] Project: {existing.name} ({existing.id})")
            continue

        pid = _uid()
        if not dry_run:
            proj = Project(
                id=pid,
                org_id=org_id,
                name=p_data["name"],
                slug=p_data["slug"],
                description=p_data["description"],
                project_type=p_data["project_type"],
                status=p_data["status"],
                stage=p_data["stage"],
                geography_country=p_data["geography_country"],
                geography_region=p_data.get("geography_region"),
                geography_coordinates=p_data.get("geography_coordinates"),
                capacity_mw=p_data.get("capacity_mw"),
                total_investment_required=p_data["total_investment_required"],
                currency=p_data["currency"],
                technology_details=p_data.get("technology_details"),
                created_by=user_id,
            )
            session.add(proj)
            session.flush()
        project_ids[p_data["slug"]] = pid
        print(f"  [+] Created project: {p_data['name']} ({pid})")

    return project_ids


# ── Signal Scores ──────────────────────────────────────────────────────────

SIGNAL_SCORES = {
    "helios-solar-portfolio-iberia": {
        "overall_score": 88,
        "project_viability_score": 91,
        "financial_planning_score": 89,
        "risk_assessment_score": 84,
        "team_strength_score": 87,
        "esg_score": 92,
        "ai_summary": (
            "Helios Solar demonstrates strong investor readiness across all dimensions. "
            "Operational cash generation is above P50 forecasts, contracted revenue at 56% "
            "provides downside protection, and ESG credentials are market-leading. "
            "Minor concerns around merchant price volatility and Spanish curtailment risk."
        ),
        "dimension_details": {
            "viability": {
                "comment": "6 fully operational plants, P50 yield tracking +2.3% above forecast"
            },
            "financial": {"comment": "DSCR 1.42x Q1 2026 vs 1.15x covenant; fully funded"},
            "risk": {"comment": "Curtailment risk in Andalucía; grid upgrade scheduled H2 2026"},
            "team": {"comment": "Experienced Iberian solar developer, 3GW+ track record"},
            "esg": {
                "comment": "GRESB Green Star, SFDR Art. 9 eligible, 595k tCO₂e avoided annually"
            },
        },
    },
    "nordvik-wind-farm-ii": {
        "overall_score": 79,
        "project_viability_score": 76,
        "financial_planning_score": 81,
        "risk_assessment_score": 74,
        "team_strength_score": 82,
        "esg_score": 85,
        "ai_summary": (
            "Nordvik Wind II has strong fundamentals but elevated construction risk with 15% "
            "of works outstanding. Commissioning timeline risk is the primary concern — "
            "a Q1 2027 slip would reduce IRR by ~80bps. ElCert regime provides meaningful "
            "revenue uplift beyond Nordpool spot."
        ),
        "dimension_details": {
            "viability": {"comment": "85% construction complete; foundation & tower erection done"},
            "financial": {
                "comment": "€287M senior debt fully drawn; contingency reserve €22M intact"
            },
            "risk": {"comment": "Blade installation phase; weather window risk Nov–Mar"},
            "team": {"comment": "Vestas EPC with Nordic wind O&M track record"},
            "esg": {
                "comment": "Biodiversity Management Plan approved; reindeer migration corridors preserved"
            },
        },
    },
    "adriatic-infrastructure-holdings": {
        "overall_score": 83,
        "project_viability_score": 86,
        "financial_planning_score": 82,
        "risk_assessment_score": 81,
        "team_strength_score": 79,
        "esg_score": 84,
        "ai_summary": (
            "Adriatic Infrastructure offers diversified, regulated cash flows with low single-asset "
            "concentration risk. Motorway PPP revenue tracked 1.8% above forecast YTD; water utility "
            "EBITDA margin at 38.2%. Regulatory risk in Croatian water tariff review (2027) is the "
            "key watch item."
        ),
        "dimension_details": {
            "viability": {"comment": "3 assets, 85% regulated; average concession 18yr remaining"},
            "financial": {"comment": "Consolidated DSCR 1.38x; LTV 70% at acquisition"},
            "risk": {
                "comment": "Croatian water tariff review H1 2027 — potential 5-8% tariff adjustment"
            },
            "team": {"comment": "O&M partnerships with Autocesta HRV and Veolia Water"},
            "esg": {
                "comment": "ISO 14001 certified across all assets; district heating displaces 12k tCO₂e/yr"
            },
        },
    },
}


def ensure_signal_scores(
    session: Session, org_id: uuid.UUID, project_ids: dict[str, uuid.UUID], dry_run: bool
) -> None:
    for slug, data in SIGNAL_SCORES.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        existing = session.execute(
            select(SignalScore).where(
                SignalScore.project_id == pid,
                SignalScore.org_id == org_id,
            )
        ).scalar_one_or_none()

        if existing:
            print(f"  [ok] SignalScore for {slug}")
            continue

        if not dry_run:
            ss = SignalScore(
                id=_uid(),
                project_id=pid,
                org_id=org_id,
                overall_score=data["overall_score"],
                project_viability_score=data["project_viability_score"],
                financial_planning_score=data["financial_planning_score"],
                risk_assessment_score=data["risk_assessment_score"],
                team_strength_score=data["team_strength_score"],
                esg_score=data["esg_score"],
                ai_summary=data["ai_summary"],
                dimension_details=data["dimension_details"],
                status="completed",
            )
            session.add(ss)
        print(f"  [+] SignalScore for {slug} ({data['overall_score']})")


# ── Milestones ──────────────────────────────────────────────────────────────

MILESTONES: dict[str, list[dict]] = {
    "helios-solar-portfolio-iberia": [
        {
            "title": "Environmental Impact Assessment approved",
            "due_date": date(2022, 6, 1),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "Full EIA approval from MITECO for all 6 sites",
        },
        {
            "title": "Grid connection agreements signed",
            "due_date": date(2022, 11, 1),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "REE access and connection permits secured",
        },
        {
            "title": "Senior debt financial close",
            "due_date": date(2023, 8, 30),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "€218.4M TLB signed with BBVA / Santander / ING syndicate",
        },
        {
            "title": "EPC completion — Helios Almería I & II",
            "due_date": date(2024, 3, 22),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "Commercial operation declaration for 155 MWp Almería cluster",
        },
        {
            "title": "EPC completion — Helios Badajoz",
            "due_date": date(2024, 4, 15),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "Largest single site at 100 MWp, first power exported",
        },
        {
            "title": "Portfolio full commercial operation (COD)",
            "due_date": date(2024, 6, 30),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "All 6 plants commercially operational — 420 MWp portfolio live",
        },
        {
            "title": "First PPA settlement — Iberdrola",
            "due_date": date(2024, 8, 1),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "CfD PPA settlement invoice cleared; revenue tracking confirmed",
        },
        {
            "title": "DSCR covenant test — Year 1",
            "due_date": date(2025, 6, 30),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "DSCR 1.42x vs 1.15x covenant; passed with 23% headroom",
        },
        {
            "title": "Grid upgrade — Almería cluster",
            "due_date": date(2026, 9, 30),
            "status": MilestoneStatus.IN_PROGRESS,
            "completion_pct": 35,
            "description": "REE-led 220 kV upgrade to reduce curtailment from 4.2% to <1.5%",
        },
        {
            "title": "DSCR covenant test — Year 2",
            "due_date": date(2026, 6, 30),
            "status": MilestoneStatus.IN_PROGRESS,
            "completion_pct": 70,
            "description": "Forecast DSCR 1.39x; financial model refresh in progress",
        },
    ],
    "nordvik-wind-farm-ii": [
        {
            "title": "Norwegian NVE permit granted",
            "due_date": date(2022, 9, 15),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "Full wind power license from NVE, 25yr term",
        },
        {
            "title": "EPC contract signed — Vestas / Implenia",
            "due_date": date(2023, 3, 31),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "Lump-sum EPC with Vestas turbine supply and Implenia civil works",
        },
        {
            "title": "Financial close — DNB / Nordea syndicate",
            "due_date": date(2023, 7, 28),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "€287M senior facility; first drawdown August 2023",
        },
        {
            "title": "Site clearance and access roads complete",
            "due_date": date(2023, 10, 31),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "35 turbine pads graded; 18 km internal road network commissioned",
        },
        {
            "title": "Foundation pouring — all 35 turbines",
            "due_date": date(2024, 6, 30),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "Gravity-based foundations complete; curing period satisfied",
        },
        {
            "title": "Tower erection — 35 turbines",
            "due_date": date(2024, 12, 31),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "All 35 tower sections assembled; nacelles installation underway",
        },
        {
            "title": "Nacelle & blade installation",
            "due_date": date(2025, 8, 31),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "All 35 nacelles and 105 blades installed; commissioning commenced",
        },
        {
            "title": "Grid connection commissioning",
            "due_date": date(2026, 6, 30),
            "status": MilestoneStatus.IN_PROGRESS,
            "completion_pct": 60,
            "description": "Statnett 132 kV substation works; energization Q2 2026",
        },
        {
            "title": "Commercial operation date (COD)",
            "due_date": date(2026, 10, 31),
            "status": MilestoneStatus.PENDING,
            "completion_pct": 0,
            "description": "Full 210 MW commercial operation; ElCert registration pending COD",
        },
        {
            "title": "O&M long-term service agreement start",
            "due_date": date(2026, 11, 1),
            "status": MilestoneStatus.PENDING,
            "completion_pct": 0,
            "description": "Vestas 20yr LTSA activation post-COD",
        },
    ],
    "adriatic-infrastructure-holdings": [
        {
            "title": "Motorway PPP concession acquired — A1-ext",
            "due_date": date(2021, 4, 30),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "87 km A1 extension concession assignment from Croatian HAC",
        },
        {
            "title": "Zadar Water Utility acquisition closed",
            "due_date": date(2022, 1, 31),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "51% stake in Vodovod Zadar acquired from Zadar County",
        },
        {
            "title": "Ljubljana District Heating acquisition",
            "due_date": date(2022, 9, 30),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "42 MW district heating network in Ljubljana South acquired from municipality",
        },
        {
            "title": "Refinancing — consolidated senior facility",
            "due_date": date(2023, 5, 31),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "€339.5M consolidated TLA across 3 assets; 12yr tenor, EURIBOR +195bps",
        },
        {
            "title": "ISO 14001 certification — all assets",
            "due_date": date(2024, 3, 31),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "Environmental management certification by Bureau Veritas",
        },
        {
            "title": "Water tariff periodic review — Croatia",
            "due_date": date(2025, 1, 31),
            "status": MilestoneStatus.COMPLETED,
            "completion_pct": 100,
            "description": "HRT regulator approved +4.2% tariff increase (in-line with CPI formula)",
        },
        {
            "title": "Motorway traffic growth milestone (5yr target)",
            "due_date": date(2026, 4, 30),
            "status": MilestoneStatus.IN_PROGRESS,
            "completion_pct": 80,
            "description": "ADT tracking at 8,340 vs 8,500 target; YTD growth 3.1%",
        },
        {
            "title": "Croatian water tariff review — next cycle",
            "due_date": date(2027, 6, 30),
            "status": MilestoneStatus.PENDING,
            "completion_pct": 0,
            "description": "HRT regulatory review; modelling 3-year tariff determination",
        },
        {
            "title": "Ljubljana DH network expansion — Phase II",
            "due_date": date(2027, 12, 31),
            "status": MilestoneStatus.PENDING,
            "completion_pct": 0,
            "description": "+18 MW biomass boiler; grant application submitted to Slovenia MEDT",
        },
    ],
}


def ensure_milestones(
    session: Session,
    org_id: uuid.UUID,
    project_ids: dict[str, uuid.UUID],
    user_id: uuid.UUID,
    dry_run: bool,
) -> None:
    for slug, milestones in MILESTONES.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        count = 0
        for m in milestones:
            existing = session.execute(
                select(ProjectMilestone).where(
                    ProjectMilestone.project_id == pid,
                    ProjectMilestone.title == m["title"],
                )
            ).scalar_one_or_none()
            if existing:
                continue
            if not dry_run:
                session.add(
                    ProjectMilestone(
                        id=_uid(),
                        project_id=pid,
                        org_id=org_id,
                        title=m["title"],
                        description=m.get("description", ""),
                        due_date=m["due_date"],
                        status=m["status"],
                        completion_percentage=m["completion_pct"],
                        created_by=user_id,
                    )
                )
            count += 1
        print(f"  [+] {count} milestone(s) for {slug}")


# ── Budget Items ───────────────────────────────────────────────────────────

BUDGET_ITEMS: dict[str, list[dict]] = {
    "helios-solar-portfolio-iberia": [
        {
            "category": "EPC - Panels & racking",
            "budget": Decimal("142000000"),
            "actual": Decimal("139800000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "EPC - Balance of plant",
            "budget": Decimal("68000000"),
            "actual": Decimal("67200000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Grid connection & substation",
            "budget": Decimal("24000000"),
            "actual": Decimal("24850000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Land lease (35yr prepaid)",
            "budget": Decimal("18500000"),
            "actual": Decimal("18500000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Development & permitting",
            "budget": Decimal("8200000"),
            "actual": Decimal("7900000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Owner's engineer & insurance",
            "budget": Decimal("5800000"),
            "actual": Decimal("5950000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Financing fees & interest during construction",
            "budget": Decimal("12500000"),
            "actual": Decimal("11900000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Contingency reserve",
            "budget": Decimal("15000000"),
            "actual": Decimal("4400000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "O&M reserves (first 2yr)",
            "budget": Decimal("9000000"),
            "actual": Decimal("9000000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Grid upgrade — Almería cluster",
            "budget": Decimal("9000000"),
            "actual": Decimal("3200000"),
            "status": BudgetItemStatus.IN_PROGRESS,
        },
    ],
    "nordvik-wind-farm-ii": [
        {
            "category": "Turbine supply — 35 × Vestas V162",
            "budget": Decimal("196000000"),
            "actual": Decimal("196000000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Civil works — foundations & roads",
            "budget": Decimal("48000000"),
            "actual": Decimal("47100000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Electrical installation & substation",
            "budget": Decimal("32000000"),
            "actual": Decimal("29800000"),
            "status": BudgetItemStatus.IN_PROGRESS,
        },
        {
            "category": "Grid connection — Statnett 132 kV",
            "budget": Decimal("28000000"),
            "actual": Decimal("14200000"),
            "status": BudgetItemStatus.IN_PROGRESS,
        },
        {
            "category": "Development, permitting & environmental",
            "budget": Decimal("12000000"),
            "actual": Decimal("12000000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Owner's engineer & insurance during construction",
            "budget": Decimal("8500000"),
            "actual": Decimal("7100000"),
            "status": BudgetItemStatus.IN_PROGRESS,
        },
        {
            "category": "Financing fees & interest during construction",
            "budget": Decimal("18000000"),
            "actual": Decimal("15200000"),
            "status": BudgetItemStatus.IN_PROGRESS,
        },
        {
            "category": "Contingency reserve",
            "budget": Decimal("25000000"),
            "actual": Decimal("3400000"),
            "status": BudgetItemStatus.IN_PROGRESS,
        },
        {
            "category": "Commissioning & testing",
            "budget": Decimal("6500000"),
            "actual": Decimal("0"),
            "status": BudgetItemStatus.PENDING,
        },
        {
            "category": "O&M mobilisation (Year 1)",
            "budget": Decimal("3600000"),
            "actual": Decimal("0"),
            "status": BudgetItemStatus.PENDING,
        },
        {
            "category": "Blade installation campaign",
            "budget": Decimal("9400000"),
            "actual": Decimal("9400000"),
            "status": BudgetItemStatus.COMPLETED,
        },
    ],
    "adriatic-infrastructure-holdings": [
        {
            "category": "Motorway PPP A1-ext — acquisition price",
            "budget": Decimal("168000000"),
            "actual": Decimal("168000000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Zadar Water Utility — equity acquisition (51%)",
            "budget": Decimal("84500000"),
            "actual": Decimal("84500000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Ljubljana DH — acquisition price",
            "budget": Decimal("72000000"),
            "actual": Decimal("72000000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Capex — motorway pavement overlay (Year 3-4)",
            "budget": Decimal("22000000"),
            "actual": Decimal("18700000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Capex — water pipe rehabilitation (ongoing)",
            "budget": Decimal("18000000"),
            "actual": Decimal("12400000"),
            "status": BudgetItemStatus.IN_PROGRESS,
        },
        {
            "category": "Ljubljana DH Phase II — biomass boiler",
            "budget": Decimal("14000000"),
            "actual": Decimal("0"),
            "status": BudgetItemStatus.PENDING,
        },
        {
            "category": "Refinancing fees & hedging",
            "budget": Decimal("8200000"),
            "actual": Decimal("8200000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "Working capital & reserves",
            "budget": Decimal("12300000"),
            "actual": Decimal("12300000"),
            "status": BudgetItemStatus.COMPLETED,
        },
        {
            "category": "ESG & certification programmes",
            "budget": Decimal("1800000"),
            "actual": Decimal("1600000"),
            "status": BudgetItemStatus.IN_PROGRESS,
        },
        {
            "category": "Contingency reserve",
            "budget": Decimal("18200000"),
            "actual": Decimal("4800000"),
            "status": BudgetItemStatus.IN_PROGRESS,
        },
    ],
}


def ensure_budget_items(
    session: Session,
    org_id: uuid.UUID,
    project_ids: dict[str, uuid.UUID],
    user_id: uuid.UUID,
    dry_run: bool,
) -> None:
    for slug, items in BUDGET_ITEMS.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        existing_count = (
            session.execute(select(ProjectBudgetItem).where(ProjectBudgetItem.project_id == pid))
            .scalars()
            .all()
        )
        if existing_count:
            print(f"  [ok] Budget items exist for {slug} ({len(existing_count)} rows)")
            continue
        if not dry_run:
            for item in items:
                session.add(
                    ProjectBudgetItem(
                        id=_uid(),
                        project_id=pid,
                        org_id=org_id,
                        category=item["category"],
                        budgeted_amount=item["budget"],
                        actual_amount=item["actual"],
                        currency="EUR",
                        status=item["status"],
                        created_by=user_id,
                    )
                )
        print(f"  [+] {len(items)} budget items for {slug}")


# ── Risk Assessments ────────────────────────────────────────────────────────

RISKS: dict[str, list[dict]] = {
    "helios-solar-portfolio-iberia": [
        {
            "title": "Curtailment risk — Almería grid congestion",
            "risk_type": RiskType.OPERATIONAL,
            "severity": RiskSeverity.HIGH,
            "probability": RiskProbability.MEDIUM,
            "description": "Almería 132 kV feeder at 94% utilisation; curtailment averaging 4.2% YTD above P50 assumption of 2.5%. REE upgrade scheduled H2 2026.",
            "mitigation": "Grid upgrade agreement in place; revenue insurance policy covers curtailment >3.5%",
        },
        {
            "title": "Merchant price volatility — Iberian pool",
            "risk_type": RiskType.MARKET,
            "severity": RiskSeverity.HIGH,
            "probability": RiskProbability.MEDIUM,
            "description": "44% of revenue uncontracted after 2031; OMIE forward curve 60-75 €/MWh vs model base 65 €/MWh.",
            "mitigation": "2-year rolling hedge strategy; option to extend Endesa PPA to 12yr",
        },
        {
            "title": "Panel degradation above forecast",
            "risk_type": RiskType.TECHNICAL,
            "severity": RiskSeverity.MEDIUM,
            "probability": RiskProbability.LOW,
            "description": "P90 degradation scenario (0.7%/yr) would reduce revenues by ~3.2% over asset life vs P50 (0.45%/yr).",
            "mitigation": "Annual thermal imaging survey; panel replacement reserve funded from O&M budget",
        },
        {
            "title": "Counterparty credit — Iberdrola CfD PPA",
            "risk_type": RiskType.COUNTERPARTY,
            "severity": RiskSeverity.MEDIUM,
            "probability": RiskProbability.LOW,
            "description": "Iberdrola rated BBB+ (S&P); €280 GWh/yr contracted. Change-of-control or downgrade below BB triggers put option.",
            "mitigation": "Put option in PPA; parent guarantee from Iberdrola S.A.",
        },
        {
            "title": "Regulatory change — Spanish RES regulation",
            "risk_type": RiskType.REGULATORY,
            "severity": RiskSeverity.MEDIUM,
            "probability": RiskProbability.LOW,
            "description": "MITECO regulatory review 2027 could alter merchant access rules or introduce capacity payments.",
            "mitigation": "Government affairs monitoring; industry association membership",
        },
        {
            "title": "DSCR covenant breach — stress scenario",
            "risk_type": RiskType.FINANCIAL,
            "severity": RiskSeverity.HIGH,
            "probability": RiskProbability.LOW,
            "description": "P90 yield + P90 price scenario compresses DSCR to 1.12x vs 1.15x minimum covenant.",
            "mitigation": "€9M reserve account maintained; equity cure right available for 2 consecutive quarters",
        },
    ],
    "nordvik-wind-farm-ii": [
        {
            "title": "Construction delay — weather window risk",
            "risk_type": RiskType.CONSTRUCTION,
            "severity": RiskSeverity.HIGH,
            "probability": RiskProbability.MEDIUM,
            "description": "Blade installation dependent on <10m/s wind conditions; Oct-Mar window has 40% probability of multi-week delay. COD slip to Q1 2027 would cost ~€4.2M lost revenue.",
            "mitigation": "EPC liquidated damages clause; completion guarantee from Vestas; €22M contingency intact",
        },
        {
            "title": "Grid commissioning delay — Statnett",
            "risk_type": RiskType.REGULATORY,
            "severity": RiskSeverity.HIGH,
            "probability": RiskProbability.MEDIUM,
            "description": "Statnett 132 kV substation construction 60% complete; any delay in energization pushes COD.",
            "mitigation": "Dedicated Statnett project manager; weekly progress calls; delay insurance in place",
        },
        {
            "title": "Wind resource below P50",
            "risk_type": RiskType.OPERATIONAL,
            "severity": RiskSeverity.HIGH,
            "probability": RiskProbability.LOW,
            "description": "P90 AEP 629 GWh vs P50 708 GWh; 3 consecutive low-wind years would breach DSCR by Year 3.",
            "mitigation": "Wind data from 15yr mast; 2-year DSCR grace period in loan; cash sweep mechanism",
        },
        {
            "title": "EPC contractor default",
            "risk_type": RiskType.COUNTERPARTY,
            "severity": RiskSeverity.HIGH,
            "probability": RiskProbability.LOW,
            "description": "Implenia B-rated (S&P); single EPC for civil & electrical works.",
            "mitigation": "10% retention bond; parent guarantee from Implenia AG; step-in rights",
        },
        {
            "title": "ElCert price decline",
            "risk_type": RiskType.MARKET,
            "severity": RiskSeverity.MEDIUM,
            "probability": RiskProbability.MEDIUM,
            "description": "Norwegian ElCert trades at NOK 21/MWh (€1.84); floor risk if Sweden exits scheme.",
            "mitigation": "Sweden exit scenario modelled; Nordpool spot covers 80% of revenue base case",
        },
        {
            "title": "Reindeer migration corridor dispute",
            "risk_type": RiskType.ENVIRONMENTAL,
            "severity": RiskSeverity.MEDIUM,
            "probability": RiskProbability.LOW,
            "description": "Sami reindeer herders have filed an appeal against NVE permit; case in Norwegian Supreme Court.",
            "mitigation": "Voluntary mitigation protocol agreed with Sami Association; corridor buffers built into layout",
        },
        {
            "title": "Interest rate risk — floating rate debt",
            "risk_type": RiskType.FINANCIAL,
            "severity": RiskSeverity.MEDIUM,
            "probability": RiskProbability.MEDIUM,
            "description": "€287M EURIBOR-linked; 1% EURIBOR increase = €2.87M additional annual cost.",
            "mitigation": "65% of debt hedged with interest rate cap at 4.5% EURIBOR through 2028",
        },
    ],
    "adriatic-infrastructure-holdings": [
        {
            "title": "Croatian water tariff review risk",
            "risk_type": RiskType.REGULATORY,
            "severity": RiskSeverity.HIGH,
            "probability": RiskProbability.MEDIUM,
            "description": "HRT 3-year tariff determination due H1 2027. If regulator caps below CPI formula, EBITDA could fall 8-12%. Modelled as base case risk.",
            "mitigation": "Active engagement with HRT; evidence dossier on capital expenditure needs submitted",
        },
        {
            "title": "Traffic volume underperformance — A1-ext",
            "risk_type": RiskType.MARKET,
            "severity": RiskSeverity.MEDIUM,
            "probability": RiskProbability.LOW,
            "description": "ADT 8,340 vs 8,500 five-year target; Croatian tourism growth +3.1% offsets haulage softness.",
            "mitigation": "Shadow toll structure ensures minimum payment floor from Croatian government",
        },
        {
            "title": "Inflation on O&M costs — water utility",
            "risk_type": RiskType.FINANCIAL,
            "severity": RiskSeverity.MEDIUM,
            "probability": RiskProbability.MEDIUM,
            "description": "Croatian CPI 5.2% vs tariff increase 4.2%; margin compression if energy and chemical costs remain elevated.",
            "mitigation": "Energy cost pass-through clause in revised concession; chemical procurement 18-month contract",
        },
        {
            "title": "Political risk — Croatia EU asset ownership rules",
            "risk_type": RiskType.REGULATORY,
            "severity": RiskSeverity.MEDIUM,
            "probability": RiskProbability.LOW,
            "description": "Proposed Croatian legislation on strategic infrastructure ownership (foreign equity cap 49% for water).",
            "mitigation": "51% held via Croatian SPV meeting local ownership rules; legal opinion confirms compliance",
        },
        {
            "title": "District heating system failure — Ljubljana",
            "risk_type": RiskType.TECHNICAL,
            "severity": RiskSeverity.HIGH,
            "probability": RiskProbability.LOW,
            "description": "Primary distribution pipework average age 28yr; catastrophic failure risk during winter peak demand.",
            "mitigation": "Annual CCTV inspection; €4.2M capex provision for pipe sections >35yr; emergency heat supply agreement with local gas utility",
        },
        {
            "title": "FX risk — NOK / HRK revenue vs EUR debt",
            "risk_type": RiskType.MARKET,
            "severity": RiskSeverity.LOW,
            "probability": RiskProbability.MEDIUM,
            "description": "HRK income on water utility; Croatia adopted EUR in 2023 eliminating FX risk. Slovenia DH in EUR.",
            "mitigation": "Full EUR revenue base following Croatian EUR adoption (Jan 2023) — risk substantially eliminated",
        },
        {
            "title": "Refinancing risk — 2035 debt maturity",
            "risk_type": RiskType.FINANCIAL,
            "severity": RiskSeverity.MEDIUM,
            "probability": RiskProbability.LOW,
            "description": "€339.5M consolidated facility matures 2035; refinancing risk if credit markets tighten.",
            "mitigation": "Long-dated assets; DSCR amortisation schedule ensures 30% principal repaid by 2030",
        },
    ],
}


def ensure_risks(
    session: Session,
    org_id: uuid.UUID,
    project_ids: dict[str, uuid.UUID],
    user_id: uuid.UUID,
    dry_run: bool,
) -> None:
    for slug, risks in RISKS.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        existing = (
            session.execute(
                select(RiskAssessment).where(
                    RiskAssessment.entity_id == pid,
                    RiskAssessment.org_id == org_id,
                )
            )
            .scalars()
            .all()
        )
        if existing:
            print(f"  [ok] Risk assessments exist for {slug} ({len(existing)} rows)")
            continue
        if not dry_run:
            for risk in risks:
                session.add(
                    RiskAssessment(
                        id=_uid(),
                        org_id=org_id,
                        entity_id=pid,
                        entity_type=RiskEntityType.PROJECT,
                        title=risk["title"],
                        description=risk["description"],
                        risk_type=risk["risk_type"],
                        severity=risk["severity"],
                        probability=risk["probability"],
                        mitigation=risk["mitigation"],
                        status=RiskAssessmentStatus.ACTIVE,
                        assessed_by=user_id,
                    )
                )
        print(f"  [+] {len(risks)} risk assessments for {slug}")


# ── ESG Metrics ─────────────────────────────────────────────────────────────

ESG_DATA: dict[str, dict] = {
    "helios-solar-portfolio-iberia": {
        "carbon_avoided_tco2e": Decimal("595000"),
        "carbon_intensity_gco2e_kwh": Decimal("0"),
        "renewable_energy_pct": Decimal("100"),
        "water_usage_cubic_m": Decimal("18500"),
        "waste_recycled_pct": Decimal("94"),
        "biodiversity_score": Decimal("78"),
        "social_jobs_created": 340,
        "governance_score": Decimal("85"),
        "gresb_score": Decimal("74"),
        "eu_taxonomy_eligible_pct": Decimal("100"),
        "sfdr_classification": "article_9",
        "esg_data": {
            "carbon": {"lcoe_gco2e_kwh": 22.5, "displaces_coal_tco2e": 595000},
            "water": {"water_use_m3_per_mwh": 0.024, "source": "groundwater abstraction permitted"},
            "biodiversity": {
                "agrivoltaic_co_use": True,
                "pollinator_corridors": True,
                "sheep_grazing": True,
            },
            "social": {
                "local_jobs_operations": 42,
                "local_jobs_construction": 298,
                "community_fund_eur": 150000,
            },
            "certifications": ["GRESB Green Star", "ISO 14001", "SFDR Art.9"],
        },
    },
    "nordvik-wind-farm-ii": {
        "carbon_avoided_tco2e": Decimal("322000"),
        "carbon_intensity_gco2e_kwh": Decimal("0"),
        "renewable_energy_pct": Decimal("100"),
        "water_usage_cubic_m": Decimal("0"),
        "waste_recycled_pct": Decimal("88"),
        "biodiversity_score": Decimal("71"),
        "social_jobs_created": 180,
        "governance_score": Decimal("82"),
        "gresb_score": Decimal("68"),
        "eu_taxonomy_eligible_pct": Decimal("100"),
        "sfdr_classification": "article_9",
        "esg_data": {
            "carbon": {
                "construction_phase_tco2e": 48000,
                "operational_tco2e_avoided_annual": 322000,
            },
            "biodiversity": {
                "reindeer_corridors_preserved_m": 2800,
                "raptor_monitoring_active": True,
                "bat_acoustic_monitoring": True,
            },
            "social": {
                "local_content_pct": 38,
                "indigenous_consultation_rounds": 12,
                "jobs_construction": 145,
                "jobs_operations": 35,
            },
            "certifications": ["Norwegian EPBD", "ISO 14001 (pending COD)", "EU Taxonomy eligible"],
        },
    },
    "adriatic-infrastructure-holdings": {
        "carbon_avoided_tco2e": Decimal("18000"),
        "carbon_intensity_gco2e_kwh": None,
        "renewable_energy_pct": Decimal("22"),
        "water_usage_cubic_m": Decimal("28000000"),
        "waste_recycled_pct": Decimal("71"),
        "biodiversity_score": Decimal("62"),
        "social_jobs_created": 520,
        "governance_score": Decimal("80"),
        "gresb_score": Decimal("63"),
        "eu_taxonomy_eligible_pct": Decimal("68"),
        "sfdr_classification": "article_8",
        "esg_data": {
            "carbon": {
                "district_heating_co2_avoided_tco2e": 12000,
                "motorway_avoided_emissions_tco2e": 6000,
                "water_treatment_energy_kwh_per_m3": 0.42,
            },
            "water": {
                "connections_served": 340000,
                "non_revenue_water_pct": 18.2,
                "target_nrw_pct_2027": 14.0,
            },
            "social": {
                "jobs_total": 520,
                "local_procurement_pct": 72,
                "water_access_improvement": True,
                "district_heating_households": 12800,
            },
            "certifications": [
                "ISO 14001 (all assets)",
                "EU Taxonomy Art.8",
                "Croatian ESG Charter",
            ],
        },
    },
}


def ensure_esg(
    session: Session, org_id: uuid.UUID, project_ids: dict[str, uuid.UUID], dry_run: bool
) -> None:
    for slug, esg in ESG_DATA.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        existing = session.execute(
            select(ESGMetrics).where(
                ESGMetrics.project_id == pid,
                ESGMetrics.org_id == org_id,
            )
        ).scalar_one_or_none()
        if existing:
            print(f"  [ok] ESG metrics exist for {slug}")
            continue
        if not dry_run:
            session.add(
                ESGMetrics(
                    id=_uid(),
                    project_id=pid,
                    org_id=org_id,
                    **{k: v for k, v in esg.items()},
                    as_of_date=REPORTING_DATE,
                )
            )
        print(f"  [+] ESG metrics for {slug}")


# ── KPI Targets & Actuals ───────────────────────────────────────────────────

KPI_DATA: dict[str, list[dict]] = {
    "helios-solar-portfolio-iberia": [
        {
            "name": "Energy Production (GWh)",
            "unit": "GWh",
            "target": Decimal("768.5"),
            "actual": Decimal("786.2"),
            "period": "2025-12-31",
        },
        {
            "name": "Capacity Factor (%)",
            "unit": "%",
            "target": Decimal("20.8"),
            "actual": Decimal("21.3"),
            "period": "2025-12-31",
        },
        {
            "name": "DSCR",
            "unit": "x",
            "target": Decimal("1.15"),
            "actual": Decimal("1.42"),
            "period": "2025-12-31",
        },
        {
            "name": "Availability Factor (%)",
            "unit": "%",
            "target": Decimal("98.0"),
            "actual": Decimal("98.6"),
            "period": "2025-12-31",
        },
        {
            "name": "Revenue (€M)",
            "unit": "€M",
            "target": Decimal("46.5"),
            "actual": Decimal("48.2"),
            "period": "2025-12-31",
        },
        {
            "name": "EBITDA Margin (%)",
            "unit": "%",
            "target": Decimal("79.0"),
            "actual": Decimal("81.5"),
            "period": "2025-12-31",
        },
        {
            "name": "Curtailment (%)",
            "unit": "%",
            "target": Decimal("2.5"),
            "actual": Decimal("4.2"),
            "period": "2025-12-31",
        },
    ],
    "nordvik-wind-farm-ii": [
        {
            "name": "Construction Completion (%)",
            "unit": "%",
            "target": Decimal("95.0"),
            "actual": Decimal("85.0"),
            "period": "2026-03-01",
        },
        {
            "name": "Budget Utilisation (%)",
            "unit": "%",
            "target": Decimal("88.0"),
            "actual": Decimal("91.2"),
            "period": "2026-03-01",
        },
        {
            "name": "Contingency Remaining (€M)",
            "unit": "€M",
            "target": Decimal("18.0"),
            "actual": Decimal("21.6"),
            "period": "2026-03-01",
        },
        {
            "name": "Schedule Adherence (days vs baseline)",
            "unit": "days",
            "target": Decimal("0"),
            "actual": Decimal("14"),
            "period": "2026-03-01",
        },
        {
            "name": "H&S Incidents (LTI rate)",
            "unit": "per 200k hrs",
            "target": Decimal("0.0"),
            "actual": Decimal("0.0"),
            "period": "2026-03-01",
        },
    ],
    "adriatic-infrastructure-holdings": [
        {
            "name": "Motorway ADT (vehicles/day)",
            "unit": "ADT",
            "target": Decimal("8500"),
            "actual": Decimal("8340"),
            "period": "2025-12-31",
        },
        {
            "name": "Water EBITDA Margin (%)",
            "unit": "%",
            "target": Decimal("36.0"),
            "actual": Decimal("38.2"),
            "period": "2025-12-31",
        },
        {
            "name": "Non-Revenue Water (%)",
            "unit": "%",
            "target": Decimal("20.0"),
            "actual": Decimal("18.2"),
            "period": "2025-12-31",
        },
        {
            "name": "Consolidated DSCR",
            "unit": "x",
            "target": Decimal("1.20"),
            "actual": Decimal("1.38"),
            "period": "2025-12-31",
        },
        {
            "name": "District Heating Availability (%)",
            "unit": "%",
            "target": Decimal("99.0"),
            "actual": Decimal("99.4"),
            "period": "2025-12-31",
        },
        {
            "name": "Portfolio Revenue (€M)",
            "unit": "€M",
            "target": Decimal("58.0"),
            "actual": Decimal("61.2"),
            "period": "2025-12-31",
        },
    ],
}


def ensure_kpis(
    session: Session, org_id: uuid.UUID, project_ids: dict[str, uuid.UUID], dry_run: bool
) -> None:
    for slug, kpis in KPI_DATA.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        existing = (
            session.execute(select(KPITarget).where(KPITarget.project_id == pid)).scalars().all()
        )
        if existing:
            print(f"  [ok] KPIs exist for {slug} ({len(existing)} rows)")
            continue
        if not dry_run:
            for kpi in kpis:
                period_date = date.fromisoformat(kpi["period"])
                target = KPITarget(
                    id=_uid(),
                    project_id=pid,
                    org_id=org_id,
                    name=kpi["name"],
                    unit=kpi["unit"],
                    target_value=kpi["target"],
                    period_start=date(period_date.year, 1, 1),
                    period_end=period_date,
                )
                session.add(target)
                session.flush()
                session.add(
                    KPIActual(
                        id=_uid(),
                        target_id=target.id,
                        project_id=pid,
                        org_id=org_id,
                        actual_value=kpi["actual"],
                        recorded_at=_now(),
                        notes="Seed data — actual as at reporting date",
                    )
                )
        print(f"  [+] {len(kpis)} KPIs for {slug}")


# ── Documents ───────────────────────────────────────────────────────────────

DOCUMENTS: dict[str, list[dict]] = {
    "helios-solar-portfolio-iberia": [
        {
            "name": "Helios Solar — Financial Model v4.2.xlsx",
            "file_type": "xlsx",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "size": 2847291,
            "classification": "confidential",
        },
        {
            "name": "EPC Completion Certificate — Portfolio.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 1243000,
            "classification": "confidential",
        },
        {
            "name": "Grid Connection Agreement — REE.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 892000,
            "classification": "restricted",
        },
        {
            "name": "PPA Agreement — Iberdrola CfD.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 1680000,
            "classification": "restricted",
        },
        {
            "name": "PPA Agreement — Endesa Fixed.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 1420000,
            "classification": "restricted",
        },
        {
            "name": "Environmental Impact Assessment.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 4200000,
            "classification": "internal",
        },
        {
            "name": "DSCR Certificate Q4 2025.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 284000,
            "classification": "confidential",
        },
        {
            "name": "Insurance Certificates 2026.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 562000,
            "classification": "internal",
        },
        {
            "name": "Sponsor Equity Model — Helios HoldCo.xlsx",
            "file_type": "xlsx",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "size": 1890000,
            "classification": "restricted",
        },
        {
            "name": "GRESB Assessment Report 2025.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 3100000,
            "classification": "internal",
        },
    ],
    "nordvik-wind-farm-ii": [
        {
            "name": "Nordvik Wind — Financial Model v3.1.xlsx",
            "file_type": "xlsx",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "size": 3241000,
            "classification": "confidential",
        },
        {
            "name": "NVE Wind Power Licence.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 2100000,
            "classification": "internal",
        },
        {
            "name": "EPC Contract — Vestas + Implenia (redacted).pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 3800000,
            "classification": "restricted",
        },
        {
            "name": "Wind Resource Assessment — AWS Truepower.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 5200000,
            "classification": "internal",
        },
        {
            "name": "Construction Progress Report — Feb 2026.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 4800000,
            "classification": "internal",
        },
        {
            "name": "Biodiversity Management Plan.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 1620000,
            "classification": "internal",
        },
        {
            "name": "Sami Consultation Protocol.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 890000,
            "classification": "confidential",
        },
        {
            "name": "DNB Nordea Facility Agreement — Summary.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 1340000,
            "classification": "restricted",
        },
        {
            "name": "Insurance — Construction All Risks 2026.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 780000,
            "classification": "internal",
        },
    ],
    "adriatic-infrastructure-holdings": [
        {
            "name": "Adriatic Holdings — Financial Model v2.8.xlsx",
            "file_type": "xlsx",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "size": 2980000,
            "classification": "confidential",
        },
        {
            "name": "Motorway PPP Concession Agreement A1-ext.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 6200000,
            "classification": "restricted",
        },
        {
            "name": "Zadar Water SPA — Share Purchase Agreement.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 4100000,
            "classification": "restricted",
        },
        {
            "name": "Ljubljana DH Acquisition Agreement.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 3400000,
            "classification": "restricted",
        },
        {
            "name": "Consolidated Senior Facility Agreement 2023.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 5800000,
            "classification": "restricted",
        },
        {
            "name": "Traffic Count Report A1-ext — Q4 2025.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 1200000,
            "classification": "internal",
        },
        {
            "name": "Water Utility Annual Report 2025.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 3600000,
            "classification": "internal",
        },
        {
            "name": "ISO 14001 Certificates — All Assets.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 980000,
            "classification": "internal",
        },
        {
            "name": "HRT Tariff Decision — 2025.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 1480000,
            "classification": "confidential",
        },
        {
            "name": "Ljubljana DH Phase II — Grant Application.pdf",
            "file_type": "pdf",
            "mime_type": "application/pdf",
            "size": 2200000,
            "classification": "internal",
        },
    ],
}


def ensure_documents(
    session: Session,
    org_id: uuid.UUID,
    project_ids: dict[str, uuid.UUID],
    user_id: uuid.UUID,
    dry_run: bool,
) -> None:
    for slug, docs in DOCUMENTS.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        existing = (
            session.execute(
                select(Document).where(
                    Document.project_id == pid,
                    Document.org_id == org_id,
                    Document.is_deleted == False,  # noqa: E712
                )
            )
            .scalars()
            .all()
        )
        if existing:
            print(f"  [ok] Documents exist for {slug} ({len(existing)} rows)")
            continue
        if not dry_run:
            for doc in docs:
                doc_id = _uid()
                s3_key = f"{org_id}/{pid}/root/{doc_id}_{doc['name'].replace(' ', '_')}"
                classification = DocumentClassification(doc["classification"])
                session.add(
                    Document(
                        id=doc_id,
                        org_id=org_id,
                        project_id=pid,
                        name=doc["name"],
                        file_type=doc["file_type"],
                        mime_type=doc["mime_type"],
                        s3_key=s3_key,
                        s3_bucket="scr-staging-documents",
                        file_size_bytes=doc["size"],
                        status=DocumentStatus.READY,
                        classification=classification,
                        version=1,
                        uploaded_by=user_id,
                    )
                )
        print(f"  [+] {len(docs)} documents for {slug}")


# ── Legal Documents ─────────────────────────────────────────────────────────

LEGAL_DOCS: dict[str, list[dict]] = {
    "helios-solar-portfolio-iberia": [
        {
            "title": "NDA — PAMP Infrastructure Partners / Helios Solar",
            "doc_type": LegalDocumentType.NDA,
            "status": LegalDocumentStatus.EXECUTED,
            "signed_date": date(2024, 5, 10),
            "expiry_date": date(2026, 5, 10),
            "content": "Mutual non-disclosure agreement between Greenfield Development Partners (as Developer) and PAMP Infrastructure Partners (as Investor) in connection with the potential acquisition of equity interests in the Helios Solar Portfolio Iberia project. Term: 24 months. Governed by Spanish law.",
        },
        {
            "title": "Term Sheet — Helios Solar Equity Investment",
            "doc_type": LegalDocumentType.TERM_SHEET,
            "status": LegalDocumentStatus.SIGNED,
            "signed_date": date(2024, 8, 1),
            "expiry_date": date(2024, 10, 31),
            "content": "Non-binding indicative term sheet for the acquisition of a 30.0% equity interest in Helios Solar HoldCo S.à r.l. (Luxembourg) by PAMP Infrastructure Partners. Headline terms: €93.6M equity valuation; 30.0% = €28.08M. MOIC floor 1.6x; call option at Year 5.",
        },
        {
            "title": "Subscription Agreement — Helios Solar HoldCo",
            "doc_type": LegalDocumentType.SUBSCRIPTION_AGREEMENT,
            "status": LegalDocumentStatus.EXECUTED,
            "signed_date": date(2024, 8, 15),
            "expiry_date": None,
            "content": "Subscription and shareholders agreement governing PAMP Infrastructure Partners 30.0% equity stake in Helios Solar HoldCo S.à r.l. Includes board representation rights (1 of 3 seats), drag-along/tag-along, ROFO provisions, and DSCR covenant test notification obligations.",
        },
        {
            "title": "SPV Luxembourg Incorporation — Helios Solar HoldCo",
            "doc_type": LegalDocumentType.SPV_INCORPORATION,
            "status": LegalDocumentStatus.EXECUTED,
            "signed_date": date(2023, 4, 28),
            "expiry_date": None,
            "content": "Articles of incorporation and corporate governance documents for Helios Solar HoldCo S.à r.l. registered in Luxembourg (RCSL B274891). Share capital €125,000. Greenfield Development Partners: 70.0%; PAMP Infrastructure Partners: 30.0% post-closing.",
        },
    ],
    "nordvik-wind-farm-ii": [
        {
            "title": "NDA — PAMP Infrastructure Partners / Nordvik Wind II",
            "doc_type": LegalDocumentType.NDA,
            "status": LegalDocumentStatus.EXECUTED,
            "signed_date": date(2025, 1, 15),
            "expiry_date": date(2027, 1, 15),
            "content": "Mutual NDA between Greenfield Development Partners and PAMP Infrastructure Partners for due diligence access on Nordvik Wind Farm II project. Norwegian law governs; Oslo District Court jurisdiction.",
        },
        {
            "title": "Term Sheet — Nordvik Wind II Equity Co-Investment",
            "doc_type": LegalDocumentType.TERM_SHEET,
            "status": LegalDocumentStatus.REVIEW,
            "signed_date": None,
            "expiry_date": date(2026, 5, 31),
            "content": "Indicative term sheet for PAMP's co-investment in Nordvik Wind Farm II alongside Greenfield. PAMP acquiring 25.0% equity post-COD. Pre-COD development risk covered by Greenfield; construction completion guarantee from Vestas.",
        },
        {
            "title": "Side Letter — Construction Period Information Rights",
            "doc_type": LegalDocumentType.SIDE_LETTER,
            "status": LegalDocumentStatus.EXECUTED,
            "signed_date": date(2025, 3, 22),
            "expiry_date": date(2026, 12, 31),
            "content": "Side letter to NDA granting PAMP monthly construction progress reports and site inspection rights during construction phase. Automatically terminates on COD or subscription agreement signing.",
        },
    ],
    "adriatic-infrastructure-holdings": [
        {
            "title": "NDA — PAMP Infrastructure Partners / Adriatic Holdings",
            "doc_type": LegalDocumentType.NDA,
            "status": LegalDocumentStatus.EXECUTED,
            "signed_date": date(2024, 9, 1),
            "expiry_date": date(2026, 9, 1),
            "content": "Mutual NDA for Adriatic Infrastructure Holdings due diligence. Covers all three sub-assets (motorway PPP, Zadar Water, Ljubljana DH). English law; London arbitration.",
        },
        {
            "title": "Term Sheet — Adriatic Infrastructure Holdings",
            "doc_type": LegalDocumentType.TERM_SHEET,
            "status": LegalDocumentStatus.SIGNED,
            "signed_date": date(2024, 11, 30),
            "expiry_date": date(2025, 3, 31),
            "content": "Non-binding term sheet for PAMP acquisition of 20.0% equity in Adriatic Infrastructure Holdings B.V. (Netherlands). Acquisition price €29.1M (20% of €145.5M equity); aligned with independent valuation at 1.02x book. Completion subject to Croatian FDI filing.",
        },
        {
            "title": "Shareholders Agreement — Adriatic Infrastructure Holdings B.V.",
            "doc_type": LegalDocumentType.SUBSCRIPTION_AGREEMENT,
            "status": LegalDocumentStatus.DRAFT,
            "signed_date": None,
            "expiry_date": None,
            "content": "Draft shareholders agreement for Adriatic Infrastructure Holdings B.V. PAMP acquiring 20.0% stake; Greenfield retains 80.0%. Reserved matters require 75% shareholder approval. PAMP entitled to quarterly management accounts and audited annual financials.",
        },
    ],
}


def ensure_legal_docs(
    session: Session,
    org_id: uuid.UUID,
    investor_org_id: uuid.UUID | None,
    project_ids: dict[str, uuid.UUID],
    dry_run: bool,
) -> None:
    for slug, docs in LEGAL_DOCS.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        existing = (
            session.execute(
                select(LegalDocument).where(
                    LegalDocument.org_id == org_id,
                    LegalDocument.project_id == pid,
                    LegalDocument.is_deleted == False,  # noqa: E712
                )
            )
            .scalars()
            .all()
        )
        if existing:
            print(f"  [ok] Legal docs exist for {slug} ({len(existing)} rows)")
            continue
        if not dry_run:
            for doc in docs:
                session.add(
                    LegalDocument(
                        id=_uid(),
                        org_id=org_id,
                        project_id=pid,
                        title=doc["title"],
                        doc_type=doc["doc_type"],
                        status=doc["status"],
                        content=doc["content"],
                        signed_date=doc.get("signed_date"),
                        expiry_date=doc.get("expiry_date"),
                        counterparty_org_id=investor_org_id,
                        version=1,
                        metadata_={
                            "counterparty_name": "PAMP Infrastructure Partners",
                            "seeded": True,
                        },
                    )
                )
        print(f"  [+] {len(docs)} legal docs for {slug}")


# ── Certifications ──────────────────────────────────────────────────────────

CERTIFICATIONS = {
    "helios-solar-portfolio-iberia": {
        "status": "certified",
        "tier": "premium",
        "certification_score": 88.4,
        "dimension_scores": {
            "financial_documentation": 92,
            "legal_structure": 90,
            "esg_credentials": 94,
            "team_track_record": 86,
            "risk_management": 84,
            "investor_reporting": 87,
        },
        "certification_count": 2,
        "consecutive_months_certified": 14,
    },
    "nordvik-wind-farm-ii": {
        "status": "certified",
        "tier": "standard",
        "certification_score": 81.2,
        "dimension_scores": {
            "financial_documentation": 84,
            "legal_structure": 78,
            "esg_credentials": 87,
            "team_track_record": 82,
            "risk_management": 76,
            "investor_reporting": 80,
        },
        "certification_count": 1,
        "consecutive_months_certified": 5,
    },
    "adriatic-infrastructure-holdings": {
        "status": "certified",
        "tier": "standard",
        "certification_score": 83.6,
        "dimension_scores": {
            "financial_documentation": 86,
            "legal_structure": 88,
            "esg_credentials": 83,
            "team_track_record": 79,
            "risk_management": 84,
            "investor_reporting": 82,
        },
        "certification_count": 1,
        "consecutive_months_certified": 8,
    },
}


def ensure_certifications(
    session: Session, org_id: uuid.UUID, project_ids: dict[str, uuid.UUID], dry_run: bool
) -> None:
    for slug, cert in CERTIFICATIONS.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        existing = session.execute(
            select(InvestorReadinessCertification).where(
                InvestorReadinessCertification.project_id == pid,
                InvestorReadinessCertification.org_id == org_id,
            )
        ).scalar_one_or_none()
        if existing:
            print(f"  [ok] Certification exists for {slug}")
            continue
        if not dry_run:
            session.add(
                InvestorReadinessCertification(
                    id=_uid(),
                    project_id=pid,
                    org_id=org_id,
                    status=cert["status"],
                    tier=cert["tier"],
                    certification_score=cert["certification_score"],
                    dimension_scores=cert["dimension_scores"],
                    certification_count=cert["certification_count"],
                    consecutive_months_certified=cert["consecutive_months_certified"],
                    certified_at=_now(),
                    last_verified_at=_now(),
                )
            )
        print(f"  [+] Certification ({cert['tier']}, {cert['certification_score']}) for {slug}")


# ── Match Results ───────────────────────────────────────────────────────────

MATCH_SCORES = {
    "helios-solar-portfolio-iberia": {
        "overall_score": 91,
        "status": MatchStatus.ENGAGED,
        "score_breakdown": {
            "geography_match": 92,
            "asset_type_match": 95,
            "ticket_size_match": 88,
            "irr_target_match": 90,
            "esg_alignment": 94,
            "stage_match": 87,
        },
        "investor_notes": "Strong match — operational solar in Iberia is core mandate. Moving to subscription agreement phase.",
        "ally_notes": "PAMP confirmed interest in 30% equity stake at €28M. Preferred investor for Series A close.",
    },
    "nordvik-wind-farm-ii": {
        "overall_score": 78,
        "status": MatchStatus.INTRO_REQUESTED,
        "score_breakdown": {
            "geography_match": 80,
            "asset_type_match": 88,
            "ticket_size_match": 75,
            "irr_target_match": 82,
            "esg_alignment": 90,
            "stage_match": 64,
        },
        "investor_notes": "Solid match on fundamentals. Construction risk is concern — need COD guarantee comfort.",
        "ally_notes": "Vestas completion guarantee confirmed. PAMP call scheduled for 15 March 2026.",
    },
    "adriatic-infrastructure-holdings": {
        "overall_score": 84,
        "status": MatchStatus.MEETING_SCHEDULED,
        "score_breakdown": {
            "geography_match": 78,
            "asset_type_match": 82,
            "ticket_size_match": 90,
            "irr_target_match": 85,
            "esg_alignment": 80,
            "stage_match": 92,
        },
        "investor_notes": "Diversified core infra — fits LP mandate for stable yield. Meeting with Croatian FIUPIK team scheduled.",
        "ally_notes": "Meeting set for 18 March 2026 — presenting motorway traffic data and water utility financials.",
    },
}


def ensure_match_results(
    session: Session,
    ally_org_id: uuid.UUID,
    investor_org_id: uuid.UUID | None,
    project_ids: dict[str, uuid.UUID],
    dry_run: bool,
) -> None:
    if not investor_org_id:
        print("  [skip] No investor org found — skipping match results")
        return

    for slug, data in MATCH_SCORES.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        existing = session.execute(
            select(MatchResult).where(
                MatchResult.investor_org_id == investor_org_id,
                MatchResult.ally_org_id == ally_org_id,
                MatchResult.project_id == pid,
            )
        ).scalar_one_or_none()
        if existing:
            print(f"  [ok] MatchResult exists for {slug}")
            continue
        if not dry_run:
            session.add(
                MatchResult(
                    id=_uid(),
                    investor_org_id=investor_org_id,
                    ally_org_id=ally_org_id,
                    project_id=pid,
                    overall_score=data["overall_score"],
                    score_breakdown=data["score_breakdown"],
                    status=data["status"],
                    initiated_by=MatchInitiator.SYSTEM,
                    investor_notes=data["investor_notes"],
                    ally_notes=data["ally_notes"],
                )
            )
        print(f"  [+] MatchResult ({data['overall_score']}, {data['status'].value}) for {slug}")


# ── Covenants ───────────────────────────────────────────────────────────────

COVENANTS: dict[str, list[dict]] = {
    "helios-solar-portfolio-iberia": [
        {
            "name": "DSCR Minimum",
            "description": "Minimum debt service coverage ratio — annual test",
            "covenant_type": "financial",
            "threshold_value": Decimal("1.15"),
            "threshold_unit": "x",
            "measurement_frequency": "annual",
            "is_active": True,
        },
        {
            "name": "LLCR Minimum",
            "description": "Loan life coverage ratio — annual test",
            "covenant_type": "financial",
            "threshold_value": Decimal("1.30"),
            "threshold_unit": "x",
            "measurement_frequency": "annual",
            "is_active": True,
        },
        {
            "name": "Curtailment Maximum",
            "description": "Maximum annual curtailment allowance before covenant breach notification",
            "covenant_type": "operational",
            "threshold_value": Decimal("6.0"),
            "threshold_unit": "%",
            "measurement_frequency": "annual",
            "is_active": True,
        },
        {
            "name": "Availability Factor Minimum",
            "description": "Portfolio availability factor minimum for O&M contract compliance",
            "covenant_type": "operational",
            "threshold_value": Decimal("95.0"),
            "threshold_unit": "%",
            "measurement_frequency": "quarterly",
            "is_active": True,
        },
    ],
    "nordvik-wind-farm-ii": [
        {
            "name": "Construction Completion — Longstop Date",
            "description": "Hard longstop COD date — lender step-in rights activate if not met",
            "covenant_type": "construction",
            "threshold_value": None,
            "threshold_unit": "date",
            "measurement_frequency": "milestone",
            "is_active": True,
        },
        {
            "name": "Contingency Reserve — Minimum Balance",
            "description": "Minimum contingency reserve to remain funded throughout construction",
            "covenant_type": "financial",
            "threshold_value": Decimal("15000000"),
            "threshold_unit": "EUR",
            "measurement_frequency": "monthly",
            "is_active": True,
        },
        {
            "name": "LTI Rate Maximum",
            "description": "Lost Time Incident rate maximum during construction phase",
            "covenant_type": "hse",
            "threshold_value": Decimal("0.5"),
            "threshold_unit": "per 200k hrs",
            "measurement_frequency": "quarterly",
            "is_active": True,
        },
    ],
    "adriatic-infrastructure-holdings": [
        {
            "name": "Consolidated DSCR Minimum",
            "description": "Portfolio-level DSCR across all 3 assets — semi-annual test",
            "covenant_type": "financial",
            "threshold_value": Decimal("1.20"),
            "threshold_unit": "x",
            "measurement_frequency": "semi-annual",
            "is_active": True,
        },
        {
            "name": "LTV Maximum",
            "description": "Loan-to-value maximum — tested at each refinancing and annually",
            "covenant_type": "financial",
            "threshold_value": Decimal("75.0"),
            "threshold_unit": "%",
            "measurement_frequency": "annual",
            "is_active": True,
        },
        {
            "name": "Motorway ADT Minimum",
            "description": "Minimum average daily traffic below which concession revenue adjustment triggers",
            "covenant_type": "operational",
            "threshold_value": Decimal("6500"),
            "threshold_unit": "ADT",
            "measurement_frequency": "quarterly",
            "is_active": True,
        },
        {
            "name": "Water Non-Revenue Maximum",
            "description": "Maximum non-revenue water percentage before regulatory reporting obligation",
            "covenant_type": "regulatory",
            "threshold_value": Decimal("25.0"),
            "threshold_unit": "%",
            "measurement_frequency": "annual",
            "is_active": True,
        },
    ],
}


def ensure_covenants(
    session: Session, org_id: uuid.UUID, project_ids: dict[str, uuid.UUID], dry_run: bool
) -> None:
    for slug, covenants in COVENANTS.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        existing = (
            session.execute(select(Covenant).where(Covenant.project_id == pid)).scalars().all()
        )
        if existing:
            print(f"  [ok] Covenants exist for {slug} ({len(existing)} rows)")
            continue
        if not dry_run:
            for c in covenants:
                session.add(
                    Covenant(
                        id=_uid(),
                        project_id=pid,
                        org_id=org_id,
                        name=c["name"],
                        description=c["description"],
                        covenant_type=c["covenant_type"],
                        threshold_value=c.get("threshold_value"),
                        threshold_unit=c["threshold_unit"],
                        measurement_frequency=c["measurement_frequency"],
                        is_active=c["is_active"],
                    )
                )
        print(f"  [+] {len(covenants)} covenants for {slug}")


# ── Main ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Seed ally (Greenfield Development Partners) demo data."
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    parser.add_argument(
        "--wipe", action="store_true", help="Delete existing Greenfield org data before re-seeding"
    )
    args = parser.parse_args()

    engine = get_engine()

    with Session(engine) as session:
        print("\n=== SCR Platform — Ally Demo Seed ===")
        print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}\n")

        # ── Resolve investor org (for match results + legal counterparty) ──
        investor_org = session.execute(
            select(Organization).where(Organization.slug == INVESTOR_ORG_SLUG)
        ).scalar_one_or_none()

        if investor_org:
            investor_org_id = investor_org.id
            print(f"Investor org found: {investor_org.name} ({investor_org_id})")
        else:
            investor_org_id = None
            print(
                f"WARNING: Investor org '{INVESTOR_ORG_SLUG}' not found — run seed_demo_complete.py first for match data"
            )

        # ── Wipe ──────────────────────────────────────────────────────────
        if args.wipe and not args.dry_run:
            existing_org = session.execute(
                select(Organization).where(Organization.slug == ALLY_ORG_SLUG)
            ).scalar_one_or_none()
            if existing_org:
                print(f"\nWiping org {existing_org.id} and all associated data...")
                session.execute(delete(Organization).where(Organization.id == existing_org.id))
                session.commit()
                print("  Wipe complete.")
            else:
                print("  Nothing to wipe.")

        # ── Seed ──────────────────────────────────────────────────────────
        print("\n--- Org & User ---")
        org_id, user_id = ensure_org_user(session, args.dry_run)

        print("\n--- Projects ---")
        project_ids = ensure_projects(session, org_id, user_id, args.dry_run)

        if not args.dry_run:
            session.flush()

        print("\n--- Signal Scores ---")
        ensure_signal_scores(session, org_id, project_ids, args.dry_run)

        print("\n--- Milestones ---")
        ensure_milestones(session, org_id, project_ids, user_id, args.dry_run)

        print("\n--- Budget Items ---")
        ensure_budget_items(session, org_id, project_ids, user_id, args.dry_run)

        print("\n--- Risk Assessments ---")
        ensure_risks(session, org_id, project_ids, user_id, args.dry_run)

        print("\n--- ESG Metrics ---")
        ensure_esg(session, org_id, project_ids, args.dry_run)

        print("\n--- KPI Targets & Actuals ---")
        ensure_kpis(session, org_id, project_ids, args.dry_run)

        print("\n--- Documents ---")
        ensure_documents(session, org_id, project_ids, user_id, args.dry_run)

        print("\n--- Legal Documents ---")
        ensure_legal_docs(session, org_id, investor_org_id, project_ids, args.dry_run)

        print("\n--- Certifications ---")
        ensure_certifications(session, org_id, project_ids, args.dry_run)

        print("\n--- Match Results ---")
        ensure_match_results(session, org_id, investor_org_id, project_ids, args.dry_run)

        print("\n--- Covenants ---")
        ensure_covenants(session, org_id, project_ids, args.dry_run)

        if not args.dry_run:
            session.commit()
            print("\n✓ All ally demo data committed successfully.")
        else:
            print("\n[DRY RUN] No changes written.")

        print("\nSummary:")
        print(f"  Org:      Greenfield Development Partners ({ALLY_ORG_SLUG})")
        print(f"  User:     Alex Greenfield <{ALLY_USER_EMAIL}>")
        print(f"  Projects: {', '.join(p['name'] for p in PROJECTS)}")
        print(f"  Login URL: https://staging.scrplatform.com → use {ALLY_USER_EMAIL}")


if __name__ == "__main__":
    main()
