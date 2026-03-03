#!/usr/bin/env python3
"""Master demo seed script — full data for SCR Platform staging/demo.

Populates ALL platform features for 3 demo projects:
  - Helios Solar Portfolio Iberia (Operational, Solar PV, Spain)
  - Nordvik Wind Farm II (Construction, Onshore Wind, Norway)
  - Adriatic Infrastructure Holdings (Operational, Core Infra, Croatia/Slovenia)

Data sourced from SCR_Demo_Seed_Data_Prompt.md.

Usage (from apps/api directory):
    poetry run python scripts/seed_demo_complete.py
    poetry run python scripts/seed_demo_complete.py --dry-run
    poetry run python scripts/seed_demo_complete.py --wipe-extra  # wipe augmented data only

Idempotent — safe to run multiple times.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

_api_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _api_root not in sys.path:
    sys.path.insert(0, _api_root)

from app.core.config import settings
from app.core.database import Base  # noqa: F401
from app.models.core import Organization, User
from app.models.projects import Project, ProjectMilestone, ProjectBudgetItem, SignalScore
from app.models.investors import (
    Portfolio, PortfolioHolding, PortfolioMetrics, RiskAssessment,
)
from app.models.monitoring import Covenant, KPIActual, KPITarget
from app.models.esg import ESGMetrics
from app.models.dataroom import Document, DocumentFolder
from app.models.pacing import CashflowAssumption, CashflowProjection
from app.models.connectors import DataConnector, OrgConnectorConfig, DataFetchLog
from app.models.external_data import ExternalDataPoint
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
DEMO_ORG_SLUG = "pamp-infra-partners"
DEMO_USER_EMAIL = "demo@pampgroup.com"
DEMO_PORTFOLIO_NAME = "PAMP Infrastructure & Energy Fund I"
REPORTING_DATE = date(2026, 3, 1)


def get_engine():
    sync_url = settings.DATABASE_URL_SYNC
    if "localhost" in sync_url or "127.0.0.1" in sync_url:
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    return create_engine(sync_url, echo=False)


def _uid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Org & User
# ---------------------------------------------------------------------------

def ensure_org_user(session: Session, dry_run: bool) -> tuple[uuid.UUID, uuid.UUID]:
    org = session.execute(
        select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
    ).scalar_one_or_none()

    if org:
        org_id = org.id
        print(f"  [ok] Org: {org.name} ({org_id})")
    else:
        org_id = _uid()
        if not dry_run:
            o = Organization(
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
                    "esg_framework": "EU Taxonomy + SFDR",
                    "fx_rates": {"EUR/USD": 1.0845, "EUR/GBP": 0.8572, "EUR/NOK": 11.42},
                },
            )
            session.add(o)
            session.flush()
        print(f"  [+] Created org ({org_id})")

    user = session.execute(
        select(User).where(User.email == DEMO_USER_EMAIL)
    ).scalar_one_or_none()

    if user:
        user_id = user.id
        print(f"  [ok] User: {user.full_name} ({user_id})")
    else:
        user_id = _uid()
        if not dry_run:
            u = User(
                id=user_id,
                org_id=org_id,
                email=DEMO_USER_EMAIL,
                full_name="Demo Admin",
                role=UserRole.ADMIN,
                external_auth_id=f"demo_{user_id}",
                is_active=True,
                preferences={
                    "onboarding_completed": True,
                    "tour_completed": True,
                    "org_type": "investor",
                },
            )
            session.add(u)
            session.flush()
        print(f"  [+] Created user demo@pampgroup.com ({user_id})")

    return org_id, user_id


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

def ensure_portfolio(session: Session, org_id: uuid.UUID, dry_run: bool) -> uuid.UUID:
    p = session.execute(
        select(Portfolio).where(
            Portfolio.org_id == org_id,
            Portfolio.name == DEMO_PORTFOLIO_NAME,
            Portfolio.is_deleted == False,  # noqa: E712
        )
    ).scalar_one_or_none()

    if p:
        print(f"  [ok] Portfolio ({p.id})")
        return p.id

    pid = _uid()
    if not dry_run:
        portfolio = Portfolio(
            id=pid,
            org_id=org_id,
            name=DEMO_PORTFOLIO_NAME,
            description=(
                "Closed-end fund targeting core and core-plus infrastructure and renewable "
                "energy assets across Europe. SFDR Article 9. Vintage 2023."
            ),
            strategy=PortfolioStrategy.INCOME,
            fund_type=FundType.CLOSED_END,
            vintage_year=2023,
            target_aum=Decimal("1500000000"),
            current_aum=Decimal("1207000000"),
            currency="EUR",
            sfdr_classification=SFDRClassification.ARTICLE_9,
            status=PortfolioStatus.INVESTING,
        )
        session.add(portfolio)
        session.flush()

        pm = PortfolioMetrics(
            id=_uid(),
            portfolio_id=pid,
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
            esg_metrics={
                "sfdr_article_9_pct": 66.7,
                "sfdr_article_8_pct": 33.3,
                "taxonomy_eligible_pct": 78.5,
                "avg_gresb_score": 71.7,
                "total_co2_avoided_tco2e": 595000,
                "total_jobs_created": 2600,
            },
            cash_flows={
                "2023": {"contributions": -126500000, "distributions": 0, "nav": 126500000},
                "2024": {"contributions": -93600000, "distributions": 0, "nav": 246500000},
                "2025": {"contributions": -82000000, "distributions": 15000000, "nav": 390500000},
            },
            as_of_date=REPORTING_DATE,
        )
        session.add(pm)
        session.flush()
    print(f"  [+] Created portfolio + metrics ({pid})")
    return pid


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

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
            "project_id_ref": "PRJ-2024-0187",
            "technology": "Bi-facial mono-PERC + single-axis trackers",
            "asset_life_years": 35,
            "cod": "2024-Q2",
            "acquisition_date": "2024-08-15",
            "sponsor": "Solaris Ibérica Renovables S.L.",
            "spv": "Helios Solar HoldCo S.à r.l. (Luxembourg)",
            "deal_team_lead": "María González (Madrid)",
            "credit_analyst": "Jens Müller (Frankfurt)",
            "availability_target_pct": 98.0,
            "degradation_pa_pct": 0.45,
            "annual_p50_yield_gwh": 768.5,
            "plants": [
                {"name": "Helios Almería I", "location": "Tabernas, Andalucía", "mwp": 85,
                 "cod": "2024-02-10", "p50_gwh": 161.5, "grid": "REE 132 kV"},
                {"name": "Helios Almería II", "location": "Níjar, Andalucía", "mwp": 70,
                 "cod": "2024-03-22", "p50_gwh": 129.5, "grid": "REE 132 kV"},
                {"name": "Helios Badajoz", "location": "Mérida, Extremadura", "mwp": 100,
                 "cod": "2024-04-15", "p50_gwh": 182.0, "grid": "REE 220 kV"},
                {"name": "Helios Ciudad Real", "location": "Puertollano, CLM", "mwp": 65,
                 "cod": "2024-05-02", "p50_gwh": 117.0, "grid": "REE 132 kV"},
                {"name": "Helios Toledo", "location": "Consuegra, CLM", "mwp": 50,
                 "cod": "2024-05-28", "p50_gwh": 88.5, "grid": "REE 66 kV"},
                {"name": "Helios Córdoba", "location": "Lucena, Andalucía", "mwp": 50,
                 "cod": "2024-06-12", "p50_gwh": 90.0, "grid": "REE 66 kV"},
            ],
            "revenue_structure": [
                {"type": "PPA-CfD", "counterparty": "Iberdrola Clientes",
                 "volume_gwh_yr": 280, "tenor_yr": 10, "tenor_end": "2034",
                 "price_eur_mwh": 42.50, "escalation": "CPI-linked (floor 1.5%)",
                 "credit_rating": "BBB+ (S&P)"},
                {"type": "PPA-Fixed", "counterparty": "Endesa Energía",
                 "volume_gwh_yr": 150, "tenor_yr": 7, "tenor_end": "2031",
                 "price_eur_mwh": 47.00, "escalation": "Fixed",
                 "credit_rating": "A- (S&P)"},
                {"type": "Merchant", "counterparty": "OMIE Day-Ahead Pool",
                 "volume_gwh_yr": 338.5, "tenor_yr": None, "tenor_end": "Ongoing",
                 "price_eur_mwh": None, "forward_range": "55-68",
                 "credit_rating": "N/A"},
            ],
            "contracted_pct": 56.0,
            "financial_model": {
                "total_investment_eur_m": 312.0,
                "senior_debt_eur_m": 218.4,
                "equity_eur_m": 93.6,
                "ltv_pct": 70.0,
                "debt_instrument": "Term Loan B — 7yr · Euribor + 175 bps",
                "dscr_p50_yr1": 1.42,
                "dscr_p90": 1.18,
                "min_dscr_covenant": 1.15,
                "llcr": 1.55,
                "project_irr_pct": 9.8,
                "equity_irr_pct": 13.2,
                "wacc_pct": 6.45,
                "npv_eur_m": 47.3,
                "payback_years": 7.4,
                "annual_opex_eur_m": 8.9,
            },
            "debt_schedule": [
                {"year": 2025, "opening_eur_m": 218.4, "repayment": 18.2, "interest": 9.6, "closing": 200.2, "dscr": 1.42},
                {"year": 2026, "opening_eur_m": 200.2, "repayment": 19.8, "interest": 8.8, "closing": 180.4, "dscr": 1.39},
                {"year": 2027, "opening_eur_m": 180.4, "repayment": 21.5, "interest": 7.9, "closing": 158.9, "dscr": 1.36},
                {"year": 2028, "opening_eur_m": 158.9, "repayment": 23.3, "interest": 6.9, "closing": 135.6, "dscr": 1.33},
                {"year": 2029, "opening_eur_m": 135.6, "repayment": 25.2, "interest": 5.9, "closing": 110.4, "dscr": 1.30},
            ],
            "cash_flow_projection": [
                {"year": 2025, "revenue": 48.2, "opex": 8.9, "ebitda": 39.3, "debt_service": 27.8, "cfads": 39.3, "free_cash": 11.5},
                {"year": 2026, "revenue": 49.8, "opex": 9.2, "ebitda": 40.6, "debt_service": 28.6, "cfads": 40.6, "free_cash": 12.0},
                {"year": 2027, "revenue": 51.0, "opex": 9.4, "ebitda": 41.6, "debt_service": 29.4, "cfads": 41.6, "free_cash": 12.2},
                {"year": 2028, "revenue": 52.6, "opex": 9.7, "ebitda": 42.9, "debt_service": 30.2, "cfads": 42.9, "free_cash": 12.7},
                {"year": 2029, "revenue": 54.1, "opex": 10.0, "ebitda": 44.1, "debt_service": 31.1, "cfads": 44.1, "free_cash": 13.0},
            ],
        },
        "current_nav": Decimal("142800000"),
        "equity_invested": Decimal("93600000"),
        "investment_date": date(2024, 8, 15),
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
            "project_id_ref": "PRJ-2025-0042",
            "technology": "Vestas V162-6.0 MW, 166m hub height",
            "turbine_model": "Vestas V162-6.0 MW",
            "turbine_count": 35,
            "rotor_diameter_m": 162,
            "hub_height_m": 166,
            "cut_in_wind_ms": 3.0,
            "rated_wind_ms": 12.0,
            "ncf_p50_pct": 38.5,
            "ncf_p90_pct": 34.2,
            "aep_p50_gwh": 708,
            "aep_p90_gwh": 629,
            "wake_losses_pct": 6.8,
            "grid_losses_pct": 1.2,
            "availability_pct": 97.5,
            "mean_annual_wind_ms": 8.4,
            "site_altitude_m": "450-620",
            "asset_life_years": 30,
            "expected_cod": "2026-Q4",
            "commitment_date": "2025-03-20",
            "sponsor": "Nordvik Kraft AS",
            "spv": "Nordvik Wind II AS (Norway)",
            "deal_team_lead": "Erik Lindström (Stockholm)",
            "credit_analyst": "Sophie van den Berg (Amsterdam)",
            "revenue_structure": [
                {"type": "Corporate PPA", "counterparty": "Norsk Hydro ASA",
                 "volume_gwh_yr": 350, "tenor_yr": 12, "tenor_end": "2038",
                 "price": "NOK 310/MWh (~€27.15)", "escalation": "70% NOR CPI",
                 "credit_rating": "BBB+ (Fitch)"},
                {"type": "Green Certificate (ElCert)", "counterparty": "Svenska Kraftnät",
                 "volume_gwh_yr": 708, "tenor_end": "2035 (phase-out)",
                 "price": "NOK 45/MWh (~€3.94)", "escalation": "Market-linked",
                 "credit_rating": "Sovereign (AAA)"},
                {"type": "Merchant", "counterparty": "Nordpool Day-Ahead",
                 "volume_gwh_yr": 358, "price": "Market", "forward_range": "NOK 380-520",
                 "credit_rating": "N/A"},
            ],
            "contracted_pct": 49.0,
            "financial_model": {
                "total_cost_nok_m": 4680,
                "total_cost_eur_m": 410,
                "senior_debt_nok_m": 3276,
                "mezzanine_nok_m": 468,
                "equity_nok_m": 936,
                "senior_debt_terms": "15yr amort · NIBOR + 210 bps",
                "mezzanine_terms": "Bullet 7yr · 8.5% fixed",
                "dscr_p50_yr1": 1.48,
                "dscr_p90_yr1": 1.22,
                "min_dscr_covenant": 1.20,
                "llcr": 1.62,
                "project_irr_pct": 10.5,
                "equity_irr_pct": 14.8,
                "construction_contingency_pct": 7.5,
                "construction_budget_spent_nok_m": 3810,
                "remaining_capex_to_cod_nok_m": 870,
            },
            "cash_flow_projection": [
                {"year": 2027, "currency": "NOK_M", "revenue": 412, "opex": 62, "ebitda": 350, "sr_debt_service": 248, "mezz_service": 40, "cfads": 350, "free_cash": 62},
                {"year": 2028, "currency": "NOK_M", "revenue": 428, "opex": 64, "ebitda": 364, "sr_debt_service": 252, "mezz_service": 40, "cfads": 364, "free_cash": 72},
                {"year": 2029, "currency": "NOK_M", "revenue": 445, "opex": 66, "ebitda": 379, "sr_debt_service": 256, "mezz_service": 40, "cfads": 379, "free_cash": 83},
                {"year": 2030, "currency": "NOK_M", "revenue": 460, "opex": 69, "ebitda": 391, "sr_debt_service": 260, "mezz_service": 40, "cfads": 391, "free_cash": 91},
                {"year": 2031, "currency": "NOK_M", "revenue": 472, "opex": 71, "ebitda": 401, "sr_debt_service": 264, "mezz_service": 468, "cfads": 401, "free_cash": -331, "note": "Mezzanine bullet repayment — refinancing planned"},
            ],
        },
        "current_nav": Decimal("89500000"),
        "equity_invested": Decimal("82000000"),
        "investment_date": date(2025, 3, 20),
    },
    {
        "slug": "adriatic-infrastructure-holdings",
        "name": "Adriatic Infrastructure Holdings",
        "description": (
            "Mixed infrastructure portfolio: Istria Motorway (A-9 toll road, 42km), "
            "Primorska Voda (water utility, Rijeka metro, 185k population), "
            "Ljubljana District Energy (78km heating network, 1,240 buildings). "
            "Croatia & Slovenia. Concession-based stable yields, GDP-linked demand growth."
        ),
        "project_type": ProjectType.INFRASTRUCTURE,
        "status": ProjectStatus.ACTIVE,
        "stage": ProjectStage.OPERATIONAL,
        "geography_country": "Croatia / Slovenia",
        "geography_region": "Southeast Europe — Istria, Rijeka, Ljubljana",
        "geography_coordinates": {"lat": 45.3, "lng": 14.5},
        "capacity_mw": None,
        "total_investment_required": Decimal("485000000"),
        "currency": "EUR",
        "technology_details": {
            "project_id_ref": "PRJ-2023-0311",
            "asset_class": "Core Infrastructure — Transport & Utilities",
            "acquisition_date": "2023-12-15",
            "sponsor": "Adriatic Infra Partners d.o.o. (Zagreb)",
            "spv": "Adriatic Infrastructure HoldCo Ltd (Jersey)",
            "deal_team_lead": "Luka Petrović (Vienna)",
            "credit_analyst": "Anna Kowalski (London)",
            "concessions": [
                {
                    "name": "Istria Motorway (A-9 extension)",
                    "type": "Toll Road",
                    "location": "Istria, Croatia",
                    "concession_end": "2048",
                    "annual_revenue_eur_m": 38.5,
                    "road_length_km": 42,
                    "lanes": "2x2",
                    "aadt_2025": 18400,
                    "aadt_growth_pct": 2.5,
                    "toll_rate_light_eur_km": 0.12,
                    "toll_rate_heavy_eur_km": 0.28,
                    "toll_escalation": "80% CPI-linked",
                    "traffic_mix_light_pct": 72,
                    "om_contractor": "Strabag (10yr service contract)",
                    "seasonal_variation": "+45% summer",
                },
                {
                    "name": "Primorska Voda",
                    "type": "Water Utility",
                    "location": "Rijeka metro area, Croatia",
                    "concession_end": "2051",
                    "annual_revenue_eur_m": 22.0,
                    "service_population": 185000,
                    "water_production_m3_day": 42000,
                    "network_length_km": 680,
                    "nrw_pct": 34.0,
                    "nrw_target_pct": 25.0,
                    "tariff_eur_m3": 1.85,
                    "regulatory_reset": "5yr (next: 2028)",
                    "rab_eur_m": 95,
                    "allowed_wacc_pct": 5.8,
                    "capex_programme_eur_m": 45,
                    "watchlist": True,
                    "watchlist_reason": "Regulatory risk — tariff review 2028 may compress allowed return",
                },
                {
                    "name": "Ljubljana District Energy",
                    "type": "District Heating/Cooling",
                    "location": "Ljubljana, Slovenia",
                    "concession_end": "2045",
                    "annual_revenue_eur_m": 18.5,
                    "network_heating_km": 78,
                    "network_cooling_km": 12,
                    "connected_buildings": 1240,
                    "heat_production_gwh_yr": 680,
                    "cooling_production_gwh_yr": 45,
                    "fuel_mix": {"natural_gas_pct": 55, "biomass_pct": 30, "waste_heat_pct": 15},
                    "decarbonisation_target": "80% renewable by 2035",
                    "largest_customer": "City of Ljubljana (18% revenue)",
                    "planned_investment_eur_m": 32,
                },
            ],
            "financial_model": {
                "total_ev_eur_m": 485.0,
                "senior_debt_eur_m": 310.0,
                "sub_notes_eur_m": 48.5,
                "equity_eur_m": 126.5,
                "blended_ltv_pct": 64.0,
                "blended_debt_cost": "Euribor + 195 bps (swapped: 4.72% all-in)",
                "consolidated_dscr": 1.38,
                "consolidated_dscr_downside": 1.14,
                "min_dscr_holdco": 1.10,
                "min_dscr_asset": 1.15,
                "portfolio_irr_pct": 11.2,
                "equity_irr_pct": 15.4,
                "dividend_yield_yr1_pct": 6.8,
                "wacc_pct": 7.15,
            },
            "cash_flow_projection": [
                {"year": 2025, "revenue": 79.0, "opex": 32.5, "ebitda": 46.5, "debt_service": 28.8, "capex": 12.0, "free_cash": 5.7},
                {"year": 2026, "revenue": 82.4, "opex": 33.8, "ebitda": 48.6, "debt_service": 29.4, "capex": 14.5, "free_cash": 4.7},
                {"year": 2027, "revenue": 86.1, "opex": 35.2, "ebitda": 50.9, "debt_service": 30.0, "capex": 18.0, "free_cash": 2.9},
                {"year": 2028, "revenue": 89.5, "opex": 36.4, "ebitda": 53.1, "debt_service": 30.6, "capex": 16.5, "free_cash": 6.0},
                {"year": 2029, "revenue": 93.2, "opex": 37.8, "ebitda": 55.4, "debt_service": 31.2, "capex": 11.0, "free_cash": 13.2},
            ],
            "watchlist": {"active": True, "item": "Primorska Voda — tariff review 2028"},
        },
        "current_nav": Decimal("158200000"),
        "equity_invested": Decimal("126500000"),
        "investment_date": date(2023, 12, 15),
    },
]


def ensure_projects(
    session: Session, org_id: uuid.UUID, portfolio_id: uuid.UUID,
    user_id: uuid.UUID, dry_run: bool,
) -> dict[str, uuid.UUID]:
    project_ids: dict[str, uuid.UUID] = {}

    for pd in PROJECTS:
        existing = session.execute(
            select(Project).where(
                Project.org_id == org_id,
                Project.slug == pd["slug"],
                Project.is_deleted == False,  # noqa: E712
            )
        ).scalar_one_or_none()

        if existing:
            print(f"  [ok] Project: {existing.name} ({existing.id})")
            project_ids[pd["slug"]] = existing.id
            # Update JSONB fields if needed
            if not dry_run:
                existing.technology_details = pd["technology_details"]
                existing.description = pd["description"]
                session.flush()
            continue

        pid = _uid()
        if not dry_run:
            proj = Project(
                id=pid,
                org_id=org_id,
                name=pd["name"],
                slug=pd["slug"],
                description=pd["description"],
                project_type=pd["project_type"],
                status=pd["status"],
                stage=pd["stage"],
                geography_country=pd["geography_country"],
                geography_region=pd["geography_region"],
                geography_coordinates=pd["geography_coordinates"],
                capacity_mw=pd["capacity_mw"],
                total_investment_required=pd["total_investment_required"],
                currency=pd["currency"],
                technology_details=pd["technology_details"],
                is_published=True,
            )
            session.add(proj)
            session.flush()

            # Portfolio holding
            ph = PortfolioHolding(
                id=_uid(),
                portfolio_id=portfolio_id,
                project_id=pid,
                asset_name=pd["name"],
                asset_type=AssetType.EQUITY,
                investment_date=pd["investment_date"],
                investment_amount=pd["equity_invested"],
                current_value=pd["current_nav"],
                ownership_pct=Decimal("100.00"),
                currency="EUR",
                status=HoldingStatus.ACTIVE,
                notes=pd["technology_details"].get("project_id_ref", ""),
            )
            session.add(ph)
            session.flush()

        project_ids[pd["slug"]] = pid
        print(f"  [+] Created project: {pd['name']} ({pid})")

    return project_ids


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------

MILESTONES = {
    "helios-solar-portfolio-iberia": [
        ("Financial Close", "Senior Facility Agreement executed", date(2024, 8, 14), date(2024, 8, 14), MilestoneStatus.COMPLETED, 100),
        ("Helios Almería I — COD", "Commercial operation of first plant (85 MWp)", date(2024, 2, 10), date(2024, 2, 10), MilestoneStatus.COMPLETED, 100),
        ("Helios Badajoz — COD", "Largest plant COD (100 MWp)", date(2024, 4, 15), date(2024, 4, 15), MilestoneStatus.COMPLETED, 100),
        ("Full Portfolio COD", "All 6 plants operational (420 MWp)", date(2024, 6, 30), date(2024, 6, 12), MilestoneStatus.COMPLETED, 100),
        ("First PPA Payment", "Iberdrola CfD first quarterly settlement", date(2024, 10, 1), date(2024, 10, 1), MilestoneStatus.COMPLETED, 100),
        ("Q4 2025 Monitoring Report", "Quarterly IC report submitted to lenders", date(2026, 2, 15), date(2026, 1, 28), MilestoneStatus.COMPLETED, 100),
        ("Córdoba Snag-List Resolution", "Complete outstanding items on Córdoba plant", date(2026, 3, 31), None, MilestoneStatus.IN_PROGRESS, 60),
        ("SFDR Periodic Disclosure", "Annual SFDR Art. 9 disclosure to investors", date(2026, 6, 30), None, MilestoneStatus.NOT_STARTED, 0),
        ("PPA-2 Renewal Strategy", "Term sheet options for Endesa PPA renewal", date(2026, 6, 30), None, MilestoneStatus.IN_PROGRESS, 20),
        ("Insurance Renewal", "Allianz policy renewal (expires Jan 2027)", date(2026, 10, 1), None, MilestoneStatus.NOT_STARTED, 0),
    ],
    "nordvik-wind-farm-ii": [
        ("Financial Close", "Senior and mezzanine facilities executed", date(2025, 3, 20), date(2025, 3, 20), MilestoneStatus.COMPLETED, 100),
        ("Site Access Roads", "Access road construction complete", date(2025, 4, 30), date(2025, 5, 8), MilestoneStatus.COMPLETED, 100),
        ("Foundation Pours (35/35)", "All 35 turbine foundations poured", date(2025, 9, 30), date(2025, 10, 12), MilestoneStatus.COMPLETED, 100),
        ("Turbine Deliveries Start", "First Vestas nacelle delivery", date(2025, 10, 15), date(2025, 10, 15), MilestoneStatus.COMPLETED, 100),
        ("Turbine Erection (35/35)", "All 35 turbines erected (28/35 complete)", date(2026, 6, 30), None, MilestoneStatus.IN_PROGRESS, 80),
        ("Internal Grid & Substation", "HV grid and substation (65% complete)", date(2026, 7, 31), None, MilestoneStatus.IN_PROGRESS, 65),
        ("Commissioning & Testing", "Individual turbine commissioning", date(2026, 9, 30), None, MilestoneStatus.NOT_STARTED, 0),
        ("COD / Grid Energisation", "Commercial operation and grid connection", date(2026, 11, 15), None, MilestoneStatus.NOT_STARTED, 0),
        ("Construction Milestone Certificate — March", "Monthly lender reporting", date(2026, 3, 20), None, MilestoneStatus.NOT_STARTED, 0),
        ("Defects Liability Period End", "End of Vestas 2-year DLP", date(2028, 11, 15), None, MilestoneStatus.NOT_STARTED, 0),
    ],
    "adriatic-infrastructure-holdings": [
        ("Portfolio Acquisition Close", "Acquisition of all 3 concessions completed", date(2023, 12, 15), date(2023, 12, 15), MilestoneStatus.COMPLETED, 100),
        ("Post-Acquisition 100-Day Review", "Operational handover and integration", date(2024, 3, 31), date(2024, 4, 5), MilestoneStatus.COMPLETED, 100),
        ("NRW Reduction Programme Launch", "Primorska Voda network improvement kickoff", date(2024, 6, 1), date(2024, 6, 1), MilestoneStatus.COMPLETED, 100),
        ("Annual Valuation (2025)", "External portfolio valuation completed", date(2026, 1, 30), date(2026, 1, 30), MilestoneStatus.COMPLETED, 100),
        ("Q4 2025 Monitoring Report", "IC quarterly report submitted", date(2026, 2, 15), date(2026, 2, 10), MilestoneStatus.COMPLETED, 100),
        ("NRW Mid-Programme Review", "Progress review: target 25% by 2030", date(2026, 6, 30), None, MilestoneStatus.IN_PROGRESS, 40),
        ("Heat Pump Procurement", "District Energy heat pump final review", date(2026, 9, 1), None, MilestoneStatus.IN_PROGRESS, 35),
        ("Tariff Pre-Filing Strategy", "Primorska Voda regulatory review preparation", date(2027, 6, 30), None, MilestoneStatus.NOT_STARTED, 0),
        ("EV Charging Feasibility Study", "Motorway EV infrastructure assessment", date(2026, 7, 31), None, MilestoneStatus.NOT_STARTED, 0),
        ("Insurance Renewal (All 3 Assets)", "Annual insurance review across portfolio", date(2026, 11, 15), None, MilestoneStatus.NOT_STARTED, 0),
    ],
}


def seed_milestones(session: Session, project_ids: dict, dry_run: bool):
    for slug, items in MILESTONES.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        for i, (name, desc, target, completed, status, pct) in enumerate(items):
            existing = session.execute(
                select(ProjectMilestone).where(
                    ProjectMilestone.project_id == pid,
                    ProjectMilestone.name == name,
                    ProjectMilestone.is_deleted == False,  # noqa: E712
                )
            ).scalar_one_or_none()
            if existing:
                continue
            if not dry_run:
                m = ProjectMilestone(
                    id=_uid(),
                    project_id=pid,
                    name=name,
                    description=desc,
                    target_date=target,
                    completed_date=completed,
                    status=status,
                    completion_pct=pct,
                    order_index=i,
                )
                session.add(m)
        print(f"  [+] Milestones seeded for {slug}")
    if not dry_run:
        session.flush()


# ---------------------------------------------------------------------------
# Budget Items
# ---------------------------------------------------------------------------

BUDGET_ITEMS = {
    "helios-solar-portfolio-iberia": [
        ("EPC & Equipment", "Solar panels, inverters, trackers, BOS", Decimal("218000000"), Decimal("218000000"), "EUR", BudgetItemStatus.PAID),
        ("Grid Connection & Substation", "Grid connection costs across 6 plants", Decimal("18500000"), Decimal("18200000"), "EUR", BudgetItemStatus.PAID),
        ("Land Lease (prepaid)", "25-year land lease payments capitalised", Decimal("12000000"), Decimal("12000000"), "EUR", BudgetItemStatus.PAID),
        ("Development & Permitting", "Environmental permits, planning, legal", Decimal("8500000"), Decimal("8300000"), "EUR", BudgetItemStatus.PAID),
        ("Debt Arrangement Fees", "Facility agent, legal, modelling", Decimal("4200000"), Decimal("4200000"), "EUR", BudgetItemStatus.PAID),
        ("Debt Service Reserve", "6 months DSRA funded at financial close", Decimal("13900000"), Decimal("13900000"), "EUR", BudgetItemStatus.PAID),
        ("O&M Reserve", "Initial O&M reserve account funding", Decimal("2500000"), Decimal("2500000"), "EUR", BudgetItemStatus.PAID),
        ("Snag-List Retention (Córdoba)", "Retained pending snag list completion", Decimal("1200000"), None, "EUR", BudgetItemStatus.COMMITTED),
    ],
    "nordvik-wind-farm-ii": [
        ("EPC Contract (Vestas/Skanska JV)", "Fixed-price EPC including nacelles and installation", Decimal("302000000"), Decimal("257700000"), "EUR", BudgetItemStatus.COMMITTED),
        ("Turbine Supply (35 × V162)", "Vestas nacelle supply and 10yr service contract", Decimal("168000000"), Decimal("148000000"), "EUR", BudgetItemStatus.COMMITTED),
        ("Grid & Substation (Internal)", "Internal 66kV grid and substation", Decimal("42000000"), Decimal("27300000"), "EUR", BudgetItemStatus.COMMITTED),
        ("Access Roads & Civil Works", "Site roads, laydown areas, foundations", Decimal("28000000"), Decimal("28000000"), "EUR", BudgetItemStatus.PAID),
        ("Environmental & Permitting", "NVE licence, environmental studies, Sámi consultation", Decimal("5500000"), Decimal("5500000"), "EUR", BudgetItemStatus.PAID),
        ("Development & Finance Costs", "Advisor, modelling, legal, arrangement fees", Decimal("12500000"), Decimal("12500000"), "EUR", BudgetItemStatus.PAID),
        ("Construction Contingency", "7.5% contingency reserve", Decimal("30500000"), Decimal("7000000"), "EUR", BudgetItemStatus.COMMITTED),
        ("Construction Insurance (CAR)", "Construction all-risk policy (Swiss Re)", Decimal("3200000"), Decimal("3200000"), "EUR", BudgetItemStatus.PAID),
    ],
    "adriatic-infrastructure-holdings": [
        ("Motorway Acquisition (Istria A-9)", "Equity purchase of toll road concession", Decimal("105000000"), Decimal("105000000"), "EUR", BudgetItemStatus.PAID),
        ("Water Utility Acquisition (Primorska)", "Equity purchase of water utility", Decimal("85000000"), Decimal("85000000"), "EUR", BudgetItemStatus.PAID),
        ("District Energy Acquisition (Ljubljana)", "Equity purchase of district heating", Decimal("75000000"), Decimal("75000000"), "EUR", BudgetItemStatus.PAID),
        ("Transaction Costs", "Legal, advisory, due diligence (PwC, Steer)", Decimal("14500000"), Decimal("14500000"), "EUR", BudgetItemStatus.PAID),
        ("Primorska Voda CapEx Programme", "Network renewal, NRW reduction 5yr programme", Decimal("45000000"), Decimal("12000000"), "EUR", BudgetItemStatus.COMMITTED),
        ("Ljubljana Heat Pump Integration", "Heat pump & geothermal (2027-2029)", Decimal("32000000"), Decimal("0"), "EUR", BudgetItemStatus.PLANNED),
        ("Motorway EV Charging Roll-out", "EV charging stations (post-feasibility)", Decimal("8000000"), None, "EUR", BudgetItemStatus.PLANNED),
    ],
}


def seed_budget_items(session: Session, project_ids: dict, dry_run: bool):
    for slug, items in BUDGET_ITEMS.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        for name, desc, estimated, actual, currency, status in items:
            existing = session.execute(
                select(ProjectBudgetItem).where(
                    ProjectBudgetItem.project_id == pid,
                    ProjectBudgetItem.category == name,
                    ProjectBudgetItem.is_deleted == False,  # noqa: E712
                )
            ).scalar_one_or_none()
            if existing:
                continue
            if not dry_run:
                b = ProjectBudgetItem(
                    id=_uid(),
                    project_id=pid,
                    category=name,
                    description=desc,
                    estimated_amount=estimated,
                    actual_amount=actual,
                    currency=currency,
                    status=status,
                )
                session.add(b)
        print(f"  [+] Budget items seeded for {slug}")
    if not dry_run:
        session.flush()


# ---------------------------------------------------------------------------
# Risk Assessments (21 total)
# ---------------------------------------------------------------------------

RISKS = {
    "helios-solar-portfolio-iberia": [
        ("R-001", RiskType.MARKET, RiskSeverity.HIGH, RiskProbability.POSSIBLE,
         "Merchant pool price drops below €40/MWh (OMIE day-ahead)",
         "56% contracted; hedging strategy for yr 2–3 merchant tail", "amber"),
        ("R-002", RiskType.CLIMATE, RiskSeverity.MEDIUM, RiskProbability.UNLIKELY,
         "Irradiance below P90 for >2 consecutive years",
         "DNV-verified P50/P90 reports; bifacial gain buffer", "green"),
        ("R-003", RiskType.REGULATORY, RiskSeverity.MEDIUM, RiskProbability.POSSIBLE,
         "Retroactive windfall profit tax (Spain)",
         "Portfolio diversification across 3 autonomous communities", "amber"),
        ("R-004", RiskType.OPERATIONAL, RiskSeverity.MEDIUM, RiskProbability.UNLIKELY,
         "Inverter failure rate above warranty curve",
         "Huawei SUN2000 5yr warranty + extended service agreement", "green"),
        ("R-005", RiskType.MARKET, RiskSeverity.HIGH, RiskProbability.UNLIKELY,
         "PPA off-taker downgrade below investment grade",
         "Step-in rights; replacement PPA trigger at BB+", "green"),
        ("R-006", RiskType.OPERATIONAL, RiskSeverity.LOW, RiskProbability.UNLIKELY,
         "Remaining snag-list items on Córdoba plant",
         "€1.2M retention held; 95% complete", "green"),
        ("R-007", RiskType.MARKET, RiskSeverity.LOW, RiskProbability.UNLIKELY,
         "EUR/USD mismatch on USD-denominated module spares",
         "Natural hedge via EUR revenues; minor exposure", "green"),
    ],
    "nordvik-wind-farm-ii": [
        ("R-101", RiskType.OPERATIONAL, RiskSeverity.MEDIUM, RiskProbability.LIKELY,
         "Winter weather delays (Nov–Feb) to construction schedule",
         "Schedule buffer; Arctic-rated equipment; heated concrete", "amber"),
        ("R-102", RiskType.MARKET, RiskSeverity.HIGH, RiskProbability.UNLIKELY,
         "Vestas nacelle delivery delay (remaining 7 turbines)",
         "28/35 delivered; remaining 7 in transit (ETA Apr 2026)", "green"),
        ("R-103", RiskType.OPERATIONAL, RiskSeverity.MEDIUM, RiskProbability.POSSIBLE,
         "Unexpected rock conditions at T-29 to T-35 foundation sites",
         "Geotech survey complete; additional blasting budget approved", "amber"),
        ("R-104", RiskType.MARKET, RiskSeverity.MEDIUM, RiskProbability.POSSIBLE,
         "NOK depreciation vs EUR (sponsor FX exposure)",
         "NOK-denominated debt; natural hedge on revenue", "green"),
        ("R-105", RiskType.REGULATORY, RiskSeverity.MEDIUM, RiskProbability.UNLIKELY,
         "ElCert scheme early phase-out before 2035",
         "PPA floor price covers debt service without ElCerts", "green"),
        ("R-106", RiskType.CLIMATE, RiskSeverity.HIGH, RiskProbability.UNLIKELY,
         "Reindeer migration corridor — construction impact",
         "Seasonal halt (Apr 15–May 30); Sámi council agreement signed", "green"),
        ("R-107", RiskType.MARKET, RiskSeverity.HIGH, RiskProbability.UNLIKELY,
         "Norsk Hydro credit deterioration below BBB",
         "Cross-default clause; parent guarantee (Norsk Hydro ASA)", "green"),
        ("R-108", RiskType.MARKET, RiskSeverity.HIGH, RiskProbability.UNLIKELY,
         "Total construction cost exceeds 7.5% contingency",
         "Fixed-price EPC with Vestas/Skanska JV; contingency 22% used", "green"),
    ],
    "adriatic-infrastructure-holdings": [
        ("R-201", RiskType.REGULATORY, RiskSeverity.HIGH, RiskProbability.LIKELY,
         "[WATCHLIST] Croatian water tariff review 2028 — allowed return compression",
         "Engaged regulatory advisor; pre-filing strategy Q3 2027", "red"),
        ("R-202", RiskType.MARKET, RiskSeverity.MEDIUM, RiskProbability.POSSIBLE,
         "Istria motorway traffic below base case (recession / tourism decline)",
         "Summer traffic buffer; 80% CPI toll escalation", "amber"),
        ("R-203", RiskType.REGULATORY, RiskSeverity.HIGH, RiskProbability.UNLIKELY,
         "Change of government affecting concession terms",
         "Concession protected by bilateral investment treaty", "green"),
        ("R-204", RiskType.OPERATIONAL, RiskSeverity.MEDIUM, RiskProbability.POSSIBLE,
         "Non-revenue water reduction programme behind schedule",
         "Dedicated PMO; milestone-linked contractor payments", "amber"),
        ("R-205", RiskType.MARKET, RiskSeverity.HIGH, RiskProbability.POSSIBLE,
         "Natural gas price spike impacts district heating margins",
         "Biomass switching capacity; 70% pass-through in tariff", "amber"),
        ("R-206", RiskType.OPERATIONAL, RiskSeverity.MEDIUM, RiskProbability.POSSIBLE,
         "District energy decarbonisation CapEx overrun",
         "Fixed-price heat pump contract; €5M contingency", "amber"),
        ("R-207", RiskType.MARKET, RiskSeverity.LOW, RiskProbability.UNLIKELY,
         "EUR/HRK residual FX risk",
         "Eliminated — Croatia adopted EUR Jan 2023", "green"),
        ("R-208", RiskType.CLIMATE, RiskSeverity.MEDIUM, RiskProbability.UNLIKELY,
         "Biomass sourcing — FSC certification gap",
         "Supplier audit programme; 2 certified alternates identified", "green"),
        ("R-209", RiskType.MARKET, RiskSeverity.MEDIUM, RiskProbability.UNLIKELY,
         "City of Ljubljana budget constraints affecting district energy revenue",
         "15yr take-or-pay contract; sovereign-adjacent counterparty", "green"),
    ],
}

SEVERITY_MAP = {"green": RiskAssessmentStatus.MONITORING, "amber": RiskAssessmentStatus.IDENTIFIED, "red": RiskAssessmentStatus.IDENTIFIED}
SCORE_MAP = {"red": Decimal("8.0"), "amber": Decimal("5.0"), "green": Decimal("2.5")}


def seed_risks(session: Session, project_ids: dict, org_id: uuid.UUID, user_id: uuid.UUID, dry_run: bool):
    for slug, risks in RISKS.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        for risk_id, rtype, sev, prob, desc, mitigation, colour in risks:
            existing = session.execute(
                select(RiskAssessment).where(
                    RiskAssessment.entity_id == pid,
                    RiskAssessment.description == desc,
                    RiskAssessment.is_deleted == False,  # noqa: E712
                )
            ).scalar_one_or_none()
            if existing:
                continue
            if not dry_run:
                r = RiskAssessment(
                    id=_uid(),
                    entity_type=RiskEntityType.PROJECT,
                    entity_id=pid,
                    org_id=org_id,
                    risk_type=rtype,
                    severity=sev,
                    probability=prob,
                    description=f"[{risk_id}] {desc}",
                    mitigation=mitigation,
                    status=SEVERITY_MAP[colour],
                    assessed_by=user_id,
                    overall_risk_score=SCORE_MAP[colour],
                    market_risk_score=SCORE_MAP[colour] if rtype == RiskType.MARKET else None,
                    regulatory_risk_score=SCORE_MAP[colour] if rtype == RiskType.REGULATORY else None,
                    climate_risk_score=SCORE_MAP[colour] if rtype == RiskType.CLIMATE else None,
                    technology_risk_score=SCORE_MAP[colour] if rtype == RiskType.OPERATIONAL else None,
                    monitoring_enabled=True,
                    data_sources={"source": "IC Memo", "last_review": str(REPORTING_DATE)},
                )
                session.add(r)
        print(f"  [+] Risks seeded for {slug}")
    if not dry_run:
        session.flush()


# ---------------------------------------------------------------------------
# Covenants
# ---------------------------------------------------------------------------

COVENANTS = {
    "helios-solar-portfolio-iberia": [
        ("Minimum DSCR", "financial_ratio", "dscr", ">=", 1.15, 1.42, "compliant", "monthly"),
        ("Distribution Lock-Up DSCR", "financial_ratio", "distribution_dscr", ">=", 1.20, 1.42, "compliant", "quarterly"),
        ("Debt Service Reserve Account", "financial_ratio", "dsra_months", ">=", 6.0, 6.0, "compliant", "monthly"),
        ("O&M Reserve Minimum", "financial_ratio", "om_reserve_eur_m", ">=", 2.0, 2.5, "compliant", "quarterly"),
        ("Insurance Coverage", "insurance_maintenance", "insurance_active", "==", 1.0, 1.0, "compliant", "annual"),
        ("Environmental Permit Validity", "milestone", "permits_valid", "==", 1.0, 1.0, "compliant", "annual"),
        ("Quarterly IC Reporting", "reporting_deadline", "days_overdue", "<=", 45.0, 0.0, "compliant", "quarterly"),
        ("SFDR Periodic Disclosure", "reporting_deadline", "days_to_deadline", ">=", 0.0, 121.0, "compliant", "annual"),
    ],
    "nordvik-wind-farm-ii": [
        ("Construction Budget (EPC)", "financial_ratio", "epc_budget_nok_m", "<=", 4680.0, 3810.0, "compliant", "monthly"),
        ("Contingency Drawdown", "financial_ratio", "contingency_used_pct", "<=", 50.0, 22.0, "compliant", "monthly"),
        ("Construction Milestone Certificate", "reporting_deadline", "days_overdue", "<=", 0.0, 0.0, "compliant", "monthly"),
        ("Equity Contribution Schedule", "financial_ratio", "equity_drawn_pct", ">=", 80.0, 82.0, "compliant", "monthly"),
        ("Environmental Permit (NVE)", "milestone", "permit_active", "==", 1.0, 1.0, "compliant", "annual"),
        ("Construction All Risk Insurance", "insurance_maintenance", "car_insurance_active", "==", 1.0, 1.0, "compliant", "monthly"),
        ("Turbine Supply Progress", "milestone", "turbines_erected", ">=", 28.0, 28.0, "warning", "monthly"),
    ],
    "adriatic-infrastructure-holdings": [
        ("Holdco DSCR", "financial_ratio", "holdco_dscr", ">=", 1.10, 1.38, "compliant", "quarterly"),
        ("Motorway DSCR (ring-fenced)", "financial_ratio", "motorway_dscr", ">=", 1.15, 1.52, "compliant", "quarterly"),
        ("Water Utility DSCR", "financial_ratio", "water_dscr", ">=", 1.15, 1.18, "warning", "quarterly"),
        ("District Energy DSCR", "financial_ratio", "energy_dscr", ">=", 1.15, 1.35, "compliant", "quarterly"),
        ("Distribution Lock-Up (Holdco)", "financial_ratio", "distribution_dscr", ">=", 1.20, 1.38, "compliant", "quarterly"),
        ("CapEx Reporting", "reporting_deadline", "capex_report_days_overdue", "<=", 45.0, 0.0, "compliant", "quarterly"),
        ("Concession Compliance (all 3)", "milestone", "concessions_certified", "==", 3.0, 3.0, "compliant", "annual"),
        ("Water NRW Target", "operational_kpi", "nrw_pct", "<=", 30.0, 34.0, "breach", "quarterly"),
        ("Insurance (all assets)", "insurance_maintenance", "insurance_active", "==", 3.0, 3.0, "compliant", "annual"),
        ("Quarterly IC Reporting", "reporting_deadline", "days_overdue", "<=", 45.0, 0.0, "compliant", "quarterly"),
    ],
}


def seed_covenants(session: Session, project_ids: dict, org_id: uuid.UUID, dry_run: bool):
    for slug, covs in COVENANTS.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        for name, ctype, metric, comp, threshold, current, status, freq in covs:
            existing = session.execute(
                select(Covenant).where(
                    Covenant.project_id == pid,
                    Covenant.name == name,
                    Covenant.is_deleted == False,  # noqa: E712
                )
            ).scalar_one_or_none()
            if existing:
                if not dry_run:
                    existing.current_value = current
                    existing.status = status
                continue
            if not dry_run:
                c = Covenant(
                    id=_uid(),
                    org_id=org_id,
                    project_id=pid,
                    name=name,
                    covenant_type=ctype,
                    metric_name=metric,
                    comparison=comp,
                    threshold_value=threshold,
                    current_value=current,
                    status=status,
                    check_frequency=freq,
                    last_checked_at=_now(),
                    warning_threshold_pct=0.05,
                )
                session.add(c)
        print(f"  [+] Covenants seeded for {slug}")
    if not dry_run:
        session.flush()


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

KPIS = {
    "helios-solar-portfolio-iberia": [
        ("Energy Production (P50)", "actual", "2025-Q4", 192.1, "GWh", "quarterly"),
        ("DSCR", "actual", "2025-Q4", 1.42, "ratio", "quarterly"),
        ("Revenue", "actual", "2025-Q4", 12.05, "EUR_M", "quarterly"),
        ("OPEX", "actual", "2025-Q4", 2.225, "EUR_M", "quarterly"),
        ("Availability Factor", "actual", "2025-Q4", 98.4, "pct", "quarterly"),
        ("CO2 Avoided", "actual", "2025", 309500, "tCO2e", "annual"),
        ("Energy Production (P50)", "target", "2025-Q4", 192.1, "GWh", "quarterly"),
        ("DSCR", "target", "2025-Q4", 1.42, "ratio", "quarterly"),
        ("Availability Factor", "target", "2025-Q4", 98.0, "pct", "quarterly"),
    ],
    "nordvik-wind-farm-ii": [
        ("Construction Progress", "actual", "2026-Q1", 85.0, "pct_complete", "monthly"),
        ("Turbines Erected", "actual", "2026-Q1", 28.0, "count", "monthly"),
        ("Budget Utilisation", "actual", "2026-Q1", 81.4, "pct", "monthly"),
        ("Contingency Used", "actual", "2026-Q1", 22.0, "pct", "monthly"),
        ("Construction Progress", "target", "2026-Q1", 85.0, "pct_complete", "monthly"),
        ("Turbines Erected", "target", "2026-Q1", 35.0, "count", "monthly"),
    ],
    "adriatic-infrastructure-holdings": [
        ("Consolidated Revenue", "actual", "2025", 79.0, "EUR_M", "annual"),
        ("Consolidated DSCR", "actual", "2025-Q4", 1.38, "ratio", "quarterly"),
        ("AADT Motorway", "actual", "2025", 18400.0, "vehicles_day", "annual"),
        ("Water NRW", "actual", "2025-Q4", 34.0, "pct", "quarterly"),
        ("Water Tariff", "actual", "2026-Q1", 1.85, "EUR_m3", "quarterly"),
        ("Heat Production", "actual", "2025", 680.0, "GWh_yr", "annual"),
        ("Consolidated Revenue", "target", "2025", 79.0, "EUR_M", "annual"),
        ("Consolidated DSCR", "target", "2025-Q4", 1.38, "ratio", "quarterly"),
        ("Water NRW", "target", "2025-Q4", 30.0, "pct", "quarterly"),
    ],
}


def seed_kpis(session: Session, project_ids: dict, org_id: uuid.UUID, user_id: uuid.UUID, dry_run: bool):
    for slug, kpis in KPIS.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        for name, kind, period, value, unit, period_type in kpis:
            if kind == "actual":
                existing = session.execute(
                    select(KPIActual).where(
                        KPIActual.project_id == pid,
                        KPIActual.kpi_name == name,
                        KPIActual.period == period,
                        KPIActual.is_deleted == False,  # noqa: E712
                    )
                ).scalar_one_or_none()
                if existing:
                    continue
                if not dry_run:
                    session.add(KPIActual(
                        id=_uid(), org_id=org_id, project_id=pid,
                        kpi_name=name, value=value, unit=unit,
                        period=period, period_type=period_type,
                        source="manual", entered_by=user_id,
                    ))
            else:
                existing = session.execute(
                    select(KPITarget).where(
                        KPITarget.project_id == pid,
                        KPITarget.kpi_name == name,
                        KPITarget.period == period,
                        KPITarget.is_deleted == False,  # noqa: E712
                    )
                ).scalar_one_or_none()
                if existing:
                    continue
                if not dry_run:
                    session.add(KPITarget(
                        id=_uid(), org_id=org_id, project_id=pid,
                        kpi_name=name, target_value=value, period=period,
                        tolerance_pct=0.05, source="investment_memo",
                    ))
        print(f"  [+] KPIs seeded for {slug}")
    if not dry_run:
        session.flush()


# ---------------------------------------------------------------------------
# ESG Metrics
# ---------------------------------------------------------------------------

ESG_DATA = {
    "helios-solar-portfolio-iberia": {
        "period": "2025",
        "carbon_avoided_tco2e": 309500.0,
        "carbon_footprint_tco2e": 0.0,
        "renewable_energy_mwh": 768500.0,
        "water_usage_cubic_m": 12500.0,
        "waste_diverted_tonnes": 45.0,
        "biodiversity_score": 72.0,
        "jobs_created": 85,
        "jobs_supported": 210,
        "local_procurement_pct": 42.0,
        "community_investment_eur": 180000.0,
        "gender_diversity_pct": 35.0,
        "health_safety_incidents": 0,
        "board_independence_pct": 60.0,
        "audit_completed": True,
        "esg_reporting_standard": "SFDR",
        "taxonomy_eligible": True,
        "taxonomy_aligned": True,
        "taxonomy_activity": "Climate Mitigation — Solar power generation (4.1)",
        "sfdr_article": 9,
        "sdg_contributions": {
            "7": {"name": "Affordable and Clean Energy", "contribution_level": "high"},
            "13": {"name": "Climate Action", "contribution_level": "high"},
            "8": {"name": "Decent Work and Economic Growth", "contribution_level": "medium"},
            "15": {"name": "Life on Land", "contribution_level": "low"},
        },
        "esg_narrative": (
            "Helios Solar Portfolio demonstrates strong EU Taxonomy alignment (100% Climate "
            "Mitigation eligible). 56% contracted revenue underpins financial stability. "
            "Biodiversity corridor restoration underway in Almería. SFDR Art. 9 classification "
            "confirmed. GRESB target score 78/100."
        ),
    },
    "nordvik-wind-farm-ii": {
        "period": "2025",
        "carbon_avoided_tco2e": 285000.0,  # post-COD estimate
        "carbon_footprint_tco2e": 8200.0,   # construction emissions
        "renewable_energy_mwh": 0.0,         # pre-COD
        "water_usage_cubic_m": 850.0,
        "waste_diverted_tonnes": 180.0,
        "biodiversity_score": 65.0,
        "jobs_created": 340,
        "jobs_supported": 680,
        "local_procurement_pct": 38.0,
        "community_investment_eur": 1050000.0,  # NOK 12M community fund → ~€1.05M
        "gender_diversity_pct": 28.0,
        "health_safety_incidents": 1,
        "board_independence_pct": 50.0,
        "audit_completed": False,
        "esg_reporting_standard": "SFDR",
        "taxonomy_eligible": True,
        "taxonomy_aligned": True,
        "taxonomy_activity": "Climate Mitigation — Wind power generation (4.3)",
        "sfdr_article": 9,
        "sdg_contributions": {
            "7": {"name": "Affordable and Clean Energy", "contribution_level": "high"},
            "13": {"name": "Climate Action", "contribution_level": "high"},
            "15": {"name": "Life on Land", "contribution_level": "medium"},
            "11": {"name": "Sustainable Cities", "contribution_level": "low"},
        },
        "esg_narrative": (
            "Nordvik Wind II achieves SFDR Art. 9 classification. Reindeer migration corridor "
            "mitigation plan approved with Sámi Reindeer Herding Council. Construction phase "
            "emissions tracked; operational CO2 avoidance estimated at 285,000 tCO2e annually "
            "post-COD. GRESB target 72/100."
        ),
    },
    "adriatic-infrastructure-holdings": {
        "period": "2025",
        "carbon_avoided_tco2e": 0.0,
        "carbon_footprint_tco2e": 42000.0,  # Scope 1+2 (district heating dominant)
        "renewable_energy_mwh": 119000.0,   # biomass + waste heat portion
        "water_usage_cubic_m": 15330000.0,  # 42,000 m³/day water production
        "waste_diverted_tonnes": 0.0,
        "biodiversity_score": 52.0,
        "jobs_created": 420,
        "jobs_supported": 2400,
        "local_procurement_pct": 55.0,
        "community_investment_eur": 650000.0,
        "gender_diversity_pct": 40.0,  # 40% female board
        "health_safety_incidents": 2,
        "board_independence_pct": 60.0,
        "audit_completed": True,
        "esg_reporting_standard": "SFDR",
        "taxonomy_eligible": True,
        "taxonomy_aligned": False,  # partial — motorway transitional
        "taxonomy_activity": "Mixed: Water (6.1), District Energy (4.15), Motorway (Transitional)",
        "sfdr_article": 8,
        "sdg_contributions": {
            "6": {"name": "Clean Water and Sanitation", "contribution_level": "high"},
            "11": {"name": "Sustainable Cities and Communities", "contribution_level": "high"},
            "9": {"name": "Industry, Innovation and Infrastructure", "contribution_level": "medium"},
            "13": {"name": "Climate Action", "contribution_level": "medium"},
        },
        "esg_narrative": (
            "Adriatic Infrastructure holds SFDR Art. 8 classification. Water utility NRW "
            "reduction programme (34%→25% by 2030) is the primary environmental initiative. "
            "District Energy decarbonisation target 80% renewable by 2035. Gender diversity "
            "at board level: 40%. GRESB target 65/100. Motorway classified as Transitional."
        ),
    },
}


def seed_esg(session: Session, project_ids: dict, org_id: uuid.UUID, dry_run: bool):
    for slug, data in ESG_DATA.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        period = data["period"]
        existing = session.execute(
            select(ESGMetrics).where(
                ESGMetrics.project_id == pid,
                ESGMetrics.period == period,
                ESGMetrics.is_deleted == False,  # noqa: E712
            )
        ).scalar_one_or_none()
        if existing:
            if not dry_run:
                for k, v in data.items():
                    if k != "period" and hasattr(existing, k):
                        setattr(existing, k, v)
            continue
        if not dry_run:
            e = ESGMetrics(id=_uid(), project_id=pid, org_id=org_id, **data)
            session.add(e)
        print(f"  [+] ESG metrics seeded for {slug}")
    if not dry_run:
        session.flush()


# ---------------------------------------------------------------------------
# Documents (35+ total)
# ---------------------------------------------------------------------------

DOCUMENTS = {
    "helios-solar-portfolio-iberia": [
        ("Investment Committee Memo", "IC Pack", "Confidential", date(2024, 7, 22), "pdf"),
        ("Independent Technical Assessment (DNV)", "Due Diligence", "Confidential", date(2024, 6, 1), "pdf"),
        ("Yield Assessment Report — P50/P90 (DNV)", "Due Diligence", "Confidential", date(2024, 5, 15), "pdf"),
        ("Legal Due Diligence Report", "Due Diligence", "Confidential", date(2024, 6, 20), "pdf"),
        ("PPA-1 Executed Agreement (Iberdrola)", "Legal", "StrictlyConfidential", date(2024, 8, 10), "pdf"),
        ("PPA-2 Executed Agreement (Endesa)", "Legal", "StrictlyConfidential", date(2024, 8, 10), "pdf"),
        ("Senior Facility Agreement", "Legal", "StrictlyConfidential", date(2024, 8, 14), "pdf"),
        ("Environmental Impact Assessment", "Permit", "Internal", date(2023, 11, 20), "pdf"),
        ("Insurance Certificate (Allianz 2025)", "Insurance", "Internal", date(2025, 1, 15), "pdf"),
        ("Q4 2025 Monitoring Report", "Monitoring", "Internal", date(2026, 1, 28), "pdf"),
        ("Annual Valuation Report 2025", "Valuation", "Confidential", date(2026, 2, 15), "pdf"),
        ("SFDR Pre-contractual Disclosure", "ESG / Regulatory", "Public", date(2024, 8, 15), "pdf"),
        ("EU Taxonomy Assessment", "ESG / Regulatory", "Internal", date(2024, 8, 1), "pdf"),
    ],
    "nordvik-wind-farm-ii": [
        ("Investment Committee Memo", "IC Pack", "Confidential", date(2025, 2, 28), "pdf"),
        ("Independent Engineer Report (DNV)", "Due Diligence", "Confidential", date(2025, 1, 20), "pdf"),
        ("Wind Resource Assessment (Vortex/WindSim)", "Due Diligence", "Confidential", date(2024, 11, 15), "pdf"),
        ("Geotechnical Investigation Report", "Technical", "Internal", date(2024, 8, 30), "pdf"),
        ("EPC Contract (Vestas/Skanska JV)", "Legal", "StrictlyConfidential", date(2025, 3, 18), "pdf"),
        ("Corporate PPA — Norsk Hydro", "Legal", "StrictlyConfidential", date(2025, 3, 15), "pdf"),
        ("Senior Facility Agreement (DNB/Nordea)", "Legal", "StrictlyConfidential", date(2025, 3, 20), "pdf"),
        ("Mezzanine Facility Agreement", "Legal", "StrictlyConfidential", date(2025, 3, 20), "pdf"),
        ("NVE Concession & Environmental Permit", "Permit", "Internal", date(2023, 9, 10), "pdf"),
        ("Sámi Council Co-existence Agreement", "ESG / Social", "Internal", date(2024, 6, 22), "pdf"),
        ("Monthly Construction Report #11 (Feb 2026)", "Monitoring", "Internal", date(2026, 2, 15), "pdf"),
    ],
    "adriatic-infrastructure-holdings": [
        ("Investment Committee Memo", "IC Pack", "Confidential", date(2023, 11, 20), "pdf"),
        ("Consolidated Due Diligence Report (PwC)", "Due Diligence", "Confidential", date(2023, 10, 1), "pdf"),
        ("Traffic Study — Istria Motorway (Steer)", "Due Diligence", "Confidential", date(2023, 9, 15), "pdf"),
        ("Water Utility Technical Assessment (Mott MacDonald)", "Due Diligence", "Confidential", date(2023, 9, 20), "pdf"),
        ("District Energy Decarbonisation Plan", "Technical", "Internal", date(2023, 10, 10), "pdf"),
        ("Concession Agreement — Istria Motorway", "Legal", "StrictlyConfidential", date(2012, 6, 30), "pdf"),
        ("Concession Agreement — Primorska Voda", "Legal", "StrictlyConfidential", date(2018, 3, 15), "pdf"),
        ("Concession Agreement — Ljubljana District Energy", "Legal", "StrictlyConfidential", date(2015, 9, 1), "pdf"),
        ("Senior Facility Agreement (UniCredit/Erste)", "Legal", "StrictlyConfidential", date(2023, 12, 14), "pdf"),
        ("Q4 2025 Monitoring Report", "Monitoring", "Internal", date(2026, 2, 10), "pdf"),
        ("Croatian Water Regulatory Framework Analysis", "Regulatory", "Internal", date(2025, 8, 15), "pdf"),
        ("Annual Valuation Report (2025)", "Valuation", "Confidential", date(2026, 1, 30), "pdf"),
        ("SFDR Periodic Disclosure (2025)", "ESG / Regulatory", "Public", date(2026, 3, 1), "pdf"),
    ],
}

CLASSIFICATION_MAP = {
    "Legal": DocumentClassification.LEGAL_AGREEMENT,
    "Permit": DocumentClassification.PERMIT,
    "Insurance": DocumentClassification.INSURANCE,
    "Valuation": DocumentClassification.VALUATION,
    "ESG / Regulatory": DocumentClassification.ENVIRONMENTAL_REPORT,
    "Due Diligence": DocumentClassification.TECHNICAL_STUDY,
    "Technical": DocumentClassification.TECHNICAL_STUDY,
    "IC Pack": DocumentClassification.PRESENTATION,
    "Monitoring": DocumentClassification.OTHER,
    "Financial": DocumentClassification.FINANCIAL_STATEMENT,
    "Business Plan": DocumentClassification.BUSINESS_PLAN,
}


def seed_documents(session: Session, project_ids: dict, org_id: uuid.UUID, user_id: uuid.UUID, dry_run: bool):
    for slug, docs in DOCUMENTS.items():
        pid = project_ids.get(slug)
        if not pid:
            continue

        # Ensure folder per project
        folder = session.execute(
            select(DocumentFolder).where(
                DocumentFolder.project_id == pid,
                DocumentFolder.name == "Due Diligence & Legal",
                DocumentFolder.is_deleted == False,  # noqa: E712
            )
        ).scalar_one_or_none()
        if not folder and not dry_run:
            folder = DocumentFolder(
                id=_uid(), org_id=org_id, project_id=pid,
                name="Due Diligence & Legal",
            )
            session.add(folder)
            session.flush()

        for doc_name, doc_type, classification, doc_date, ext in docs:
            existing = session.execute(
                select(Document).where(
                    Document.project_id == pid,
                    Document.name == doc_name,
                    Document.is_deleted == False,  # noqa: E712
                )
            ).scalar_one_or_none()
            if existing:
                continue
            if not dry_run:
                safe_name = doc_name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
                d = Document(
                    id=_uid(),
                    org_id=org_id,
                    project_id=pid,
                    folder_id=folder.id if folder else None,
                    name=doc_name,
                    file_type=ext,
                    mime_type="application/pdf",
                    s3_key=f"demo/{slug}/{safe_name}_{doc_date.strftime('%Y%m%d')}.{ext}",
                    s3_bucket="scr-staging-documents",
                    file_size_bytes=int(500000 + hash(doc_name) % 9500000),
                    version=1,
                    status=DocumentStatus.READY,
                    uploaded_by=user_id,
                    checksum_sha256="0" * 64,
                    classification=CLASSIFICATION_MAP.get(doc_type),
                    metadata_={
                        "document_type": doc_type,
                        "access_level": classification,
                        "document_date": str(doc_date),
                        "source": "Demo Seed",
                    },
                )
                session.add(d)
        print(f"  [+] Documents seeded for {slug}")
    if not dry_run:
        session.flush()


# ---------------------------------------------------------------------------
# Signal Scores
# ---------------------------------------------------------------------------

SIGNAL_SCORES = {
    "helios-solar-portfolio-iberia": {
        "overall_score": 83,
        "project_viability_score": 88,
        "financial_planning_score": 85,
        "risk_assessment_score": 79,
        "team_strength_score": 84,
        "esg_score": 78,
        "market_opportunity_score": 80,
        "scoring_details": {
            "ai_summary": (
                "Strong operational solar portfolio with 56% contracted revenue providing cash-flow "
                "visibility. DSCR 1.42x comfortably above 1.15x covenant. Merchant tail exposure "
                "manageable; bifacial upside supports P50. ESG Art. 9, EU Taxonomy aligned. "
                "Minor amber: merchant price risk and Spanish regulatory environment."
            )
        },
    },
    "nordvik-wind-farm-ii": {
        "overall_score": 76,
        "project_viability_score": 79,
        "financial_planning_score": 77,
        "risk_assessment_score": 71,
        "team_strength_score": 82,
        "esg_score": 69,
        "market_opportunity_score": 74,
        "scoring_details": {
            "ai_summary": (
                "Late-stage construction wind farm with strong wind resource (NCF 38.5%). "
                "85% complete; 7 remaining nacelles in transit. Construction risk amber due to "
                "winter weather and geotech at T-29 to T-35. NOK/EUR FX naturally hedged. "
                "Post-COD DSCR projected 1.48x. Sámi agreement resolved key ESG risk."
            )
        },
    },
    "adriatic-infrastructure-holdings": {
        "overall_score": 74,
        "project_viability_score": 80,
        "financial_planning_score": 75,
        "risk_assessment_score": 65,
        "team_strength_score": 78,
        "esg_score": 70,
        "market_opportunity_score": 72,
        "scoring_details": {
            "ai_summary": (
                "Diversified core infrastructure portfolio with stable regulated revenues. "
                "DSCR 1.38x holdco level. Key watchlist: Primorska Voda tariff review 2028 — "
                "Red risk flag. NRW reduction behind plan (34% vs 30% target). District Energy "
                "decarbonisation CapEx creates near-term free cash compression. SFDR Art. 8."
            )
        },
    },
}


def seed_signal_scores(session: Session, project_ids: dict, org_id: uuid.UUID, user_id: uuid.UUID, dry_run: bool):
    for slug, data in SIGNAL_SCORES.items():
        pid = project_ids.get(slug)
        if not pid:
            continue
        existing = session.execute(
            select(SignalScore).where(
                SignalScore.project_id == pid,
            )
        ).scalar_one_or_none()
        if existing:
            if not dry_run:
                for k, v in data.items():
                    if hasattr(existing, k):
                        setattr(existing, k, v)
            continue
        if not dry_run:
            s = SignalScore(
                id=_uid(),
                project_id=pid,
                model_used="demo-seed",
                calculated_at=datetime.utcnow(),
                **data,
            )
            session.add(s)
        print(f"  [+] Signal score seeded for {slug}")
    if not dry_run:
        session.flush()


# ---------------------------------------------------------------------------
# Cashflow Assumptions & Projections (J-Curve)
# ---------------------------------------------------------------------------

def seed_cashflow_pacing(session: Session, portfolio_id: uuid.UUID, org_id: uuid.UUID, dry_run: bool):
    existing = session.execute(
        select(CashflowAssumption).where(
            CashflowAssumption.portfolio_id == portfolio_id,
            CashflowAssumption.is_active == True,  # noqa: E712
            CashflowAssumption.is_deleted == False,  # noqa: E712
        )
    ).scalar_one_or_none()

    if existing:
        print(f"  [ok] Cashflow assumption already exists ({existing.id})")
        return

    if dry_run:
        return

    assumption_id = _uid()
    assumption = CashflowAssumption(
        id=assumption_id,
        portfolio_id=portfolio_id,
        org_id=org_id,
        committed_capital=Decimal("302100000"),
        investment_period_years=5,
        fund_life_years=15,
        optimistic_modifier=Decimal("1.25"),
        pessimistic_modifier=Decimal("0.80"),
        deployment_schedule={
            "year_1_pct": -0.42,  # 2023 — Adriatic acquisition
            "year_2_pct": -0.31,  # 2024 — Helios acquisition
            "year_3_pct": -0.27,  # 2025 — Nordvik commitment
            "year_4_pct": 0.0,
            "year_5_pct": 0.0,
        },
        distribution_schedule={
            "year_3_pct": 0.05,   # 2025 — first distributions
            "year_4_pct": 0.08,
            "year_5_pct": 0.12,
            "year_6_pct": 0.15,
            "year_7_pct": 0.18,
            "year_8_pct": 0.22,
            "year_9_pct": 0.25,
            "year_10_pct": 0.30,
            "year_11_pct": 0.35,
            "year_12_pct": 0.40,
            "year_13_pct": 0.50,
            "year_14_pct": 0.60,
            "year_15_pct": 0.80,
        },
        label="PAMP Infrastructure & Energy Fund I — Base Case",
        is_active=True,
    )
    session.add(assumption)
    session.flush()

    # J-curve projections for 3 scenarios
    SCENARIOS = {
        "base": (Decimal("1.00"), [
            (2023, date(2023, 1, 1), date(2023, 12, 31), Decimal("-126500000"), Decimal("0"), Decimal("126500000"), Decimal("-126500000")),
            (2024, date(2024, 1, 1), date(2024, 12, 31), Decimal("-93600000"), Decimal("0"), Decimal("220100000"), Decimal("-93600000")),
            (2025, date(2025, 1, 1), date(2025, 12, 31), Decimal("-82000000"), Decimal("15000000"), Decimal("390500000"), Decimal("-67000000")),
            (2026, date(2026, 1, 1), date(2026, 12, 31), Decimal("0"), Decimal("24200000"), Decimal("410000000"), Decimal("24200000")),
            (2027, date(2027, 1, 1), date(2027, 12, 31), Decimal("0"), Decimal("36200000"), Decimal("430000000"), Decimal("36200000")),
            (2028, date(2028, 1, 1), date(2028, 12, 31), Decimal("0"), Decimal("45600000"), Decimal("445000000"), Decimal("45600000")),
            (2029, date(2029, 1, 1), date(2029, 12, 31), Decimal("0"), Decimal("54200000"), Decimal("458000000"), Decimal("54200000")),
            (2030, date(2030, 1, 1), date(2030, 12, 31), Decimal("0"), Decimal("65000000"), Decimal("468000000"), Decimal("65000000")),
        ]),
        "optimistic": (Decimal("1.25"), None),
        "pessimistic": (Decimal("0.80"), None),
    }

    base_rows = SCENARIOS["base"][1]
    for scenario, (modifier, rows) in SCENARIOS.items():
        if rows is None:
            rows = base_rows
        for year_idx, (year, pstart, pend, contrib, distrib, nav, net_cf) in enumerate(rows):
            session.add(CashflowProjection(
                id=_uid(),
                assumption_id=assumption_id,
                org_id=org_id,
                scenario=scenario,
                year=year_idx + 1,
                period_start=pstart,
                period_end=pend,
                projected_contributions=contrib * modifier if scenario != "base" else contrib,
                projected_distributions=distrib * modifier if scenario != "base" else distrib,
                projected_nav=nav * modifier if scenario != "base" else nav,
                projected_net_cashflow=net_cf * modifier if scenario != "base" else net_cf,
                actual_contributions=contrib if year <= 2025 else None,
                actual_distributions=distrib if year <= 2025 else None,
                actual_nav=nav if year <= 2025 else None,
                actual_net_cashflow=net_cf if year <= 2025 else None,
            ))
    session.flush()
    print(f"  [+] Cashflow assumption + projections seeded (3 scenarios, 8 years)")


# ---------------------------------------------------------------------------
# Market Data (External Data Points)
# ---------------------------------------------------------------------------

MARKET_DATA_POINTS = [
    # FRED — interest rates & macro
    ("fred", "DGS10", "10-Year Treasury Constant Maturity Rate", date(2026, 3, 1), 4.21, "percent"),
    ("fred", "EURIBOR3MD156N", "3-Month Euribor (EUR)", date(2026, 3, 1), 3.15, "percent"),
    ("fred", "CPIAUCSL", "Consumer Price Index (US, All Urban)", date(2026, 2, 1), 314.2, "index"),
    ("fred", "DCOILWTICO", "Crude Oil Prices: WTI", date(2026, 3, 1), 78.45, "usd_per_barrel"),
    ("fred", "DHHNGSP", "Natural Gas: Henry Hub Spot Price", date(2026, 3, 1), 2.85, "usd_per_mmBtu"),
    # Alpha Vantage — market data
    ("alpha_vantage", "BRENT", "Brent Crude Oil Spot Price", date(2026, 3, 1), 82.10, "usd_per_barrel"),
    ("alpha_vantage", "TTF", "TTF Natural Gas Forward Price", date(2026, 3, 1), 35.40, "eur_per_mwh"),
    ("alpha_vantage", "VIX", "CBOE Volatility Index", date(2026, 3, 1), 17.8, "index"),
    # Ember — carbon data
    ("ember", "EUA", "EU ETS Carbon Allowance Price", date(2026, 3, 1), 68.25, "eur_per_tco2"),
    ("ember", "CARB_INTENSITY_EU", "EU Power Sector Carbon Intensity", date(2026, 3, 1), 215.0, "gco2_per_kwh"),
    # EIA — energy data
    ("eia", "ELEC.CONS_TOT.ALL-EU-99.A", "EU Total Electricity Consumption", date(2025, 12, 31), 3218.5, "twh"),
    ("eia", "NG.RNGWHHD.D", "Henry Hub Natural Gas Spot Price", date(2026, 3, 1), 2.85, "usd_per_mmBtu"),
    # OpenWeather — weather for project sites
    ("openweather", "WIND_MADRID", "Wind Speed — Madrid (Helios proxy)", date(2026, 3, 1), 4.2, "m_per_s"),
    ("openweather", "IRRADIANCE_SEVILLE", "GHI Solar Irradiance — Seville", date(2026, 3, 1), 185.0, "wh_per_m2_day"),
    ("openweather", "WIND_TRONDHEIM", "Wind Speed — Trondheim (Nordvik proxy)", date(2026, 3, 1), 7.8, "m_per_s"),
    # ENTSO-E — power prices
    ("entsoe", "OMIE_DAH", "OMIE Day-Ahead Price — Iberia", date(2026, 3, 1), 61.45, "eur_per_mwh"),
    ("entsoe", "NORDPOOL_NO3", "Nordpool Day-Ahead — NO3 Area", date(2026, 3, 1), 42.10, "eur_per_mwh"),
    ("entsoe", "EPEX_DE", "EPEX Day-Ahead — Germany", date(2026, 3, 1), 58.90, "eur_per_mwh"),
    # ECB — FX rates
    ("ecb", "EUR/USD", "EUR/USD Exchange Rate", date(2026, 3, 1), 1.0845, "rate"),
    ("ecb", "EUR/NOK", "EUR/NOK Exchange Rate", date(2026, 3, 1), 11.42, "rate"),
    ("ecb", "EUR/GBP", "EUR/GBP Exchange Rate", date(2026, 3, 1), 0.8572, "rate"),
]


def seed_market_data(session: Session, dry_run: bool):
    for source, series_id, series_name, data_date, value, unit in MARKET_DATA_POINTS:
        existing = session.execute(
            select(ExternalDataPoint).where(
                ExternalDataPoint.source == source,
                ExternalDataPoint.series_id == series_id,
                ExternalDataPoint.data_date == data_date,
            )
        ).scalar_one_or_none()
        if existing:
            continue
        if not dry_run:
            session.add(ExternalDataPoint(
                id=_uid(),
                source=source,
                series_id=series_id,
                series_name=series_name,
                data_date=data_date,
                value=value,
                unit=unit,
                fetched_at=_now(),
            ))
    if not dry_run:
        session.flush()
    print(f"  [+] {len(MARKET_DATA_POINTS)} market data points seeded")


# ---------------------------------------------------------------------------
# Data Connectors & Org Config
# ---------------------------------------------------------------------------

CONNECTOR_CATALOG = [
    ("fred", "FRED (Federal Reserve)", "market_data", "api_key", "free", 60, "https://fred.stlouisfed.org/docs/api/"),
    ("alpha_vantage", "Alpha Vantage", "market_data", "api_key", "free", 5, "https://www.alphavantage.co/documentation/"),
    ("ember", "Ember Carbon Data", "esg", "api_key", "free", 60, "https://ember-climate.org/data/apis/"),
    ("eia", "EIA (US Energy Info Admin)", "energy", "api_key", "free", 60, "https://www.eia.gov/opendata/"),
    ("open_weather", "OpenWeatherMap", "weather", "api_key", "free", 60, "https://openweathermap.org/api"),
    ("entso_e", "ENTSO-E Transparency", "energy", "api_key", "free", 30, "https://transparency.entsoe.eu/"),
    ("ecb", "European Central Bank", "market_data", "none", "free", 60, "https://sdw-wsrest.ecb.europa.eu/"),
    ("companies_house", "Companies House (UK)", "company", "api_key", "free", 600, "https://developer.company-information.service.gov.uk/"),
]


def seed_connectors(session: Session, org_id: uuid.UUID, dry_run: bool):
    connector_ids: dict[str, uuid.UUID] = {}

    for name, display_name, category, auth_type, pricing, rate_limit, docs_url in CONNECTOR_CATALOG:
        existing = session.execute(
            select(DataConnector).where(DataConnector.name == name)
        ).scalar_one_or_none()

        if existing:
            connector_ids[name] = existing.id
        else:
            cid = _uid()
            if not dry_run:
                session.add(DataConnector(
                    id=cid,
                    name=name,
                    display_name=display_name,
                    category=category,
                    auth_type=auth_type,
                    is_available=True,
                    pricing_tier=pricing,
                    rate_limit_per_minute=rate_limit,
                    documentation_url=docs_url,
                ))
                session.flush()
            connector_ids[name] = cid

    # Org connector configs (mark all with real API keys as enabled)
    KEY_MAP = {
        "fred": ("6769e42c27f54948d56699515e285413", True),
        "alpha_vantage": ("23ZBO37U67F7CYNQ", True),
        "ember": ("66c9b7f0-28e0-05f8-d195-90289d3cf56a", True),
        "eia": ("3BwFjfe0zLKkydg0U1NHE2hndB8LJdr7ePYVJBf6", True),
        "open_weather": ("73e778bfad3d5fc1ce40076afc939a34", True),
        "entso_e": ("", False),  # no key provided
        "ecb": ("", True),  # no auth required
        "companies_house": ("d2c13c50-a808-40d1-99ee-a240bda6aab3", True),
    }

    for conn_name, (api_key, is_enabled) in KEY_MAP.items():
        cid = connector_ids.get(conn_name)
        if not cid:
            continue
        existing = session.execute(
            select(OrgConnectorConfig).where(
                OrgConnectorConfig.org_id == org_id,
                OrgConnectorConfig.connector_id == cid,
                OrgConnectorConfig.is_deleted == False,  # noqa: E712
            )
        ).scalar_one_or_none()
        if existing:
            if not dry_run:
                existing.is_enabled = is_enabled
                existing.last_sync_at = _now()
                existing.total_calls_this_month = 12 + hash(conn_name) % 50
            continue
        if not dry_run:
            session.add(OrgConnectorConfig(
                id=_uid(),
                org_id=org_id,
                connector_id=cid,
                is_enabled=is_enabled,
                api_key_encrypted=api_key[:20] + "***" if api_key else None,  # obfuscated in seed
                config={"environment": "staging", "regions": ["eu-north-1"]},
                last_sync_at=_now(),
                last_error=None,
                total_calls_this_month=12 + hash(conn_name) % 50,
            ))

    if not dry_run:
        session.flush()

    # Seed fetch logs (synthetic history)
    fetch_history = [
        ("fred", "https://api.stlouisfed.org/fred/series/observations", 200, 245, None),
        ("alpha_vantage", "https://www.alphavantage.co/query?function=COMMODITY", 200, 318, None),
        ("ember", "https://api.ember-climate.org/v1/carbon-price-data", 200, 420, None),
        ("eia", "https://api.eia.gov/v2/electricity/rto/region-data", 200, 380, None),
        ("open_weather", "https://api.openweathermap.org/data/2.5/weather", 200, 195, None),
        ("ecb", "https://sdw-wsrest.ecb.europa.eu/service/data/EXR", 200, 290, None),
        ("entso_e", "https://transparency.entsoe.eu/api", 403, 120, "API key not configured"),
        ("companies_house", "https://api.company-information.service.gov.uk/search", 200, 560, None),
    ]

    for conn_name, endpoint, status, resp_ms, error in fetch_history:
        cid = connector_ids.get(conn_name)
        if not cid or dry_run:
            continue
        session.add(DataFetchLog(
            id=_uid(),
            org_id=org_id,
            connector_id=cid,
            endpoint=endpoint,
            status_code=status,
            response_time_ms=resp_ms,
            error_message=error,
        ))

    if not dry_run:
        session.flush()
    print(f"  [+] {len(CONNECTOR_CATALOG)} connectors + org configs + fetch logs seeded")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Master demo seed script")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be seeded without DB writes")
    parser.add_argument("--wipe-extra", action="store_true", help="Delete augmented data before re-seeding")
    args = parser.parse_args()

    print("\n🌱  SCR Platform — Master Demo Seed")
    print("=" * 60)

    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        print(f"  DB: {result.scalar()[:50]}...")

    with Session(engine) as session:
        print("\n[1/10] Organisation & user")
        org_id, user_id = ensure_org_user(session, args.dry_run)

        print("\n[2/10] Portfolio")
        portfolio_id = ensure_portfolio(session, org_id, args.dry_run)

        print("\n[3/10] Projects")
        project_ids = ensure_projects(session, org_id, portfolio_id, user_id, args.dry_run)

        print("\n[4/10] Milestones")
        seed_milestones(session, project_ids, args.dry_run)

        print("\n[5/10] Budget items")
        seed_budget_items(session, project_ids, args.dry_run)

        print("\n[6/10] Risk assessments (21 risks)")
        seed_risks(session, project_ids, org_id, user_id, args.dry_run)

        print("\n[7/10] Covenants")
        seed_covenants(session, project_ids, org_id, args.dry_run)

        print("\n[8/10] KPIs")
        seed_kpis(session, project_ids, org_id, user_id, args.dry_run)

        print("\n[9/10] ESG metrics")
        seed_esg(session, project_ids, org_id, args.dry_run)

        print("\n[10/10] Documents (35+)")
        seed_documents(session, project_ids, org_id, user_id, args.dry_run)

        print("\n[Bonus A] Signal scores")
        seed_signal_scores(session, project_ids, org_id, user_id, args.dry_run)

        print("\n[Bonus B] Cashflow pacing (J-curve)")
        seed_cashflow_pacing(session, portfolio_id, org_id, args.dry_run)

        print("\n[Bonus C] Market data (FRED, AV, Ember, EIA, OpenWeather, ENTSO-E, ECB)")
        seed_market_data(session, args.dry_run)

        print("\n[Bonus D] Data connectors + sync history")
        seed_connectors(session, org_id, args.dry_run)

        if not args.dry_run:
            session.commit()
            print("\n✅  Committed.")
        else:
            print("\n[DRY RUN — no DB writes]")

    print("\nDone. Every platform page should now show populated demo data.")
    print("Login: demo@pampgroup.com / Demo@SCR2026!")


if __name__ == "__main__":
    main()
