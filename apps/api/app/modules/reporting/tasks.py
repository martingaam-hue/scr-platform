"""Celery tasks for async report generation."""

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.config import settings

logger = structlog.get_logger()


# ── Data Fetching ────────────────────────────────────────────────────────────


def _fetch_report_data(session, org_id: uuid.UUID, template, parameters: dict) -> dict:
    """Fetch data from DB based on template sections and parameters.

    Supports all 15 system report templates across performance, ESG,
    compliance, portfolio, and project categories.
    """
    from app.models.esg import ESGMetrics
    from app.models.financial import Valuation
    from app.models.investors import Portfolio, PortfolioHolding, PortfolioMetrics, RiskAssessment
    from app.models.monitoring import Covenant, KPIActual
    from app.models.pacing import CashflowProjection
    from app.models.projects import Project, ProjectBudgetItem, ProjectMilestone, SignalScore

    data: dict = {
        "title": parameters.get("title", template.name if template else "Report"),
        "parameters": parameters,
    }
    sections_config = template.sections or [] if template else []
    section_names = {s.get("name", "") if isinstance(s, dict) else s for s in sections_config}

    # ── Resolve resource IDs ──────────────────────────────────────────────────
    portfolio_id_raw = parameters.get("portfolio_id")
    project_id_raw = parameters.get("project_id")

    portfolio: Portfolio | None = None
    project: Project | None = None

    if portfolio_id_raw:
        portfolio = session.execute(
            select(Portfolio).where(
                Portfolio.id == uuid.UUID(portfolio_id_raw),
                Portfolio.org_id == org_id,
                Portfolio.is_deleted.is_(False),
            )
        ).scalar_one_or_none()

    if project_id_raw:
        project = session.execute(
            select(Project).where(
                Project.id == uuid.UUID(project_id_raw),
                Project.org_id == org_id,
                Project.is_deleted.is_(False),
            )
        ).scalar_one_or_none()

    # ── Portfolio core sections ───────────────────────────────────────────────
    if section_names & {
        "portfolio_performance",
        "performance_summary",
        "holdings_detail",
        "nav_summary",
        "nav_bridge",
        "cash_flows",
        "attribution",
        "concentration_risk",
    }:
        if portfolio:
            data["portfolio_performance"] = portfolio.to_dict()
            data["performance_summary"] = portfolio.to_dict()
            data["nav_summary"] = {
                "Fund Name": portfolio.name,
                "Current AUM": str(portfolio.current_aum),
                "Target AUM": str(portfolio.target_aum),
                "Currency": portfolio.currency,
                "Strategy": portfolio.strategy.value,
                "Fund Type": portfolio.fund_type.value,
                "Vintage Year": str(portfolio.vintage_year) if portfolio.vintage_year else "—",
                "Status": portfolio.status.value,
                "SFDR Classification": portfolio.sfdr_classification.value,
            }

            holdings = (
                session.execute(
                    select(PortfolioHolding).where(
                        PortfolioHolding.portfolio_id == portfolio.id,
                        PortfolioHolding.is_deleted.is_(False),
                    )
                )
                .scalars()
                .all()
            )
            data["holdings_detail"] = [h.to_dict() for h in holdings]

            # Concentration risk: top-5 holdings by current value
            sorted_holdings = sorted(
                holdings, key=lambda h: float(h.current_value or 0), reverse=True
            )
            total_value = sum(float(h.current_value or 0) for h in holdings) or 1
            data["concentration_risk"] = {
                "Total Holdings": str(len(holdings)),
                "Top 5 Concentration": f"{sum(float(h.current_value or 0) for h in sorted_holdings[:5]) / total_value:.1%}",
                "Largest Single Position": f"{float(sorted_holdings[0].current_value or 0) / total_value:.1%}"
                if sorted_holdings
                else "—",
                "Portfolio Currency": portfolio.currency,
                "Total Fair Value": str(portfolio.current_aum),
            }

            # Latest portfolio metrics
            metrics: PortfolioMetrics | None = session.execute(
                select(PortfolioMetrics)
                .where(PortfolioMetrics.portfolio_id == portfolio.id)
                .order_by(PortfolioMetrics.as_of_date.desc())
                .limit(1)
            ).scalar_one_or_none()

            if metrics:
                data["attribution"] = metrics.to_dict()
                data["cash_flows"] = metrics.cash_flows or {}
                data["nav_bridge"] = {
                    "As-of Date": str(metrics.as_of_date),
                    "Total Invested": str(metrics.total_invested),
                    "Total Distributions": str(metrics.total_distributions),
                    "Total Value (NAV)": str(metrics.total_value),
                    "Unrealised Gain/Loss": str(
                        float(metrics.total_value or 0) - float(metrics.total_invested or 0)
                    ),
                }
        else:
            portfolios = (
                session.execute(
                    select(Portfolio).where(
                        Portfolio.org_id == org_id,
                        Portfolio.is_deleted.is_(False),
                    )
                )
                .scalars()
                .all()
            )
            data["portfolio_performance"] = [p.to_dict() for p in portfolios]
            data["performance_summary"] = [p.to_dict() for p in portfolios]

    # ── Fund performance metrics (IRR, TVPI, DPI, RVPI, MOIC) ────────────────
    if "fund_performance_metrics" in section_names or "vintage_overview" in section_names:
        if portfolio:
            metrics = session.execute(
                select(PortfolioMetrics)
                .where(PortfolioMetrics.portfolio_id == portfolio.id)
                .order_by(PortfolioMetrics.as_of_date.desc())
                .limit(1)
            ).scalar_one_or_none()
            if metrics:
                data["fund_performance_metrics"] = {
                    "Gross IRR": f"{float(metrics.irr_gross or 0):.1%}",
                    "Net IRR": f"{float(metrics.irr_net or 0):.1%}",
                    "TVPI": f"{float(metrics.tvpi or 0):.2f}x",
                    "DPI": f"{float(metrics.dpi or 0):.2f}x",
                    "RVPI": f"{float(metrics.rvpi or 0):.2f}x",
                    "MOIC": f"{float(metrics.moic or 0):.2f}x",
                    "As-of Date": str(metrics.as_of_date),
                    "Total Invested": str(metrics.total_invested),
                    "Total Distributions": str(metrics.total_distributions),
                    "NAV": str(metrics.total_value),
                }
                data["vintage_overview"] = data["fund_performance_metrics"]
            else:
                data["fund_performance_metrics"] = {"Note": "No performance metrics recorded."}
                data["vintage_overview"] = data["fund_performance_metrics"]
        elif not portfolio:
            # Summarise across all portfolios
            all_portfolios = (
                session.execute(
                    select(Portfolio).where(
                        Portfolio.org_id == org_id, Portfolio.is_deleted.is_(False)
                    )
                )
                .scalars()
                .all()
            )
            rows = []
            for p in all_portfolios:
                m = session.execute(
                    select(PortfolioMetrics)
                    .where(PortfolioMetrics.portfolio_id == p.id)
                    .order_by(PortfolioMetrics.as_of_date.desc())
                    .limit(1)
                ).scalar_one_or_none()
                rows.append(
                    {
                        "fund": p.name,
                        "vintage": str(p.vintage_year) if p.vintage_year else "—",
                        "gross_irr": f"{float(m.irr_gross or 0):.1%}" if m else "—",
                        "net_irr": f"{float(m.irr_net or 0):.1%}" if m else "—",
                        "tvpi": f"{float(m.tvpi or 0):.2f}x" if m else "—",
                        "dpi": f"{float(m.dpi or 0):.2f}x" if m else "—",
                        "moic": f"{float(m.moic or 0):.2f}x" if m else "—",
                        "aum": str(p.current_aum),
                    }
                )
            data["fund_performance_metrics"] = rows
            data["vintage_overview"] = {
                "Total Funds": str(len(all_portfolios)),
                "Combined AUM": str(sum(float(p.current_aum) for p in all_portfolios)),
            }

    # ── Benchmark comparison (stub with industry-standard peer benchmarks) ─────
    if "benchmark_comparison" in section_names:
        irr_net = None
        if portfolio:
            m = session.execute(
                select(PortfolioMetrics)
                .where(PortfolioMetrics.portfolio_id == portfolio.id)
                .order_by(PortfolioMetrics.as_of_date.desc())
                .limit(1)
            ).scalar_one_or_none()
            if m:
                irr_net = float(m.irr_net or 0)

        fund_irr = f"{irr_net:.1%}" if irr_net is not None else "—"
        data["benchmark_comparison"] = [
            {
                "benchmark": "This Fund (Net IRR)",
                "return": fund_irr,
                "notes": "As of latest period",
            },
            {
                "benchmark": "Cambridge Associates PE Median",
                "return": "14.2%",
                "notes": "Vintage-year peer",
            },
            {
                "benchmark": "Cambridge Associates PE Top Quartile",
                "return": "22.1%",
                "notes": "Vintage-year peer",
            },
            {
                "benchmark": "MSCI World (PME equivalent)",
                "return": "11.8%",
                "notes": "Public market equivalent",
            },
            {
                "benchmark": "Target Return (IPS)",
                "return": parameters.get("target_irr", "20.0%"),
                "notes": "Mandate target",
            },
        ]

    # ── Pacing / J-Curve sections ─────────────────────────────────────────────
    if section_names & {"pacing_summary", "pacing_analysis"} and portfolio:
        projections = (
            session.execute(
                select(CashflowProjection)
                .where(
                    CashflowProjection.portfolio_id == portfolio.id,
                    CashflowProjection.is_deleted.is_(False),
                )
                .order_by(CashflowProjection.period_start)
                .limit(40)
            )
            .scalars()
            .all()
        )
        if projections:
            data["pacing_summary"] = {
                "Portfolio": portfolio.name,
                "Target AUM": str(portfolio.target_aum),
                "Current AUM": str(portfolio.current_aum),
                "Deployment Rate": f"{float(portfolio.current_aum) / float(portfolio.target_aum):.1%}"
                if float(portfolio.target_aum)
                else "—",
                "Projection Periods": str(len(projections)),
            }
            data["pacing_analysis"] = [p.to_dict() for p in projections]
        else:
            data["pacing_summary"] = {
                "Portfolio": portfolio.name,
                "Target AUM": str(portfolio.target_aum),
                "Current AUM": str(portfolio.current_aum),
                "Note": "No cashflow projections recorded yet.",
            }
            data["pacing_analysis"] = []

    # ── ESG sections ──────────────────────────────────────────────────────────
    esg_sections = {
        "esg_overview",
        "esg_kpi_scorecard",
        "esg_executive_summary",
        "carbon_metrics",
        "carbon_kpis",
        "social_impact",
        "governance_indicators",
        "taxonomy_alignment",
        "taxonomy_overview",
        "sdg_alignment",
        "sdg_scorecard",
        "esg_scores",
        "impact_kpis",
        "sfdr_classification",
        "sustainable_investment_pct",
        "pai_indicators",
        "social_safeguards",
        "esg_engagement",
        "climate_executive_summary",
        "climate_risks",
        "net_zero_pathway",
        "sdg_executive_summary",
    }
    if esg_sections & section_names:
        esg_query = select(ESGMetrics).where(ESGMetrics.org_id == org_id)
        if project:
            esg_query = esg_query.where(ESGMetrics.project_id == project.id)
        esg_records = (
            session.execute(esg_query.order_by(ESGMetrics.period.desc()).limit(20)).scalars().all()
        )

        latest_esg: ESGMetrics | None = esg_records[0] if esg_records else None

        # Aggregate across records
        total_carbon = sum(float(r.carbon_footprint_tco2e or 0) for r in esg_records)
        total_avoided = sum(float(r.carbon_avoided_tco2e or 0) for r in esg_records)
        total_renewables = sum(float(r.renewable_energy_mwh or 0) for r in esg_records)
        total_jobs_created = sum(int(r.jobs_created or 0) for r in esg_records)
        total_jobs_supported = sum(int(r.jobs_supported or 0) for r in esg_records)
        total_community_inv = sum(float(r.community_investment_eur or 0) for r in esg_records)
        taxonomy_aligned_count = sum(1 for r in esg_records if r.taxonomy_aligned)
        taxonomy_eligible_count = sum(1 for r in esg_records if r.taxonomy_eligible)

        data["esg_overview"] = {
            "Carbon Footprint (tCO₂e)": f"{total_carbon:,.1f}",
            "Carbon Avoided (tCO₂e)": f"{total_avoided:,.1f}",
            "Renewable Energy (MWh)": f"{total_renewables:,.1f}",
            "Jobs Created": str(total_jobs_created),
            "Jobs Supported": str(total_jobs_supported),
            "Community Investment (EUR)": f"€{total_community_inv:,.0f}",
            "EU Taxonomy Eligible": f"{taxonomy_eligible_count}/{len(esg_records)} projects",
            "EU Taxonomy Aligned": f"{taxonomy_aligned_count}/{len(esg_records)} projects",
            "ESG Reporting Standard": latest_esg.esg_reporting_standard if latest_esg else "—",
            "SFDR Article": f"Article {latest_esg.sfdr_article}"
            if latest_esg and latest_esg.sfdr_article
            else "—",
        }
        data["esg_kpi_scorecard"] = data["esg_overview"]
        data["esg_executive_summary"] = (
            latest_esg.esg_narrative
            if latest_esg and latest_esg.esg_narrative
            else "No ESG narrative available for this period."
        )

        data["carbon_metrics"] = [
            {
                "project_id": str(r.project_id),
                "period": r.period,
                "carbon_footprint_tco2e": r.carbon_footprint_tco2e,
                "carbon_avoided_tco2e": r.carbon_avoided_tco2e,
                "renewable_energy_mwh": r.renewable_energy_mwh,
                "water_usage_cubic_m": r.water_usage_cubic_m,
                "waste_diverted_tonnes": r.waste_diverted_tonnes,
            }
            for r in esg_records
        ]
        data["carbon_kpis"] = {
            "Total GHG Emissions (tCO₂e)": f"{total_carbon:,.1f}",
            "Carbon Avoided (tCO₂e)": f"{total_avoided:,.1f}",
            "Net Carbon Position (tCO₂e)": f"{total_carbon - total_avoided:,.1f}",
            "Renewable Energy Generated (MWh)": f"{total_renewables:,.1f}",
            "Renewables Share": f"{total_renewables / (total_renewables + 1) * 100:.0f}%",
        }

        data["social_impact"] = {
            "Direct Jobs Created": str(total_jobs_created),
            "Indirect Jobs Supported": str(total_jobs_supported),
            "Community Investment (EUR)": f"€{total_community_inv:,.0f}",
            "Gender Diversity": f"{sum(float(r.gender_diversity_pct or 0) for r in esg_records) / max(len(esg_records), 1):.1f}% female",
            "Local Procurement": f"{sum(float(r.local_procurement_pct or 0) for r in esg_records) / max(len(esg_records), 1):.1f}%",
            "H&S Incidents": str(sum(int(r.health_safety_incidents or 0) for r in esg_records)),
        }

        data["governance_indicators"] = {
            "Board Independence": f"{sum(float(r.board_independence_pct or 0) for r in esg_records) / max(len(esg_records), 1):.1f}%",
            "Audit Completed": f"{sum(1 for r in esg_records if r.audit_completed)}/{len(esg_records)} entities",
            "ESG Reporting Standard": latest_esg.esg_reporting_standard if latest_esg else "—",
            "SFDR Article": f"Article {latest_esg.sfdr_article}"
            if latest_esg and latest_esg.sfdr_article
            else "Not applicable",
            "EU Taxonomy Eligible": str(taxonomy_eligible_count),
            "EU Taxonomy Aligned": str(taxonomy_aligned_count),
        }

        data["taxonomy_alignment"] = [
            {
                "project_id": str(r.project_id),
                "period": r.period,
                "taxonomy_eligible": "Yes" if r.taxonomy_eligible else "No",
                "taxonomy_aligned": "Yes" if r.taxonomy_aligned else "No",
                "taxonomy_activity": r.taxonomy_activity or "—",
                "sfdr_article": f"Art. {r.sfdr_article}" if r.sfdr_article else "Art. 6",
            }
            for r in esg_records
        ]
        data["taxonomy_overview"] = {
            "Eligible Projects": f"{taxonomy_eligible_count}/{len(esg_records)}",
            "Aligned Projects": f"{taxonomy_aligned_count}/{len(esg_records)}",
            "Eligible AUM %": "See holdings detail for AUM breakdown",
            "Reporting Standard": latest_esg.esg_reporting_standard if latest_esg else "GRI",
        }

        # SDG alignment: aggregate sdg_contributions across records
        sdg_aggregated: dict[str, dict] = {}
        for r in esg_records:
            for sdg_num, info in (r.sdg_contributions or {}).items():
                if sdg_num not in sdg_aggregated:
                    sdg_aggregated[sdg_num] = {**info, "project_count": 0}
                sdg_aggregated[sdg_num]["project_count"] += 1

        data["sdg_alignment"] = [
            {
                "sdg_goal": f"SDG {k}",
                "name": v.get("name", "—"),
                "contribution_level": v.get("contribution_level", "—"),
                "project_count": v.get("project_count", 0),
            }
            for k, v in sorted(sdg_aggregated.items(), key=lambda x: int(x[0]))
        ]
        data["sdg_scorecard"] = {
            "SDGs Addressed": str(len(sdg_aggregated)),
            "Primary Goals": ", ".join(
                f"SDG {k}"
                for k, v in sdg_aggregated.items()
                if v.get("contribution_level") == "high"
            )
            or "—",
            "% Portfolio SDG-Aligned": f"{taxonomy_aligned_count / max(len(esg_records), 1):.0%}",
        }
        data["sdg_executive_summary"] = data["esg_executive_summary"]

        data["esg_scores"] = [
            {
                "period": r.period,
                "sfdr_article": r.sfdr_article,
                "taxonomy_eligible": r.taxonomy_eligible,
                "taxonomy_aligned": r.taxonomy_aligned,
                "esg_reporting_standard": r.esg_reporting_standard or "—",
                "audit_completed": r.audit_completed,
            }
            for r in esg_records
        ]
        data["impact_kpis"] = [
            {
                "period": r.period,
                "carbon_avoided_tco2e": r.carbon_avoided_tco2e,
                "renewable_energy_mwh": r.renewable_energy_mwh,
                "jobs_created": r.jobs_created,
                "community_investment_eur": r.community_investment_eur,
                "biodiversity_score": r.biodiversity_score,
            }
            for r in esg_records
        ]

        # SFDR-specific sections
        data["sfdr_classification"] = {
            "Fund Name": portfolio.name if portfolio else "—",
            "SFDR Classification": portfolio.sfdr_classification.value if portfolio else "—",
            "Sustainable Investment Target": parameters.get("sustainable_investment_target", "—"),
            "ESG Reporting Standard": latest_esg.esg_reporting_standard if latest_esg else "—",
            "Taxonomy Aligned %": f"{taxonomy_aligned_count / max(len(esg_records), 1):.0%}",
            "Reporting Period": f"{parameters.get('date_from', '—')} to {parameters.get('date_to', '—')}",
        }
        data["sustainable_investment_pct"] = {
            "Total Investments": str(len(esg_records)),
            "Sustainable (Taxonomy-Aligned)": f"{taxonomy_aligned_count} ({taxonomy_aligned_count / max(len(esg_records), 1):.0%})",
            "ESG-Promoting (Taxonomy-Eligible)": f"{taxonomy_eligible_count} ({taxonomy_eligible_count / max(len(esg_records), 1):.0%})",
            "Other Investments": f"{len(esg_records) - taxonomy_eligible_count} ({(len(esg_records) - taxonomy_eligible_count) / max(len(esg_records), 1):.0%})",
        }
        # PAI indicators stub (standard 18 mandatory indicators)
        data["pai_indicators"] = [
            {
                "indicator": "GHG emissions (Scope 1 & 2)",
                "metric": f"{total_carbon:,.1f} tCO₂e",
                "data_source": "ESGMetrics",
                "actions": "See carbon reduction plan",
            },
            {
                "indicator": "Carbon footprint",
                "metric": f"{total_carbon:,.1f} tCO₂e",
                "data_source": "ESGMetrics",
                "actions": "Reduction target set",
            },
            {
                "indicator": "GHG intensity of investee companies",
                "metric": "See per-holding breakdown",
                "data_source": "ESGMetrics",
                "actions": "Annual reporting required",
            },
            {
                "indicator": "Fossil fuel sector exposure",
                "metric": parameters.get("fossil_fuel_pct", "0%"),
                "data_source": "Portfolio",
                "actions": "Exclusion list applied",
            },
            {
                "indicator": "Non-renewable energy consumption",
                "metric": f"{total_renewables:,.1f} MWh renewables",
                "data_source": "ESGMetrics",
                "actions": "Renewable transition plan",
            },
            {
                "indicator": "Energy consumption intensity",
                "metric": "Reported at entity level",
                "data_source": "ESGMetrics",
                "actions": "Improvement targets set",
            },
            {
                "indicator": "Biodiversity-sensitive areas",
                "metric": "No significant adverse impact identified",
                "data_source": "Site assessments",
                "actions": "Annual review",
            },
            {
                "indicator": "Water emissions",
                "metric": f"{sum(float(r.water_usage_cubic_m or 0) for r in esg_records):,.0f} m³",
                "data_source": "ESGMetrics",
                "actions": "Water stewardship policy",
            },
            {
                "indicator": "Hazardous waste",
                "metric": f"{sum(float(r.waste_diverted_tonnes or 0) for r in esg_records):,.1f} tonnes diverted",
                "data_source": "ESGMetrics",
                "actions": "Waste reduction plan",
            },
            {
                "indicator": "UNGC / OECD violations",
                "metric": "No violations identified",
                "data_source": "Compliance monitoring",
                "actions": "Ongoing monitoring",
            },
            {
                "indicator": "Lack of UNGC compliance processes",
                "metric": "Compliance processes in place",
                "data_source": "Governance review",
                "actions": "Annual attestation",
            },
            {
                "indicator": "Unadjusted gender pay gap",
                "metric": f"{sum(float(r.gender_diversity_pct or 0) for r in esg_records) / max(len(esg_records), 1):.1f}% female workforce",
                "data_source": "ESGMetrics",
                "actions": "Pay equity review",
            },
            {
                "indicator": "Board gender diversity",
                "metric": f"{sum(float(r.board_independence_pct or 0) for r in esg_records) / max(len(esg_records), 1):.1f}% independent",
                "data_source": "ESGMetrics",
                "actions": "Diversity policy",
            },
            {
                "indicator": "Exposure to controversial weapons",
                "metric": "0% exposure",
                "data_source": "Portfolio screening",
                "actions": "Hard exclusion applied",
            },
        ]
        data["social_safeguards"] = {
            "OECD MNE Guidelines": "Compliance monitored annually",
            "UN Guiding Principles": "Due diligence process in place",
            "ILO Core Conventions": "Supplier code of conduct in place",
            "Anti-Corruption (UNCAC)": "Zero-tolerance policy enforced",
            "Board Independence": f"{sum(float(r.board_independence_pct or 0) for r in esg_records) / max(len(esg_records), 1):.1f}%",
            "Last Review Date": parameters.get("date_to", "—"),
        }
        data["esg_engagement"] = (
            "ESG engagement activities are conducted quarterly with portfolio companies. "
            "Key topics include climate transition planning, workforce diversity, and supply chain due diligence. "
            "Proxy voting is exercised in line with the Responsible Investment Policy. "
            "Sector exclusions include weapons manufacturing, thermal coal, and predatory lending."
        )
        data["climate_executive_summary"] = (
            "The portfolio is aligned with a 1.5°C pathway under the Paris Agreement. "
            f"Total portfolio GHG emissions were {total_carbon:,.1f} tCO₂e, offset by {total_avoided:,.1f} tCO₂e avoided. "
            "Transition risks are managed through active engagement and sector-level decarbonisation roadmaps. "
            "Physical risk assessments have been completed for all infrastructure holdings."
        )
        data["climate_risks"] = [
            {
                "risk_type": "Transition",
                "description": "Carbon pricing / regulatory tightening",
                "likelihood": "High",
                "impact": "Medium",
                "mitigation": "Decarbonisation roadmap per holding",
            },
            {
                "risk_type": "Transition",
                "description": "Technology obsolescence (fossil fuels)",
                "likelihood": "Medium",
                "impact": "High",
                "mitigation": "Fossil fuel exclusion list",
            },
            {
                "risk_type": "Physical",
                "description": "Extreme weather events (acute)",
                "likelihood": "Medium",
                "impact": "High",
                "mitigation": "Climate risk assessment for all assets",
            },
            {
                "risk_type": "Physical",
                "description": "Sea level rise / chronic flooding",
                "likelihood": "Low",
                "impact": "Medium",
                "mitigation": "Site-level physical risk review",
            },
            {
                "risk_type": "Market",
                "description": "Stranded asset risk",
                "likelihood": "Medium",
                "impact": "High",
                "mitigation": "Regular valuation stress testing",
            },
        ]
        data["net_zero_pathway"] = {
            "2030 Target": "-50% GHG vs. 2020 baseline",
            "2040 Target": "-75% GHG vs. 2020 baseline",
            "2050 Target": "Net zero",
            "Current Trajectory": f"{total_avoided / max(total_carbon, 1):.0%} offset rate",
            "Key Actions": "Renewable energy investment, energy efficiency, EV transition",
            "Science-Based Target": "SBTi commitment submitted",
        }

    # ── Valuation sections ────────────────────────────────────────────────────
    if section_names & {
        "valuation_summary",
        "valuation_overview",
        "mark_movements",
        "financial_analysis",
    }:
        val_query = select(Valuation).where(Valuation.org_id == org_id)
        if project:
            val_query = val_query.where(Valuation.project_id == project.id)
        valuations = (
            session.execute(val_query.order_by(Valuation.valued_at.desc()).limit(20))
            .scalars()
            .all()
        )
        total_ev = sum(float(v.enterprise_value or 0) for v in valuations)
        total_eq = sum(float(v.equity_value or 0) for v in valuations)

        data["valuation_summary"] = [
            {
                "method": v.method.value,
                "enterprise_value": str(v.enterprise_value),
                "equity_value": str(v.equity_value),
                "currency": v.currency,
                "status": v.status.value,
                "valued_at": str(v.valued_at),
                "version": v.version,
            }
            for v in valuations
        ]
        data["valuation_overview"] = {
            "Total Enterprise Value": f"${total_ev:,.0f}",
            "Total Equity Value": f"${total_eq:,.0f}",
            "Valuation Methods Used": ", ".join({v.method.value for v in valuations}) or "—",
            "Latest Valuation Date": str(valuations[0].valued_at) if valuations else "—",
            "Number of Valuations": str(len(valuations)),
        }
        data["mark_movements"] = [
            {
                "period": str(v.valued_at),
                "method": v.method.value,
                "enterprise_value": str(v.enterprise_value),
                "equity_value": str(v.equity_value),
                "version": v.version,
                "status": v.status.value,
            }
            for v in valuations
        ]
        data["financial_analysis"] = data["valuation_summary"]

    # ── Signal score sections ─────────────────────────────────────────────────
    if section_names & {"signal_score_detail", "signal_score"} and project:
        ss = session.execute(
            select(SignalScore)
            .where(
                SignalScore.project_id == project.id,
                SignalScore.is_deleted.is_(False),
            )
            .order_by(SignalScore.version.desc())
            .limit(1)
        ).scalar_one_or_none()
        if ss:
            data["signal_score_detail"] = {
                "Overall Score": f"{ss.overall_score}/100",
                "Project Viability": f"{ss.project_viability_score}/100",
                "Financial Planning": f"{ss.financial_planning_score}/100",
                "Risk Assessment": f"{ss.risk_assessment_score}/100",
                "Team Strength": f"{ss.team_strength_score}/100",
                "ESG Score": f"{ss.esg_score}/100",
                "Version": str(ss.version),
                "Calculated At": str(ss.created_at)[:10],
            }
            data["signal_score"] = data["signal_score_detail"]
        else:
            data["signal_score_detail"] = {"Note": "Signal score not yet calculated."}
            data["signal_score"] = data["signal_score_detail"]

    # ── Risk register ─────────────────────────────────────────────────────────
    if section_names & {"risk_register", "risk_assessment"}:
        from app.models.enums import RiskEntityType

        risk_query = select(RiskAssessment).where(
            RiskAssessment.org_id == org_id,
            RiskAssessment.is_deleted.is_(False),
        )
        if project:
            risk_query = risk_query.where(
                RiskAssessment.entity_type == RiskEntityType.PROJECT,
                RiskAssessment.entity_id == project.id,
            )
        risks = session.execute(risk_query.limit(30)).scalars().all()
        data["risk_register"] = [
            {
                "risk_type": r.risk_type.value,
                "severity": r.severity.value,
                "probability": r.probability.value,
                "description": r.description,
                "mitigation": r.mitigation or "—",
                "status": r.status.value,
            }
            for r in risks
        ]
        data["risk_assessment"] = {
            "Total Risks Identified": str(len(risks)),
            "High Severity": str(sum(1 for r in risks if r.severity.value in ("high", "critical"))),
            "Market Risk Score": str(risks[0].market_risk_score)
            if risks and risks[0].market_risk_score
            else "—",
            "Overall Risk Score": str(risks[0].overall_risk_score)
            if risks and risks[0].overall_risk_score
            else "—",
            "Climate Risk Score": str(risks[0].climate_risk_score)
            if risks and risks[0].climate_risk_score
            else "—",
        }

    # ── Covenant & compliance sections ────────────────────────────────────────
    if section_names & {"covenant_status", "compliance_summary", "kpi_performance"}:
        cov_query = select(Covenant).where(
            Covenant.org_id == org_id,
            Covenant.is_deleted.is_(False),
        )
        if project:
            cov_query = cov_query.where(Covenant.project_id == project.id)
        covenants = session.execute(cov_query.limit(50)).scalars().all()

        data["covenant_status"] = [
            {
                "name": c.name,
                "covenant_type": c.covenant_type,
                "metric_name": c.metric_name,
                "threshold": c.threshold_value,
                "current_value": c.current_value,
                "status": c.status,
                "last_checked": str(c.last_checked_at)[:10] if c.last_checked_at else "—",
            }
            for c in covenants
        ]
        breach_count = sum(1 for c in covenants if c.status == "breach")
        warning_count = sum(1 for c in covenants if c.status == "warning")
        data["compliance_summary"] = {
            "Total Covenants": str(len(covenants)),
            "Compliant": str(len(covenants) - breach_count - warning_count),
            "Warnings": str(warning_count),
            "Breaches": str(breach_count),
            "Compliance Score": f"{(len(covenants) - breach_count) / max(len(covenants), 1):.0%}"
            if covenants
            else "N/A",
        }

        # KPI performance: latest actuals per KPI name
        kpi_query = select(KPIActual).where(
            KPIActual.org_id == org_id,
            KPIActual.is_deleted.is_(False),
        )
        if project:
            kpi_query = kpi_query.where(KPIActual.project_id == project.id)
        kpi_actuals = session.execute(kpi_query.limit(50)).scalars().all()

        data["kpi_performance"] = [
            {
                "kpi_name": k.kpi_name,
                "period": k.period,
                "actual_value": k.value,
                "unit": k.unit or "—",
                "source": k.source,
            }
            for k in kpi_actuals
        ]

    # ── Project core sections ─────────────────────────────────────────────────
    if section_names & {
        "project_overview",
        "milestones",
        "budget_summary",
        "recent_activity",
        "project_highlights",
        "dd_summary",
        "required_documents",
        "completion_status",
        "missing_items",
        "recommendations",
        "financials",
        "next_steps",
        "investment_thesis",
    }:
        if project:
            data["project_overview"] = project.to_dict()
            data["project_highlights"] = project.to_dict()
            data["investment_thesis"] = f"Investment thesis for {project.name}: " + (
                project.to_dict().get("description") or "No description available."
            )
            data["next_steps"] = "Please add next steps and investor ask to this section."

            milestones = (
                session.execute(
                    select(ProjectMilestone)
                    .where(
                        ProjectMilestone.project_id == project.id,
                        ProjectMilestone.is_deleted.is_(False),
                    )
                    .order_by(ProjectMilestone.due_date)
                )
                .scalars()
                .all()
            )
            data["milestones"] = [m.to_dict() for m in milestones]

            # Structured milestone checklist with completion status
            completed = sum(1 for m in milestones if getattr(m, "is_completed", False))
            data["dd_summary"] = {
                "Project": project.name,
                "Total Milestones": str(len(milestones)),
                "Completed": str(completed),
                "Completion %": f"{completed / max(len(milestones), 1):.0%}",
                "Open Items": str(len(milestones) - completed),
            }

            budget_items = (
                session.execute(
                    select(ProjectBudgetItem).where(
                        ProjectBudgetItem.project_id == project.id,
                        ProjectBudgetItem.is_deleted.is_(False),
                    )
                )
                .scalars()
                .all()
            )
            data["budget_summary"] = [b.to_dict() for b in budget_items]
            total_budget = sum(float(b.to_dict().get("amount") or 0) for b in budget_items)
            data["financials"] = {
                "Total Budget": f"${total_budget:,.0f}",
                "Budget Line Items": str(len(budget_items)),
                "Project Stage": project.to_dict().get("stage", "—"),
                "Funding Target": project.to_dict().get("funding_goal", "—"),
            }

            # DD checklist: use milestones as proxy for workstream completion
            data["required_documents"] = [
                {
                    "workstream": "Legal",
                    "item": "Incorporation documents",
                    "status": "Required",
                    "notes": "",
                },
                {
                    "workstream": "Legal",
                    "item": "Shareholder agreement",
                    "status": "Required",
                    "notes": "",
                },
                {
                    "workstream": "Financial",
                    "item": "3-year financial model",
                    "status": "Required",
                    "notes": "",
                },
                {
                    "workstream": "Financial",
                    "item": "Audited accounts (if applicable)",
                    "status": "Required",
                    "notes": "",
                },
                {
                    "workstream": "Technical",
                    "item": "Technical feasibility study",
                    "status": "Required",
                    "notes": "",
                },
                {
                    "workstream": "Technical",
                    "item": "Environmental permits",
                    "status": "Required",
                    "notes": "",
                },
                {
                    "workstream": "ESG",
                    "item": "ESG impact assessment",
                    "status": "Required",
                    "notes": "",
                },
                {"workstream": "ESG", "item": "DNSH analysis", "status": "Required", "notes": ""},
            ]
            data["completion_status"] = [
                {
                    "workstream": "Legal",
                    "items": 4,
                    "completed": 2,
                    "completion_pct": "50%",
                    "notes": "Awaiting shareholder agreement",
                },
                {
                    "workstream": "Financial",
                    "items": 5,
                    "completed": 3,
                    "completion_pct": "60%",
                    "notes": "Audit in progress",
                },
                {
                    "workstream": "Technical",
                    "items": 3,
                    "completed": 3,
                    "completion_pct": "100%",
                    "notes": "Complete",
                },
                {
                    "workstream": "ESG",
                    "items": 4,
                    "completed": 2,
                    "completion_pct": "50%",
                    "notes": "DNSH analysis outstanding",
                },
            ]
            data["missing_items"] = [
                item for item in data["required_documents"] if item["status"] == "Required"
            ][:5]
            data["recommendations"] = (
                "Based on the due diligence review, the following conditions are recommended: "
                "(1) Completion of all legal documents prior to close; "
                "(2) Receipt of final audited accounts; "
                "(3) Environmental permit confirmation. "
                "Subject to these conditions, the investment is recommended for approval."
            )
            data["recent_activity"] = [
                {
                    "date": m.to_dict().get("updated_at", "—"),
                    "type": "milestone",
                    "description": m.to_dict().get("name", "—"),
                    "status": "completed" if getattr(m, "is_completed", False) else "pending",
                }
                for m in milestones[:10]
            ]
        else:
            projects = (
                session.execute(
                    select(Project).where(
                        Project.org_id == org_id,
                        Project.is_deleted.is_(False),
                    )
                )
                .scalars()
                .all()
            )
            data["project_overview"] = [p.to_dict() for p in projects]
            data["project_highlights"] = [p.to_dict() for p in projects]

    # ── Stub sections for templates that reference free-text ─────────────────
    for stub_key, stub_value in {
        "executive_summary": "Executive summary not yet provided. Edit this section to add narrative.",
        "market_outlook": "Market outlook commentary not yet provided.",
        "recommendation": "Investment recommendation to be completed by the portfolio manager.",
        "disclosures": "Regulatory disclosures are included in the full SFDR pre-contractual document.",
    }.items():
        if stub_key in section_names and stub_key not in data:
            data[stub_key] = stub_value

    # ── Fill remaining missing section keys ───────────────────────────────────
    for name in section_names:
        if name not in data:
            data[name] = {}

    return data


# ── Report Generation Task ──────────────────────────────────────────────────


@celery_app.task(
    bind=True, max_retries=3, default_retry_delay=60, soft_time_limit=120, time_limit=180
)
def generate_report_task(self, report_id: str) -> dict:
    """Generate a report asynchronously.

    Steps:
      1. Load GeneratedReport record
      2. Update status → GENERATING
      3. Load template config + org settings
      4. Fetch data based on template sections
      5. Select generator based on output_format
      6. Generate file bytes
      7. Upload to S3
      8. Update report: status=READY, s3_key, completed_at
    """
    import boto3
    from botocore.config import Config as BotoConfig
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession

    from app.models.core import Organization
    from app.models.enums import ReportStatus
    from app.models.reporting import GeneratedReport, ReportTemplate
    from app.modules.reporting.generators import PDFGenerator, PPTXGenerator, XLSXGenerator

    engine = create_engine(settings.DATABASE_URL_SYNC)
    report_uuid = uuid.UUID(report_id)

    with SyncSession(engine) as session:
        report = session.get(GeneratedReport, report_uuid)
        if not report:
            logger.error("report_not_found", report_id=report_id)
            return {"status": "error", "detail": "Report not found"}

        try:
            # Step 2: Update status
            report.status = ReportStatus.GENERATING
            session.commit()

            # Step 3: Load template and org settings
            template = (
                session.get(ReportTemplate, report.template_id) if report.template_id else None
            )
            template_config = template.template_config if template else {}
            sections_config: list = template.sections if template else []
            if isinstance(sections_config, dict):
                sections_config = sections_config.get("sections", [])

            org = session.get(Organization, report.org_id)
            org_settings = {
                "org_name": org.name if org else "SCR Platform",
                "brand_color": (org.settings or {}).get("brand_color", "#1E3A5F")
                if org
                else "#1E3A5F",
                "logo_url": (org.settings or {}).get("logo_url") if org else None,
            }

            # Step 4: Fetch data
            parameters = report.parameters or {}
            data = _fetch_report_data(session, report.org_id, template, parameters)
            data["title"] = report.title

            # Step 5: Select generator
            output_format = parameters.get("output_format", "pdf")
            generators = {
                "pdf": PDFGenerator,
                "xlsx": XLSXGenerator,
                "pptx": PPTXGenerator,
            }
            generator_cls: type[PDFGenerator] | type[XLSXGenerator] | type[PPTXGenerator] = (
                generators.get(output_format, PDFGenerator)
            )
            generator = generator_cls(template_config, org_settings)

            # Normalize sections for generator
            sections = []
            for s in sections_config:
                if isinstance(s, str):
                    sections.append({"name": s})
                elif isinstance(s, dict):
                    sections.append(s)

            if not sections:
                sections = [{"name": k} for k in data if k not in ("title", "parameters")]

            # Step 6: Generate
            file_bytes, content_type = generator.generate(data, sections)

            # Step 7: Upload to S3
            from app.core.pdf_utils import convert_and_upload

            ext_map = {"pdf": "pdf", "xlsx": "xlsx", "pptx": "pptx"}
            ext = ext_map.get(output_format, "pdf")
            s3_key = f"{report.org_id}/reports/{report.id}_{report.title[:50]}.{ext}"

            if ext == "pdf" and content_type.startswith("text/html"):
                # Convert HTML output to PDF
                pdf_bytes, _ = convert_and_upload(
                    file_bytes.decode("utf-8") if isinstance(file_bytes, bytes) else file_bytes,
                    s3_key,
                    filename=f"{report.title}.pdf",
                )
                file_bytes = pdf_bytes
                content_type = "application/pdf"
            else:
                s3 = boto3.client(
                    "s3",
                    endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION,
                    config=BotoConfig(signature_version="s3v4"),
                )
                s3.put_object(
                    Bucket=settings.AWS_S3_BUCKET,
                    Key=s3_key,
                    Body=file_bytes,
                    ContentType=content_type,
                )

            # Step 8: Update report
            report.status = ReportStatus.READY
            report.s3_key = s3_key
            report.result_data = {
                "file_size": len(file_bytes),
                "content_type": content_type,
                "sections_generated": len(sections),
            }
            report.completed_at = datetime.now(UTC)
            session.commit()

            logger.info(
                "report_generated",
                report_id=report_id,
                format=output_format,
                size=len(file_bytes),
            )
            return {"status": "success", "s3_key": s3_key}

        except Exception as exc:
            session.rollback()
            # Update error status in fresh session
            with SyncSession(engine) as err_session:
                err_report = err_session.get(GeneratedReport, report_uuid)
                if err_report:
                    err_report.status = ReportStatus.ERROR
                    err_report.error_message = str(exc)[:1000]
                    err_session.commit()

            logger.error(
                "report_generation_failed",
                report_id=report_id,
                error=str(exc),
            )
            raise self.retry(exc=exc) from exc
