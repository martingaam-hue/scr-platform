#!/usr/bin/env python3
"""Demo seed script — 3 fully-populated projects for SCR Platform staging/demo.

Seeds: 1 investor org + 1 portfolio + 3 projects (Helios Solar, Nordvik Wind,
Adriatic Infrastructure) with risk assessments, covenants, KPIs, ESG metrics,
signal scores, milestones, budget items, and document records.

Usage (from apps/api directory):
    poetry run python scripts/seed_demo_projects.py
    poetry run python scripts/seed_demo_projects.py --dry-run
    poetry run python scripts/seed_demo_projects.py --wipe
"""

from __future__ import annotations

import argparse
import sys
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

# Ensure the apps/api root is on sys.path regardless of how the script is invoked:
#   • Docker container: __file__ = /app/scripts/seed..py → parent = /app
#   • Repo root (dev):  __file__ = apps/api/scripts/seed..py → parent = apps/api
_api_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _api_root not in sys.path:
    sys.path.insert(0, _api_root)

from app.core.config import settings
from app.core.database import Base  # noqa: F401 — registers all tables
from app.models.core import Organization, User
from app.models.projects import Project, ProjectMilestone, ProjectBudgetItem, SignalScore
from app.models.investors import Portfolio, PortfolioHolding, PortfolioMetrics, RiskAssessment
from app.models.monitoring import Covenant, KPIActual, KPITarget
from app.models.esg import ESGMetrics
from app.models.dataroom import Document, DocumentFolder
from app.models.enums import (
    OrgType, SubscriptionTier, SubscriptionStatus, UserRole,
    ProjectType, ProjectStatus, ProjectStage, MilestoneStatus, BudgetItemStatus,
    PortfolioStrategy, FundType, SFDRClassification, PortfolioStatus,
    AssetType, HoldingStatus,
    RiskEntityType, RiskType, RiskSeverity, RiskProbability, RiskAssessmentStatus,
    DocumentStatus, DocumentClassification,
)

from sqlalchemy import create_engine, select, delete, text
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEMO_ORG_SLUG = "pamp-infra-partners"
DEMO_USER_EMAIL = "demo@pampgroup.com"
DEMO_PORTFOLIO_NAME = "PAMP Infrastructure & Energy Fund I"

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def get_engine():
    url = settings.DATABASE_URL_SYNC
    return create_engine(url, echo=False)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _uid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Organisation & User
# ---------------------------------------------------------------------------

def seed_org_and_user(session: Session, dry_run: bool) -> tuple[uuid.UUID, uuid.UUID]:
    """Return (org_id, user_id) — create if not present."""
    existing_org = session.execute(
        select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
    ).scalar_one_or_none()

    if existing_org:
        print(f"  [OK] Org already exists: {existing_org.name} ({existing_org.id})")
        org_id = existing_org.id
    else:
        org_id = _uid()
        if not dry_run:
            org = Organization(
                id=org_id,
                name="PAMP Infrastructure Partners",
                slug=DEMO_ORG_SLUG,
                type=OrgType.INVESTOR,
                subscription_tier=SubscriptionTier.ENTERPRISE,
                subscription_status=SubscriptionStatus.ACTIVE,
                settings={
                    "base_currency": "EUR",
                    "reporting_date": "2026-03-01",
                    "fiscal_year_end": "12-31",
                    "esg_framework": "EU Taxonomy + SFDR Art. 9",
                },
            )
            session.add(org)
            session.flush()
        print(f"  [+] Created org: PAMP Infrastructure Partners ({org_id})")

    existing_user = session.execute(
        select(User).where(User.email == DEMO_USER_EMAIL)
    ).scalar_one_or_none()

    if existing_user:
        print(f"  [OK] User already exists: {existing_user.full_name} ({existing_user.id})")
        user_id = existing_user.id
    else:
        user_id = _uid()
        if not dry_run:
            user = User(
                id=user_id,
                org_id=org_id,
                email=DEMO_USER_EMAIL,
                full_name="Demo Admin",
                role=UserRole.ADMIN,
                external_auth_id=f"demo_{user_id}",
                is_active=True,
            )
            session.add(user)
            session.flush()
        print(f"  [+] Created user: demo@pampgroup.com ({user_id})")

    return org_id, user_id


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

def seed_portfolio(session: Session, org_id: uuid.UUID, dry_run: bool) -> uuid.UUID:
    existing = session.execute(
        select(Portfolio).where(
            Portfolio.org_id == org_id,
            Portfolio.name == DEMO_PORTFOLIO_NAME,
            Portfolio.is_deleted == False,  # noqa: E712
        )
    ).scalar_one_or_none()

    if existing:
        print(f"  [OK] Portfolio already exists ({existing.id})")
        return existing.id

    portfolio_id = _uid()
    if not dry_run:
        portfolio = Portfolio(
            id=portfolio_id,
            org_id=org_id,
            name=DEMO_PORTFOLIO_NAME,
            description=(
                "Closed-end fund targeting core and core-plus infrastructure and renewable "
                "energy assets across Europe. SFDR Article 9."
            ),
            strategy=PortfolioStrategy.INCOME,
            fund_type=FundType.CLOSED_END,
            vintage_year=2023,
            target_aum=Decimal("1500000000"),   # €1.5bn
            current_aum=Decimal("1207000000"),  # €1.207bn (3 projects)
            currency="EUR",
            sfdr_classification=SFDRClassification.ARTICLE_9,
            status=PortfolioStatus.INVESTING,
        )
        session.add(portfolio)
        session.flush()
        # Portfolio metrics snapshot
        pm = PortfolioMetrics(
            id=_uid(),
            portfolio_id=portfolio_id,
            irr_gross=Decimal("15.2"),
            irr_net=Decimal("14.5"),
            moic=Decimal("1.18"),
            tvpi=Decimal("1.18"),
            dpi=Decimal("0.05"),
            rvpi=Decimal("1.13"),
            total_invested=Decimal("302100000"),
            total_distributions=Decimal("15000000"),
            total_value=Decimal("390500000"),
            carbon_reduction_tons=Decimal("595000"),
            as_of_date=date(2026, 3, 1),
        )
        session.add(pm)
        session.flush()

    print(f"  [+] Created portfolio: {DEMO_PORTFOLIO_NAME} ({portfolio_id})")
    return portfolio_id


# ---------------------------------------------------------------------------
# Project 1: Helios Solar Portfolio Iberia
# ---------------------------------------------------------------------------

def seed_helios(
    session: Session,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    dry_run: bool,
) -> uuid.UUID:
    existing = session.execute(
        select(Project).where(
            Project.org_id == org_id,
            Project.slug == "prj-2024-0187-helios-solar-iberia",
            Project.is_deleted == False,  # noqa: E712
        )
    ).scalar_one_or_none()

    if existing:
        print(f"  [OK] Helios Solar already exists ({existing.id})")
        return existing.id

    pid = _uid()
    if not dry_run:
        # ── Project ────────────────────────────────────────────────────────────
        proj = Project(
            id=pid,
            org_id=org_id,
            name="Helios Solar Portfolio Iberia",
            slug="prj-2024-0187-helios-solar-iberia",
            description=(
                "Operational ground-mounted solar PV portfolio totalling 420 MWp across "
                "6 plants in southern Spain (Andalucía, Extremadura, Castilla-La Mancha). "
                "Contracted cash-flow profile with merchant upside in Iberian power market. "
                "COD Q2 2024. EU Taxonomy aligned — Climate Mitigation."
            ),
            project_type=ProjectType.SOLAR,
            status=ProjectStatus.OPERATIONAL,
            stage=ProjectStage.OPERATIONAL,
            geography_country="Spain",
            geography_region="Andalucía, Extremadura, Castilla-La Mancha",
            geography_coordinates={"lat": 37.5, "lng": -4.5},
            technology_details={
                "technology": "Bi-facial mono-PERC + single-axis trackers",
                "cod": "2024-06-12",
                "plants": 6,
                "capacity_mwp": 420,
                "annual_p50_gwh": 768.5,
                "annual_p90_gwh": 695.0,
                "degradation_pct_pa": 0.45,
                "availability_target_pct": 98.0,
                "ppa_contracted_pct": 56,
                "sponsor": "Solaris Ibérica Renovables S.L.",
                "spv": "Helios Solar HoldCo S.à r.l. (Luxembourg)",
                "deal_team_lead": "María González",
                "credit_analyst": "Jens Müller",
            },
            capacity_mw=Decimal("420"),
            total_investment_required=Decimal("312000000"),
            currency="EUR",
            target_close_date=date(2024, 8, 15),
            is_published=True,
            published_at=datetime(2024, 8, 15, tzinfo=timezone.utc),
        )
        session.add(proj)
        session.flush()

        # ── Milestones ─────────────────────────────────────────────────────────
        milestones = [
            ("Investment Committee Approval", date(2024, 7, 31), date(2024, 7, 22), MilestoneStatus.COMPLETED, 100),
            ("Financial Close", date(2024, 8, 15), date(2024, 8, 15), MilestoneStatus.COMPLETED, 100),
            ("COD — All Plants", date(2024, 6, 30), date(2024, 6, 12), MilestoneStatus.COMPLETED, 100),
            ("Q4 2025 Monitoring Report", date(2026, 1, 31), date(2026, 1, 28), MilestoneStatus.COMPLETED, 100),
            ("Q1 2026 Monitoring Report", date(2026, 4, 15), None, MilestoneStatus.NOT_STARTED, 0),
            ("PPA-2 Renewal Strategy", date(2026, 6, 30), None, MilestoneStatus.IN_PROGRESS, 25),
            ("SFDR Periodic Disclosure", date(2026, 6, 30), None, MilestoneStatus.NOT_STARTED, 0),
        ]
        for i, (name, target, completed, status, pct) in enumerate(milestones):
            m = ProjectMilestone(
                id=_uid(), project_id=pid,
                name=name, description="",
                target_date=target,
                completed_date=completed,
                status=status, completion_pct=pct, order_index=i,
            )
            session.add(m)

        # ── Budget Items ───────────────────────────────────────────────────────
        budget = [
            ("EPC / Construction", "6 plants construction and installation", Decimal("270000000"), Decimal("270000000"), BudgetItemStatus.PAID),
            ("Development & Advisory", "Pre-construction development costs", Decimal("15000000"), Decimal("14200000"), BudgetItemStatus.PAID),
            ("Financing Costs", "Arrangement fees, hedging, legal", Decimal("12000000"), Decimal("11800000"), BudgetItemStatus.PAID),
            ("Debt Reserve Account", "6-month DSRA funded at financial close", Decimal("13900000"), Decimal("13900000"), BudgetItemStatus.PAID),
            ("Working Capital", "O&M reserves and initial working capital", Decimal("1100000"), Decimal("1000000"), BudgetItemStatus.PAID),
        ]
        for cat, desc, est, act, status in budget:
            session.add(ProjectBudgetItem(
                id=_uid(), project_id=pid,
                category=cat, description=desc,
                estimated_amount=est, actual_amount=act,
                currency="EUR", status=status,
            ))

        # ── Signal Score ───────────────────────────────────────────────────────
        session.add(SignalScore(
            id=_uid(), project_id=pid,
            overall_score=83,
            project_viability_score=85,
            financial_planning_score=88,
            risk_assessment_score=75,
            team_strength_score=80,
            esg_score=90,
            market_opportunity_score=75,
            model_used="demo-seed",
            version=1,
            calculated_at=_now(),
        ))

        # ── Risk Assessments ───────────────────────────────────────────────────
        risks = [
            (RiskType.MARKET, RiskSeverity.HIGH, RiskProbability.POSSIBLE,
             "Merchant pool price drops below €40/MWh",
             "56% contracted; hedging strategy for yr 2–3 merchant tail", RiskAssessmentStatus.MONITORING),
            (RiskType.CLIMATE, RiskSeverity.MEDIUM, RiskProbability.UNLIKELY,
             "Irradiance below P90 for >2 consecutive years",
             "DNV-verified P50/P90 reports; bifacial gain buffer", RiskAssessmentStatus.MONITORING),
            (RiskType.REGULATORY, RiskSeverity.MEDIUM, RiskProbability.POSSIBLE,
             "Retroactive tax on windfall profits (Spain)",
             "Portfolio diversification across 3 autonomous communities", RiskAssessmentStatus.MONITORING),
            (RiskType.OPERATIONAL, RiskSeverity.MEDIUM, RiskProbability.UNLIKELY,
             "Inverter failure rate above warranty curve",
             "Huawei SUN2000 5-yr warranty + extended service agreement", RiskAssessmentStatus.MONITORING),
            (RiskType.COUNTERPARTY, RiskSeverity.HIGH, RiskProbability.UNLIKELY,
             "PPA off-taker downgrade below investment grade",
             "Step-in rights; replacement PPA trigger at BB+", RiskAssessmentStatus.MONITORING),
        ]
        for rt, sev, prob, desc, mitigation, status in risks:
            session.add(RiskAssessment(
                id=_uid(), entity_type=RiskEntityType.PROJECT, entity_id=pid,
                org_id=org_id, risk_type=rt, severity=sev, probability=prob,
                description=desc, mitigation=mitigation, status=status,
                assessed_by=user_id,
                overall_risk_score=Decimal("35" if sev == RiskSeverity.LOW else ("55" if sev == RiskSeverity.MEDIUM else "72")),
                market_risk_score=Decimal("55" if rt == RiskType.MARKET else "30"),
                regulatory_risk_score=Decimal("50" if rt == RiskType.REGULATORY else "25"),
            ))

        # ── Covenants ──────────────────────────────────────────────────────────
        covenants = [
            ("Minimum DSCR", "financial_ratio", "DSCR", 1.15, ">=", 1.42, "compliant"),
            ("Distribution Lock-Up DSCR", "financial_ratio", "DSCR_lockup", 1.20, ">=", 1.42, "compliant"),
            ("Debt Reserve Account", "operational_kpi", "DSRA_funded_months", 6.0, ">=", 6.0, "compliant"),
            ("O&M Reserve", "operational_kpi", "OM_reserve_eur", 2000000, ">=", 2500000, "compliant"),
            ("Quarterly IC Reporting", "reporting_deadline", "quarterly_ic_report_days", 45, "<=", 30, "compliant"),
        ]
        for name, ctype, metric, threshold, comparison, current, status in covenants:
            session.add(Covenant(
                id=_uid(), org_id=org_id, project_id=pid,
                name=name, covenant_type=ctype,
                metric_name=metric, threshold_value=threshold,
                comparison=comparison, current_value=current,
                status=status, check_frequency="quarterly",
                last_checked_at=datetime(2026, 1, 28, tzinfo=timezone.utc),
            ))

        # ── KPI Actuals & Targets ──────────────────────────────────────────────
        kpi_data = [
            # (kpi_name, unit, period, actual, target)
            ("DSCR", "ratio", "2025-Q4", 1.42, 1.15),
            ("Revenue_EUR", "EUR", "2025-Q4", 12050000, 12000000),
            ("OPEX_EUR", "EUR", "2025-Q4", 2225000, 2225000),
            ("Annual_Yield_GWh", "GWh", "2025", 762, 768.5),
            ("Availability_Pct", "pct", "2025", 98.4, 98.0),
            ("DSCR", "ratio", "2025-Q3", 1.44, 1.15),
            ("DSCR", "ratio", "2025-Q2", 1.38, 1.15),
            ("DSCR", "ratio", "2025-Q1", 1.41, 1.15),
        ]
        for kpi, unit, period, actual, target in kpi_data:
            session.add(KPIActual(
                id=_uid(), org_id=org_id, project_id=pid,
                kpi_name=kpi, value=actual, unit=unit,
                period=period,
                period_type="annual" if len(period) == 4 else "quarterly",
                source="manual",
            ))
            # Only add targets for Q4
            if "Q4" in period or len(period) == 4:
                session.add(KPITarget(
                    id=_uid(), org_id=org_id, project_id=pid,
                    kpi_name=kpi, target_value=target, period=period,
                    tolerance_pct=0.05, source="investment_memo",
                ))

        # ── ESG Metrics ────────────────────────────────────────────────────────
        session.add(ESGMetrics(
            id=_uid(), project_id=pid, org_id=org_id, period="2025",
            carbon_footprint_tco2e=0,
            carbon_avoided_tco2e=310000,
            renewable_energy_mwh=762000,
            water_usage_cubic_m=800,
            jobs_created=180,
            jobs_supported=320,
            local_procurement_pct=42,
            community_investment_eur=0,
            health_safety_incidents=0,
            board_independence_pct=80,
            audit_completed=True,
            esg_reporting_standard="SFDR",
            taxonomy_eligible=True,
            taxonomy_aligned=True,
            taxonomy_activity="Solar energy generation",
            sfdr_article=9,
            sdg_contributions={
                "7": {"name": "Affordable Clean Energy", "contribution_level": "high"},
                "13": {"name": "Climate Action", "contribution_level": "high"},
                "15": {"name": "Life on Land", "contribution_level": "medium"},
            },
            esg_narrative=(
                "Helios Solar Portfolio Iberia generated approximately 762 GWh of clean electricity in 2025, "
                "displacing an estimated 310,000 tCO₂e. All plants are EU Taxonomy-aligned under Climate Mitigation. "
                "SFDR Article 9. Biodiversity corridor restoration plan in progress at Almería site."
            ),
        ))

        # ── Portfolio Holding ──────────────────────────────────────────────────
        session.add(PortfolioHolding(
            id=_uid(), portfolio_id=portfolio_id, project_id=pid,
            asset_name="Helios Solar Portfolio Iberia",
            asset_type=AssetType.EQUITY,
            investment_date=date(2024, 8, 15),
            investment_amount=Decimal("93600000"),
            current_value=Decimal("142800000"),
            ownership_pct=Decimal("100"),
            currency="EUR",
            status=HoldingStatus.ACTIVE,
            notes="Operational solar portfolio. 56% contracted (Iberdrola/Endesa PPAs). Equity IRR 13.2%.",
        ))

        # ── Documents ──────────────────────────────────────────────────────────
        folder_id = _uid()
        session.add(DocumentFolder(
            id=folder_id, org_id=org_id, project_id=pid,
            name="Helios Solar — Data Room",
        ))
        docs = [
            ("Investment Committee Memo", DocumentClassification.PRESENTATION, "IC Pack", "2024-07-22"),
            ("Independent Technical Assessment (DNV)", DocumentClassification.TECHNICAL_STUDY, "Due Diligence", "2024-06-01"),
            ("Yield Assessment Report (DNV) P50/P90", DocumentClassification.TECHNICAL_STUDY, "Due Diligence", "2024-05-15"),
            ("PPA-1 Executed Agreement (Iberdrola)", DocumentClassification.LEGAL_AGREEMENT, "Legal", "2024-08-10"),
            ("PPA-2 Executed Agreement (Endesa)", DocumentClassification.LEGAL_AGREEMENT, "Legal", "2024-08-10"),
            ("Senior Facility Agreement", DocumentClassification.LEGAL_AGREEMENT, "Legal", "2024-08-14"),
            ("Environmental Impact Assessment", DocumentClassification.ENVIRONMENTAL_REPORT, "Permit", "2023-11-20"),
            ("Insurance Certificate (Allianz)", DocumentClassification.INSURANCE, "Insurance", "2025-01-15"),
            ("Q4 2025 Monitoring Report", DocumentClassification.FINANCIAL_STATEMENT, "Monitoring", "2026-01-28"),
            ("Annual Valuation Report 2025", DocumentClassification.VALUATION, "Valuation", "2026-02-15"),
            ("EU Taxonomy Assessment", DocumentClassification.ENVIRONMENTAL_REPORT, "ESG / Regulatory", "2024-08-01"),
        ]
        for doc_name, classification, doc_type, doc_date in docs:
            session.add(Document(
                id=_uid(), org_id=org_id, project_id=pid,
                folder_id=folder_id,
                name=doc_name,
                file_type="pdf", mime_type="application/pdf",
                s3_key=f"demo/helios/{doc_name.lower().replace(' ', '-').replace('(', '').replace(')', '')}.pdf",
                s3_bucket="scr-staging-documents",
                file_size_bytes=1024 * 1024 * (2 + hash(doc_name) % 8),  # 2–10 MB
                version=1, status=DocumentStatus.READY,
                classification=classification,
                metadata_={
                    "doc_type": doc_type,
                    "doc_date": doc_date,
                    "project_id": "PRJ-2024-0187",
                    "confidentiality": "Confidential" if "Agreement" in doc_name or "Memo" in doc_name else "Internal",
                },
                uploaded_by=user_id,
                checksum_sha256=f"demo-sha256-helios-{hash(doc_name) & 0xffffffff:08x}",
                watermark_enabled=True,
            ))

    print(f"  [+] Created Helios Solar Portfolio Iberia ({pid})")
    return pid


# ---------------------------------------------------------------------------
# Project 2: Nordvik Wind Farm II
# ---------------------------------------------------------------------------

def seed_nordvik(
    session: Session,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    dry_run: bool,
) -> uuid.UUID:
    existing = session.execute(
        select(Project).where(
            Project.org_id == org_id,
            Project.slug == "prj-2025-0042-nordvik-wind-ii",
            Project.is_deleted == False,  # noqa: E712
        )
    ).scalar_one_or_none()

    if existing:
        print(f"  [OK] Nordvik Wind II already exists ({existing.id})")
        return existing.id

    pid = _uid()
    if not dry_run:
        proj = Project(
            id=pid,
            org_id=org_id,
            name="Nordvik Wind Farm II",
            slug="prj-2025-0042-nordvik-wind-ii",
            description=(
                "Late-stage construction onshore wind farm in Trøndelag, Norway. "
                "35 × Vestas V162-6.0 MW turbines, total 210 MW. "
                "Expected COD Q4 2026. Corporate PPA with Norsk Hydro (12 yr, NOK 310/MWh). "
                "EU Taxonomy aligned — Climate Mitigation. SFDR Article 9."
            ),
            project_type=ProjectType.WIND,
            status=ProjectStatus.CONSTRUCTION,
            stage=ProjectStage.UNDER_CONSTRUCTION,
            geography_country="Norway",
            geography_region="Trøndelag",
            geography_coordinates={"lat": 63.4, "lng": 10.4},
            technology_details={
                "turbine_model": "Vestas V162-6.0 MW",
                "turbine_count": 35,
                "rotor_diameter_m": 162,
                "hub_height_m": 166,
                "ncf_p50_pct": 38.5,
                "ncf_p90_pct": 34.2,
                "aep_p50_gwh": 708,
                "aep_p90_gwh": 629,
                "wind_speed_hub_ms": 8.4,
                "construction_progress_pct": 85,
                "turbines_erected": 28,
                "expected_cod": "2026-11-15",
                "sponsor": "Nordvik Kraft AS",
                "spv": "Nordvik Wind II AS",
                "deal_team_lead": "Erik Lindström",
                "credit_analyst": "Sophie van den Berg",
            },
            capacity_mw=Decimal("210"),
            total_investment_required=Decimal("410000000"),  # ~€410M
            currency="EUR",
            target_close_date=date(2026, 11, 15),
            is_published=True,
            published_at=datetime(2025, 3, 20, tzinfo=timezone.utc),
        )
        session.add(proj)
        session.flush()

        # ── Milestones ─────────────────────────────────────────────────────────
        milestones = [
            ("Financial Close", date(2025, 3, 20), date(2025, 3, 20), MilestoneStatus.COMPLETED, 100),
            ("Site Access Roads", date(2025, 4, 30), date(2025, 5, 8), MilestoneStatus.COMPLETED, 100),
            ("Foundation Pours (35/35)", date(2025, 9, 30), date(2025, 10, 12), MilestoneStatus.COMPLETED, 100),
            ("Turbine Deliveries Start", date(2025, 10, 15), date(2025, 10, 15), MilestoneStatus.COMPLETED, 100),
            ("Turbine Erection (35/35)", date(2026, 6, 30), None, MilestoneStatus.IN_PROGRESS, 80),
            ("Internal Grid & Substation", date(2026, 7, 31), None, MilestoneStatus.IN_PROGRESS, 65),
            ("Commissioning & Testing", date(2026, 9, 30), None, MilestoneStatus.NOT_STARTED, 0),
            ("COD / Grid Energisation", date(2026, 11, 15), None, MilestoneStatus.NOT_STARTED, 0),
            ("Defects Liability Period End", date(2028, 11, 15), None, MilestoneStatus.NOT_STARTED, 0),
        ]
        for i, (name, target, completed, status, pct) in enumerate(milestones):
            session.add(ProjectMilestone(
                id=_uid(), project_id=pid,
                name=name, description="",
                target_date=target, completed_date=completed,
                status=status, completion_pct=pct, order_index=i,
            ))

        # ── Budget Items ───────────────────────────────────────────────────────
        total_nok = Decimal("4680000000")  # NOK 4.68bn
        budget = [
            ("EPC Contract (Vestas/Skanska JV)", "Fixed-price EPC for all 35 turbines", Decimal("3510000000"), Decimal("2857000000"), BudgetItemStatus.COMMITTED),
            ("Development & Advisory", "Pre-construction development, permits, advisory", Decimal("280000000"), Decimal("280000000"), BudgetItemStatus.PAID),
            ("Grid Connection & Substation", "132 kV substation and grid connection", Decimal("540000000"), Decimal("350000000"), BudgetItemStatus.COMMITTED),
            ("Owner's Costs & Contingency", "Insurance, permits, 7.5% contingency (NOK 351M)", Decimal("350000000"), Decimal("323000000"), BudgetItemStatus.COMMITTED),
        ]
        for cat, desc, est, act, status in budget:
            session.add(ProjectBudgetItem(
                id=_uid(), project_id=pid,
                category=cat, description=desc,
                estimated_amount=est, actual_amount=act,
                currency="NOK", status=status,
            ))

        # ── Signal Score ───────────────────────────────────────────────────────
        session.add(SignalScore(
            id=_uid(), project_id=pid,
            overall_score=78,
            project_viability_score=82,
            financial_planning_score=80,
            risk_assessment_score=70,
            team_strength_score=78,
            esg_score=88,
            market_opportunity_score=70,
            model_used="demo-seed",
            version=1,
            calculated_at=_now(),
        ))

        # ── Risk Assessments ───────────────────────────────────────────────────
        risks = [
            (RiskType.OPERATIONAL, RiskSeverity.MEDIUM, RiskProbability.LIKELY,
             "Winter weather delays (Nov–Feb construction window)",
             "Schedule buffer; Arctic-rated equipment; heated concrete pours", RiskAssessmentStatus.MONITORING),
            (RiskType.OPERATIONAL, RiskSeverity.HIGH, RiskProbability.UNLIKELY,
             "Vestas nacelle delivery delay — remaining 7 turbines",
             "28/35 delivered; remaining 7 in transit (ETA Apr 2026)", RiskAssessmentStatus.MONITORING),
            (RiskType.MARKET, RiskSeverity.MEDIUM, RiskProbability.POSSIBLE,
             "NOK depreciation vs EUR (sponsor FX exposure)",
             "NOK-denominated debt; natural hedge on NOK revenues", RiskAssessmentStatus.MONITORING),
            (RiskType.REGULATORY, RiskSeverity.MEDIUM, RiskProbability.UNLIKELY,
             "ElCert scheme early phase-out risk",
             "PPA floor price covers debt service without ElCerts", RiskAssessmentStatus.MONITORING),
            (RiskType.COUNTERPARTY, RiskSeverity.HIGH, RiskProbability.UNLIKELY,
             "Norsk Hydro credit deterioration",
             "Cross-default clause; Norsk Hydro parent guarantee", RiskAssessmentStatus.MONITORING),
        ]
        for rt, sev, prob, desc, mitigation, status in risks:
            session.add(RiskAssessment(
                id=_uid(), entity_type=RiskEntityType.PROJECT, entity_id=pid,
                org_id=org_id, risk_type=rt, severity=sev, probability=prob,
                description=desc, mitigation=mitigation, status=status,
                assessed_by=user_id,
                overall_risk_score=Decimal("42" if sev == RiskSeverity.MEDIUM else "65"),
            ))

        # ── Covenants ──────────────────────────────────────────────────────────
        covenants = [
            ("Construction Budget (EPC)", "operational_kpi", "construction_budget_nok_spent_pct", 100, "<=", 81.4, "compliant"),
            ("Contingency Drawdown Reporting", "operational_kpi", "contingency_used_pct", 50, "<=", 22, "compliant"),
            ("Monthly Construction Milestone Certificate", "reporting_deadline", "milestone_cert_days", 30, "<=", 14, "compliant"),
            ("Equity Contribution Schedule", "financial_ratio", "equity_committed_pct", 100, "==", 100, "compliant"),
        ]
        for name, ctype, metric, threshold, comparison, current, status in covenants:
            session.add(Covenant(
                id=_uid(), org_id=org_id, project_id=pid,
                name=name, covenant_type=ctype,
                metric_name=metric, threshold_value=threshold,
                comparison=comparison, current_value=current,
                status=status, check_frequency="monthly",
                last_checked_at=datetime(2026, 2, 15, tzinfo=timezone.utc),
            ))

        # ── KPI Actuals ─────────────────────────────────────────────────────────
        kpi_data = [
            ("Construction_Progress_Pct", "pct", "2026-02", 81.4, 85.0),
            ("Turbines_Erected_Count", "count", "2026-02", 28, 30),
            ("Budget_Spent_NOK_M", "NOK_M", "2026-02", 3810, 3800),
            ("Contingency_Used_NOK_M", "NOK_M", "2026-02", 77, 0),
        ]
        for kpi, unit, period, actual, target in kpi_data:
            session.add(KPIActual(
                id=_uid(), org_id=org_id, project_id=pid,
                kpi_name=kpi, value=actual, unit=unit,
                period=period, period_type="monthly", source="manual",
            ))
            session.add(KPITarget(
                id=_uid(), org_id=org_id, project_id=pid,
                kpi_name=kpi, target_value=target, period=period,
                tolerance_pct=0.05, source="business_plan",
            ))

        # ── ESG Metrics ────────────────────────────────────────────────────────
        session.add(ESGMetrics(
            id=_uid(), project_id=pid, org_id=org_id, period="2025",
            carbon_footprint_tco2e=4200,  # construction phase
            carbon_avoided_tco2e=0,       # not yet operational
            renewable_energy_mwh=0,
            jobs_created=320,
            jobs_supported=180,
            local_procurement_pct=38,
            community_investment_eur=1050000,  # NOK 12M community fund
            health_safety_incidents=1,
            board_independence_pct=60,
            audit_completed=False,
            esg_reporting_standard="SFDR",
            taxonomy_eligible=True,
            taxonomy_aligned=True,
            taxonomy_activity="Wind energy generation",
            sfdr_article=9,
            sdg_contributions={
                "7": {"name": "Affordable Clean Energy", "contribution_level": "high"},
                "13": {"name": "Climate Action", "contribution_level": "high"},
                "15": {"name": "Life on Land", "contribution_level": "medium"},
                "8": {"name": "Decent Work and Economic Growth", "contribution_level": "medium"},
            },
            esg_narrative=(
                "Nordvik Wind Farm II is currently 85% complete with 28 of 35 Vestas turbines erected. "
                "COD targeted for Q4 2026. Once operational, the project will generate ~708 GWh/year, "
                "displacing approximately 285,000 tCO₂e annually vs the Nordic grid average. "
                "A Sámi co-existence agreement is in place, with seasonal construction halts for reindeer migration."
            ),
        ))

        # ── Portfolio Holding ──────────────────────────────────────────────────
        session.add(PortfolioHolding(
            id=_uid(), portfolio_id=portfolio_id, project_id=pid,
            asset_name="Nordvik Wind Farm II",
            asset_type=AssetType.EQUITY,
            investment_date=date(2025, 3, 20),
            investment_amount=Decimal("82000000"),   # equity tranche drawn to date
            current_value=Decimal("89500000"),       # at cost + accrued development margin
            ownership_pct=Decimal("100"),
            currency="EUR",
            status=HoldingStatus.ACTIVE,
            notes="Construction phase. Expected COD Q4 2026. Projected equity IRR 14.8%.",
        ))

        # ── Documents ──────────────────────────────────────────────────────────
        folder_id = _uid()
        session.add(DocumentFolder(
            id=folder_id, org_id=org_id, project_id=pid,
            name="Nordvik Wind II — Data Room",
        ))
        docs = [
            ("Investment Committee Memo", DocumentClassification.PRESENTATION, "IC Pack", "2025-02-28"),
            ("Independent Engineer Report (DNV)", DocumentClassification.TECHNICAL_STUDY, "Due Diligence", "2025-01-20"),
            ("Wind Resource Assessment (Vortex/WindSim)", DocumentClassification.TECHNICAL_STUDY, "Due Diligence", "2024-11-15"),
            ("EPC Contract (Vestas/Skanska JV)", DocumentClassification.LEGAL_AGREEMENT, "Legal", "2025-03-18"),
            ("Corporate PPA (Norsk Hydro ASA)", DocumentClassification.LEGAL_AGREEMENT, "Legal", "2025-03-15"),
            ("Senior Facility Agreement (DNB/Nordea)", DocumentClassification.LEGAL_AGREEMENT, "Legal", "2025-03-20"),
            ("Mezzanine Facility Agreement", DocumentClassification.LEGAL_AGREEMENT, "Legal", "2025-03-20"),
            ("NVE Concession & Environmental Permit", DocumentClassification.PERMIT, "Permit", "2023-09-10"),
            ("Sámi Council Co-existence Agreement", DocumentClassification.ENVIRONMENTAL_REPORT, "ESG / Social", "2024-06-22"),
            ("Monthly Construction Report #11", DocumentClassification.FINANCIAL_STATEMENT, "Monitoring", "2026-02-15"),
            ("Geotechnical Investigation Report", DocumentClassification.TECHNICAL_STUDY, "Technical", "2024-08-30"),
        ]
        for doc_name, classification, doc_type, doc_date in docs:
            session.add(Document(
                id=_uid(), org_id=org_id, project_id=pid,
                folder_id=folder_id,
                name=doc_name,
                file_type="pdf", mime_type="application/pdf",
                s3_key=f"demo/nordvik/{doc_name.lower().replace(' ', '-').replace('(', '').replace(')', '').replace('/', '-')}.pdf",
                s3_bucket="scr-staging-documents",
                file_size_bytes=1024 * 1024 * (2 + hash(doc_name) % 6),
                version=1, status=DocumentStatus.READY,
                classification=classification,
                metadata_={"doc_type": doc_type, "doc_date": doc_date, "project_id": "PRJ-2025-0042"},
                uploaded_by=user_id,
                checksum_sha256=f"demo-sha256-nordvik-{hash(doc_name) & 0xffffffff:08x}",
                watermark_enabled=True,
            ))

    print(f"  [+] Created Nordvik Wind Farm II ({pid})")
    return pid


# ---------------------------------------------------------------------------
# Project 3: Adriatic Infrastructure Holdings
# ---------------------------------------------------------------------------

def seed_adriatic(
    session: Session,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    dry_run: bool,
) -> uuid.UUID:
    existing = session.execute(
        select(Project).where(
            Project.org_id == org_id,
            Project.slug == "prj-2023-0311-adriatic-infrastructure",
            Project.is_deleted == False,  # noqa: E712
        )
    ).scalar_one_or_none()

    if existing:
        print(f"  [OK] Adriatic Infrastructure already exists ({existing.id})")
        return existing.id

    pid = _uid()
    if not dry_run:
        proj = Project(
            id=pid,
            org_id=org_id,
            name="Adriatic Infrastructure Holdings",
            slug="prj-2023-0311-adriatic-infrastructure",
            description=(
                "Operational core infrastructure portfolio comprising 3 concessions in Croatia and Slovenia: "
                "Istria Motorway A-9 extension (42km toll road), Primorska Voda water utility "
                "(Rijeka metro, 185,000 population), and Ljubljana District Energy (heating/cooling). "
                "⚠ WATCHLIST: Croatian water tariff regulatory review 2028. "
                "SFDR Article 8 with environmental characteristics."
            ),
            project_type=ProjectType.INFRASTRUCTURE,
            status=ProjectStatus.OPERATIONAL,
            stage=ProjectStage.OPERATIONAL,
            geography_country="Croatia / Slovenia",
            geography_region="Istria (HR), Rijeka (HR), Ljubljana (SI)",
            geography_coordinates={"lat": 45.3, "lng": 14.6},
            technology_details={
                "sub_assets": [
                    {"name": "Istria Motorway A-9", "type": "toll_road", "concession_end": "2048", "annual_revenue_eur": 38500000},
                    {"name": "Primorska Voda", "type": "water_utility", "concession_end": "2051", "annual_revenue_eur": 22000000, "watchlist": True},
                    {"name": "Ljubljana District Energy", "type": "district_heating", "concession_end": "2045", "annual_revenue_eur": 18500000},
                ],
                "portfolio_ev_eur": 485000000,
                "blended_ltv_pct": 64,
                "dividend_yield_yr1_pct": 6.8,
                "sponsor": "Adriatic Infra Partners d.o.o. (Zagreb)",
                "spv": "Adriatic Infrastructure HoldCo Ltd (Jersey)",
                "deal_team_lead": "Luka Petrović",
                "credit_analyst": "Anna Kowalski",
                "watchlist_flag": "Primorska Voda — Croatian water tariff review 2028",
            },
            capacity_mw=None,
            total_investment_required=Decimal("485000000"),
            currency="EUR",
            target_close_date=date(2023, 12, 15),
            is_published=True,
            published_at=datetime(2023, 12, 15, tzinfo=timezone.utc),
        )
        session.add(proj)
        session.flush()

        # ── Milestones ─────────────────────────────────────────────────────────
        milestones = [
            ("Investment Committee Approval", date(2023, 11, 30), date(2023, 11, 20), MilestoneStatus.COMPLETED, 100),
            ("Financial Close & Acquisition", date(2023, 12, 15), date(2023, 12, 15), MilestoneStatus.COMPLETED, 100),
            ("Year 1 Concession Compliance Certification", date(2024, 12, 31), date(2024, 12, 20), MilestoneStatus.COMPLETED, 100),
            ("Year 2 Concession Compliance Certification", date(2025, 12, 31), date(2025, 12, 22), MilestoneStatus.COMPLETED, 100),
            ("Q4 2025 Monitoring Report", date(2026, 2, 28), date(2026, 2, 10), MilestoneStatus.COMPLETED, 100),
            ("NRW Reduction Programme Mid-Review", date(2026, 6, 30), None, MilestoneStatus.IN_PROGRESS, 30),
            ("District Energy Heat Pump Procurement", date(2026, 9, 1), None, MilestoneStatus.IN_PROGRESS, 40),
            ("⚠ Tariff Review Pre-filing Strategy (Primorska Voda)", date(2027, 6, 30), None, MilestoneStatus.NOT_STARTED, 5),
        ]
        for i, (name, target, completed, status, pct) in enumerate(milestones):
            session.add(ProjectMilestone(
                id=_uid(), project_id=pid,
                name=name, description="",
                target_date=target, completed_date=completed,
                status=status, completion_pct=pct, order_index=i,
            ))

        # ── Budget Items ───────────────────────────────────────────────────────
        budget = [
            ("Acquisition (Istria Motorway)", "EV allocation at acquisition", Decimal("205000000"), Decimal("205000000"), BudgetItemStatus.PAID),
            ("Acquisition (Primorska Voda)", "EV allocation at acquisition", Decimal("140000000"), Decimal("140000000"), BudgetItemStatus.PAID),
            ("Acquisition (Ljubljana District Energy)", "EV allocation at acquisition", Decimal("140000000"), Decimal("140000000"), BudgetItemStatus.PAID),
            ("Advisory & Transaction Costs", "PwC DD, legal, advisory fees", Decimal("12000000"), Decimal("11500000"), BudgetItemStatus.PAID),
            ("Water CapEx Programme (5-yr)", "NRW reduction, network renewal", Decimal("45000000"), Decimal("8000000"), BudgetItemStatus.COMMITTED),
            ("District Energy — Heat Pump Investment", "Geothermal & heat pump integration 2027–2029", Decimal("32000000"), Decimal("0"), BudgetItemStatus.PLANNED),
        ]
        for cat, desc, est, act, status in budget:
            session.add(ProjectBudgetItem(
                id=_uid(), project_id=pid,
                category=cat, description=desc,
                estimated_amount=est, actual_amount=act,
                currency="EUR", status=status,
            ))

        # ── Signal Score ───────────────────────────────────────────────────────
        session.add(SignalScore(
            id=_uid(), project_id=pid,
            overall_score=71,
            project_viability_score=78,
            financial_planning_score=74,
            risk_assessment_score=60,   # Watchlist item
            team_strength_score=75,
            esg_score=72,
            market_opportunity_score=65,
            model_used="demo-seed",
            version=1,
            calculated_at=_now(),
        ))

        # ── Risk Assessments ───────────────────────────────────────────────────
        risks = [
            # CRITICAL — Watchlist
            (RiskType.REGULATORY, RiskSeverity.CRITICAL, RiskProbability.LIKELY,
             "[WATCHLIST] Croatian water tariff review 2028 — potential allowed return compression to <5% real WACC",
             "Engaged regulatory advisor; pre-filing strategy Q3 2027; Mott MacDonald RAB re-valuation commissioned", RiskAssessmentStatus.MONITORING),
            (RiskType.MARKET, RiskSeverity.MEDIUM, RiskProbability.POSSIBLE,
             "Istria motorway traffic below base case (recession / tourism decline)",
             "Summer traffic buffer (+45%); 80% CPI toll escalation; 1.2% downside AADT growth modelled", RiskAssessmentStatus.MONITORING),
            (RiskType.OPERATIONAL, RiskSeverity.MEDIUM, RiskProbability.POSSIBLE,
             "Non-revenue water (NRW) reduction programme behind schedule (target 34%→25% by 2030)",
             "Dedicated PMO; milestone-linked contractor payments; current: 34% vs 33% target", RiskAssessmentStatus.MONITORING),
            (RiskType.MARKET, RiskSeverity.HIGH, RiskProbability.POSSIBLE,
             "Natural gas price spike impacts Ljubljana District Energy margins",
             "Biomass switching capacity (30%); 70% pass-through in tariff structure", RiskAssessmentStatus.MONITORING),
            (RiskType.OPERATIONAL, RiskSeverity.MEDIUM, RiskProbability.POSSIBLE,
             "District energy decarbonisation CapEx overrun",
             "Fixed-price heat pump contract; €5M contingency earmarked", RiskAssessmentStatus.MONITORING),
        ]
        for rt, sev, prob, desc, mitigation, status in risks:
            session.add(RiskAssessment(
                id=_uid(), entity_type=RiskEntityType.PROJECT, entity_id=pid,
                org_id=org_id, risk_type=rt, severity=sev, probability=prob,
                description=desc, mitigation=mitigation, status=status,
                assessed_by=user_id,
                overall_risk_score=Decimal("82" if sev == RiskSeverity.CRITICAL else ("55" if sev == RiskSeverity.HIGH else "38")),
                regulatory_risk_score=Decimal("82" if rt == RiskType.REGULATORY else "25"),
                market_risk_score=Decimal("55" if rt == RiskType.MARKET else "25"),
            ))

        # ── Covenants ──────────────────────────────────────────────────────────
        covenants = [
            ("Holdco DSCR", "financial_ratio", "DSCR_holdco", 1.10, ">=", 1.38, "compliant"),
            ("Motorway DSCR (ring-fenced)", "financial_ratio", "DSCR_motorway", 1.15, ">=", 1.52, "compliant"),
            ("Water Utility DSCR", "financial_ratio", "DSCR_water", 1.15, ">=", 1.18, "warning"),  # Tight!
            ("District Energy DSCR", "financial_ratio", "DSCR_de", 1.15, ">=", 1.35, "compliant"),
            ("Distribution Lock-Up", "financial_ratio", "DSCR_distribution_lockup", 1.20, ">=", 1.38, "compliant"),
            ("Water NRW Target (2027)", "operational_kpi", "NRW_pct", 30, "<=", 34, "warning"),  # Behind plan!
            ("Concession Compliance — Annual", "reporting_deadline", "concession_cert_annual", 365, "<=", 280, "compliant"),
        ]
        for name, ctype, metric, threshold, comparison, current, status in covenants:
            session.add(Covenant(
                id=_uid(), org_id=org_id, project_id=pid,
                name=name, covenant_type=ctype,
                metric_name=metric, threshold_value=threshold,
                comparison=comparison, current_value=current,
                status=status, check_frequency="quarterly",
                last_checked_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
            ))

        # ── KPI Actuals ─────────────────────────────────────────────────────────
        kpi_data = [
            ("DSCR_holdco", "ratio", "2025-Q4", 1.38, 1.10),
            ("DSCR_water", "ratio", "2025-Q4", 1.18, 1.15),
            ("Revenue_Total_EUR", "EUR", "2025-Q4", 19750000, 19800000),
            ("NRW_Pct", "pct", "2025-Q4", 34.0, 33.0),
            ("AADT_Motorway", "vehicles_day", "2025-Q4", 18400, 18000),
            ("DSCR_holdco", "ratio", "2025-Q3", 1.36, 1.10),
            ("DSCR_holdco", "ratio", "2025-Q2", 1.41, 1.10),
            ("Annual_Revenue_EUR", "EUR", "2025", 79000000, 80000000),
            ("Annual_EBITDA_EUR", "EUR", "2025", 46500000, 47000000),
        ]
        for kpi, unit, period, actual, target in kpi_data:
            session.add(KPIActual(
                id=_uid(), org_id=org_id, project_id=pid,
                kpi_name=kpi, value=actual, unit=unit,
                period=period,
                period_type="annual" if len(period) == 4 else "quarterly",
                source="manual",
            ))
            if "Q4" in period or len(period) == 4:
                session.add(KPITarget(
                    id=_uid(), org_id=org_id, project_id=pid,
                    kpi_name=kpi, target_value=target, period=period,
                    tolerance_pct=0.05, source="investment_memo",
                ))

        # ── ESG Metrics ────────────────────────────────────────────────────────
        session.add(ESGMetrics(
            id=_uid(), project_id=pid, org_id=org_id, period="2025",
            carbon_footprint_tco2e=42000,     # Scope 1+2 (district energy dominant)
            carbon_avoided_tco2e=18000,        # vs fossil alternative
            renewable_energy_mwh=204000,       # biomass 30% + waste heat 15%
            water_usage_cubic_m=15330000,      # utility production 42,000 m³/day
            waste_diverted_tonnes=3200,
            jobs_created=180,
            jobs_supported=2220,
            local_procurement_pct=65,
            community_investment_eur=850000,
            gender_diversity_pct=40,           # 40% female board
            health_safety_incidents=2,
            board_independence_pct=60,
            audit_completed=True,
            esg_reporting_standard="SFDR",
            taxonomy_eligible=True,
            taxonomy_aligned=False,            # Motorway = transitional
            taxonomy_activity="Water supply; District heating; Road infrastructure",
            sfdr_article=8,
            sdg_contributions={
                "6": {"name": "Clean Water and Sanitation", "contribution_level": "high"},
                "7": {"name": "Affordable Clean Energy", "contribution_level": "medium"},
                "9": {"name": "Industry, Innovation and Infrastructure", "contribution_level": "high"},
                "11": {"name": "Sustainable Cities and Communities", "contribution_level": "medium"},
                "13": {"name": "Climate Action", "contribution_level": "medium"},
            },
            esg_narrative=(
                "Adriatic Infrastructure Holdings comprises 3 concession-based assets across Croatia and Slovenia. "
                "The portfolio is SFDR Article 8. The Istria Motorway is in transitional taxonomy assessment; "
                "Primorska Voda and Ljubljana District Energy are taxonomy-eligible. "
                "⚠ Watchlist: Croatian water utility tariff review 2028 poses regulatory risk. "
                "NRW reduction programme at Primorska Voda is behind schedule (34% vs 33% target). "
                "District Energy decarbonisation plan (80% renewable by 2035) is on track."
            ),
        ))

        # ── Portfolio Holding ──────────────────────────────────────────────────
        session.add(PortfolioHolding(
            id=_uid(), portfolio_id=portfolio_id, project_id=pid,
            asset_name="Adriatic Infrastructure Holdings",
            asset_type=AssetType.EQUITY,
            investment_date=date(2023, 12, 15),
            investment_amount=Decimal("126500000"),
            current_value=Decimal("158200000"),
            ownership_pct=Decimal("100"),
            currency="EUR",
            status=HoldingStatus.ACTIVE,
            notes=(
                "3-asset infrastructure portfolio (toll road, water utility, district energy). "
                "⚠ WATCHLIST: Primorska Voda water tariff review 2028. "
                "Blended equity IRR 15.4%. Dividend yield 6.8%."
            ),
        ))

        # ── Documents ──────────────────────────────────────────────────────────
        folder_id = _uid()
        session.add(DocumentFolder(
            id=folder_id, org_id=org_id, project_id=pid,
            name="Adriatic Infra — Data Room",
        ))
        docs = [
            ("Investment Committee Memo", DocumentClassification.PRESENTATION, "IC Pack", "2023-11-20"),
            ("Consolidated Due Diligence Report (PwC)", DocumentClassification.TECHNICAL_STUDY, "Due Diligence", "2023-10-01"),
            ("Traffic Study — Istria Motorway (Steer)", DocumentClassification.TECHNICAL_STUDY, "Due Diligence", "2023-09-15"),
            ("Water Utility Technical Assessment (Mott MacDonald)", DocumentClassification.TECHNICAL_STUDY, "Due Diligence", "2023-09-20"),
            ("District Energy Decarbonisation Plan", DocumentClassification.TECHNICAL_STUDY, "Technical", "2023-10-10"),
            ("Concession Agreement — Istria Motorway", DocumentClassification.LEGAL_AGREEMENT, "Legal", "2012-06-30"),
            ("Concession Agreement — Primorska Voda", DocumentClassification.LEGAL_AGREEMENT, "Legal", "2018-03-15"),
            ("Concession Agreement — Ljubljana District Energy", DocumentClassification.LEGAL_AGREEMENT, "Legal", "2015-09-01"),
            ("Senior Facility Agreement (UniCredit/Erste)", DocumentClassification.LEGAL_AGREEMENT, "Legal", "2023-12-14"),
            ("Q4 2025 Monitoring Report", DocumentClassification.FINANCIAL_STATEMENT, "Monitoring", "2026-02-10"),
            ("Croatian Water Regulatory Framework Analysis", DocumentClassification.ENVIRONMENTAL_REPORT, "Regulatory", "2025-08-15"),
            ("Annual Valuation Report 2025", DocumentClassification.VALUATION, "Valuation", "2026-01-30"),
            ("SFDR Periodic Disclosure 2025", DocumentClassification.ENVIRONMENTAL_REPORT, "ESG / Regulatory", "2026-03-01"),
        ]
        for doc_name, classification, doc_type, doc_date in docs:
            session.add(Document(
                id=_uid(), org_id=org_id, project_id=pid,
                folder_id=folder_id,
                name=doc_name,
                file_type="pdf", mime_type="application/pdf",
                s3_key=f"demo/adriatic/{doc_name.lower().replace(' ', '-').replace('(', '').replace(')', '').replace('/', '-')}.pdf",
                s3_bucket="scr-staging-documents",
                file_size_bytes=1024 * 1024 * (2 + hash(doc_name) % 7),
                version=1, status=DocumentStatus.READY,
                classification=classification,
                metadata_={"doc_type": doc_type, "doc_date": doc_date, "project_id": "PRJ-2023-0311"},
                uploaded_by=user_id,
                checksum_sha256=f"demo-sha256-adriatic-{hash(doc_name) & 0xffffffff:08x}",
                watermark_enabled=True,
            ))

    print(f"  [+] Created Adriatic Infrastructure Holdings ({pid})")
    return pid


# ---------------------------------------------------------------------------
# Wipe
# ---------------------------------------------------------------------------

def wipe_demo_data(session: Session) -> None:
    """Hard-delete all demo data for PAMP org (use in staging only)."""
    org = session.execute(
        select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
    ).scalar_one_or_none()
    if not org:
        print("  [OK] No demo org found — nothing to wipe.")
        return
    # Cascade delete via org_id FK — just delete the org
    session.execute(delete(Organization).where(Organization.id == org.id))
    print(f"  [-] Deleted demo org and all related data for '{DEMO_ORG_SLUG}'")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed SCR demo projects")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without committing")
    parser.add_argument("--wipe", action="store_true", help="Delete demo org and all its data")
    args = parser.parse_args()

    dry_run = args.dry_run
    engine = get_engine()

    print(f"\n{'[DRY RUN] ' if dry_run else ''}SCR Platform — Demo Seed Script")
    print("=" * 60)
    print(f"Database: {settings.DATABASE_URL_SYNC[:50]}...")

    with Session(engine) as session:
        if args.wipe:
            print("\n[WIPE] Removing all demo data...")
            wipe_demo_data(session)
            if not dry_run:
                session.commit()
                print("[WIPE] Done.")
            return

        print("\n[1/6] Organisation & User")
        org_id, user_id = seed_org_and_user(session, dry_run)

        print("\n[2/6] Portfolio")
        portfolio_id = seed_portfolio(session, org_id, dry_run)

        print("\n[3/6] Project 1 — Helios Solar Portfolio Iberia")
        seed_helios(session, org_id, user_id, portfolio_id, dry_run)

        print("\n[4/6] Project 2 — Nordvik Wind Farm II")
        seed_nordvik(session, org_id, user_id, portfolio_id, dry_run)

        print("\n[5/6] Project 3 — Adriatic Infrastructure Holdings")
        seed_adriatic(session, org_id, user_id, portfolio_id, dry_run)

        if not dry_run:
            print("\n[6/6] Committing...")
            session.commit()
            print("\n✓ Demo seed complete!")
        else:
            session.rollback()
            print("\n[DRY RUN] Rolled back — no changes committed.")

    print("\nSummary:")
    print("  • 1 investor organisation (PAMP Infrastructure Partners)")
    print("  • 1 portfolio (PAMP Infrastructure & Energy Fund I, €1.21bn AUM)")
    print("  • 3 projects with full data:")
    print("    1. Helios Solar Portfolio Iberia  — 420 MWp, OPERATIONAL, Art. 9")
    print("    2. Nordvik Wind Farm II           — 210 MW,  CONSTRUCTION, Art. 9")
    print("    3. Adriatic Infrastructure        — 3 concessions, OPERATIONAL, Art. 8")
    print("  • 35+ documents, 21 risks, 18+ covenants, 25+ KPI records")
    print("  • ESG metrics (Art. 8 & 9), signal scores, milestones, budget items")
    print("  • Portfolio holdings with entry cost + current NAV")


if __name__ == "__main__":
    main()
