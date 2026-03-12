"""Seed 15 professional system report templates covering all categories.

Industry-standard structures for alternative investment and impact finance.

Usage:
    poetry run python -m app.modules.reporting.seed_templates
"""

import structlog
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as SyncSession

from app.core.config import settings
from app.models.enums import ReportCategory
from app.models.reporting import ReportTemplate

logger = structlog.get_logger()

# ── Section type constants ────────────────────────────────────────────────────
#
# Each section dict may carry a `type` hint used by PDF/XLSX generators:
#   "kv"            → key/value pairs table
#   "table"         → data table (list of dicts)
#   "text"          → free-form narrative text
#   "metrics_grid"  → 2–4 column KPI card grid
#   "checklist"     → status checklist table
#
# The generator falls back gracefully if the type is unrecognised.

SYSTEM_TEMPLATES: list[dict] = [
    # ── PERFORMANCE ───────────────────────────────────────────────────────────
    {
        "name": "LP Quarterly Report",
        "category": ReportCategory.PERFORMANCE,
        "description": (
            "ILPA-aligned quarterly report for limited partners. Covers fund "
            "performance (IRR, TVPI, DPI, RVPI), NAV bridge, cash flows, portfolio "
            "company updates, ESG highlights, and forward outlook."
        ),
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "pptx"],
            "default_format": "pdf",
            "required_parameters": ["portfolio_id", "date_from", "date_to"],
            "optional_parameters": ["include_esg", "include_benchmarks"],
            "display_hints": {
                "cover_style": "formal",
                "show_page_numbers": True,
                "confidentiality_notice": True,
            },
        },
        "sections": [
            {
                "name": "executive_summary",
                "label": "Executive Summary",
                "type": "text",
                "description": "Quarter highlights, key portfolio events, and fund status.",
            },
            {
                "name": "fund_performance_metrics",
                "label": "Fund Performance Metrics",
                "type": "metrics_grid",
                "description": "IRR (gross/net), TVPI, DPI, RVPI, and MOIC since inception.",
            },
            {
                "name": "nav_bridge",
                "label": "NAV Bridge",
                "type": "table",
                "description": "Opening NAV → contributions → distributions → unrealised gains → closing NAV.",
            },
            {
                "name": "cash_flows",
                "label": "Cash Flow Summary",
                "type": "table",
                "description": "Capital calls and distributions during the period.",
            },
            {
                "name": "holdings_detail",
                "label": "Portfolio Holdings",
                "type": "table",
                "description": "Each holding: cost basis, fair value, ownership %, unrealised gain/loss.",
            },
            {
                "name": "esg_overview",
                "label": "ESG Highlights",
                "type": "kv",
                "description": "Portfolio-level ESG score, carbon footprint, and key impact KPIs.",
            },
            {
                "name": "market_outlook",
                "label": "Market Outlook",
                "type": "text",
                "description": "GP commentary on macro environment and pipeline.",
            },
        ],
    },
    {
        "name": "Portfolio Performance Report",
        "category": ReportCategory.PERFORMANCE,
        "description": (
            "Detailed portfolio analytics with holdings breakdown, performance "
            "attribution by sector and vintage year, benchmark comparison (MSCI, "
            "Cambridge Associates), and risk-adjusted return metrics."
        ),
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "xlsx",
            "required_parameters": ["portfolio_id"],
            "optional_parameters": ["date_from", "date_to"],
            "display_hints": {"include_charts": True},
        },
        "sections": [
            {
                "name": "performance_summary",
                "label": "Performance Summary",
                "type": "metrics_grid",
                "description": "AUM, deployed capital, return since inception, and vintage.",
            },
            {
                "name": "holdings_detail",
                "label": "Holdings Detail",
                "type": "table",
                "description": "Full holdings table with valuation, ownership, and sector.",
            },
            {
                "name": "attribution",
                "label": "Attribution Analysis",
                "type": "table",
                "description": "Performance attribution by sector, geography, and stage.",
            },
            {
                "name": "benchmark_comparison",
                "label": "Benchmark Comparison",
                "type": "table",
                "description": "Fund IRR vs. Cambridge, MSCI World, and target return.",
            },
            {
                "name": "concentration_risk",
                "label": "Concentration & Risk",
                "type": "kv",
                "description": "Top-5 positions, sector concentration, and liquidity profile.",
            },
        ],
    },
    {
        "name": "Fund Vintage Year Analysis",
        "category": ReportCategory.PERFORMANCE,
        "description": (
            "Multi-vintage performance analysis showing IRR, TVPI, DPI, and RVPI "
            "for each fund vintage year. Benchmarked against public-market equivalent "
            "(PME) and Cambridge Associates peer quartile data."
        ),
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "pdf",
            "required_parameters": ["date_from", "date_to"],
            "display_hints": {"include_charts": True},
        },
        "sections": [
            {
                "name": "vintage_overview",
                "label": "Vintage Overview",
                "type": "metrics_grid",
                "description": "Summary across all vintages: total committed, drawn, returned.",
            },
            {
                "name": "portfolio_performance",
                "label": "Vintage Performance Table",
                "type": "table",
                "description": "Per-vintage: size, IRR (gross/net), TVPI, DPI, RVPI, status.",
            },
            {
                "name": "benchmark_comparison",
                "label": "Benchmark vs. Peers",
                "type": "table",
                "description": "Vintage-year IRR vs. Cambridge Associates top-/median-quartile.",
            },
            {
                "name": "attribution",
                "label": "PME Analysis",
                "type": "kv",
                "description": "Public-market equivalent (Long-Nickels PME) vs. S&P 500 / MSCI.",
            },
        ],
    },
    {
        "name": "J-Curve & Pacing Analysis",
        "category": ReportCategory.PERFORMANCE,
        "description": (
            "Capital pacing report showing deployment pace vs. target schedule, "
            "J-curve progression, and 3-scenario cash flow projections "
            "(base / optimistic / pessimistic) through fund life."
        ),
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "pdf",
            "required_parameters": ["portfolio_id"],
            "display_hints": {"include_charts": True},
        },
        "sections": [
            {
                "name": "pacing_summary",
                "label": "Pacing Summary",
                "type": "metrics_grid",
                "description": "Committed capital, deployed %, remaining dry powder, pace vs. plan.",
            },
            {
                "name": "cash_flows",
                "label": "Historical Cash Flows",
                "type": "table",
                "description": "Quarterly contributions and distributions since fund inception.",
            },
            {
                "name": "pacing_analysis",
                "label": "Deployment Pace Analysis",
                "type": "table",
                "description": "Actual vs. target deployment by period, with deviation commentary.",
            },
            {
                "name": "nav_summary",
                "label": "NAV & Unrealised Portfolio",
                "type": "kv",
                "description": "Current NAV, fair value, cost, and unrealised multiple.",
            },
        ],
    },
    # ── ESG ───────────────────────────────────────────────────────────────────
    {
        "name": "ESG Impact Report",
        "category": ReportCategory.ESG,
        "description": (
            "Comprehensive ESG impact report following GRI / SASB standards. "
            "Covers environmental footprint (carbon, energy, water), social impact "
            "(jobs, community investment), governance indicators, EU Taxonomy "
            "alignment, and SDG contribution mapping."
        ),
        "template_config": {
            "audience": "both",
            "supported_formats": ["pdf", "pptx"],
            "default_format": "pdf",
            "required_parameters": ["date_from", "date_to"],
            "optional_parameters": ["portfolio_id", "project_id"],
            "display_hints": {
                "reporting_standard": "GRI",
                "confidentiality_notice": False,
            },
        },
        "sections": [
            {
                "name": "esg_executive_summary",
                "label": "Executive Summary",
                "type": "text",
                "description": "Overall ESG performance narrative and key highlights for the period.",
            },
            {
                "name": "esg_kpi_scorecard",
                "label": "ESG KPI Scorecard",
                "type": "metrics_grid",
                "description": "E/S/G scores, carbon footprint (tCO₂e), jobs created, governance rating.",
            },
            {
                "name": "carbon_metrics",
                "label": "Carbon & Energy Metrics",
                "type": "table",
                "description": "Scope 1/2/3 emissions, carbon avoided, renewable energy generated.",
            },
            {
                "name": "social_impact",
                "label": "Social Impact",
                "type": "kv",
                "description": "Jobs created/supported, community investment, gender diversity, H&S.",
            },
            {
                "name": "governance_indicators",
                "label": "Governance Indicators",
                "type": "kv",
                "description": "Board independence, audit completion, ESG reporting standards adopted.",
            },
            {
                "name": "taxonomy_alignment",
                "label": "EU Taxonomy Alignment",
                "type": "table",
                "description": "Eligible vs. aligned activities per delegated act, Do No Significant Harm.",
            },
            {
                "name": "sdg_alignment",
                "label": "SDG Contribution Map",
                "type": "table",
                "description": "UN SDG goals addressed, contribution level, and evidence.",
            },
        ],
    },
    {
        "name": "EU Taxonomy Alignment Report",
        "category": ReportCategory.ESG,
        "description": (
            "Regulatory report for EU Taxonomy Regulation disclosures. Shows "
            "eligible and aligned economic activities, Do No Significant Harm (DNSH) "
            "criteria assessment, and minimum social safeguards compliance across "
            "the portfolio."
        ),
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "pdf",
            "required_parameters": ["portfolio_id", "date_from", "date_to"],
            "display_hints": {
                "reporting_standard": "EU Taxonomy Regulation",
                "confidentiality_notice": True,
            },
        },
        "sections": [
            {
                "name": "taxonomy_overview",
                "label": "Taxonomy Overview",
                "type": "metrics_grid",
                "description": "Portfolio % eligible, % aligned, and CapEx/OpEx/Turnover KPIs.",
            },
            {
                "name": "taxonomy_alignment",
                "label": "Activity-Level Alignment",
                "type": "table",
                "description": "Each economic activity: eligibility, DNSH assessment, alignment %.",
            },
            {
                "name": "esg_scores",
                "label": "DNSH Assessment",
                "type": "table",
                "description": "Do No Significant Harm criteria per environmental objective.",
            },
            {
                "name": "social_safeguards",
                "label": "Minimum Social Safeguards",
                "type": "kv",
                "description": "OECD MNE Guidelines, UN Guiding Principles compliance status.",
            },
            {
                "name": "holdings_detail",
                "label": "Portfolio-Level Disclosure",
                "type": "table",
                "description": "Per-holding taxonomy classification and contribution to aligned AUM.",
            },
        ],
    },
    {
        "name": "UN SDG Alignment Report",
        "category": ReportCategory.ESG,
        "description": (
            "Investor-grade report mapping portfolio investments to the 17 UN "
            "Sustainable Development Goals. Shows contribution levels, supporting "
            "evidence, and IMP-aligned impact performance monitoring (IMM framework)."
        ),
        "template_config": {
            "audience": "both",
            "supported_formats": ["pdf", "pptx"],
            "default_format": "pdf",
            "required_parameters": ["date_from", "date_to"],
            "optional_parameters": ["portfolio_id"],
            "display_hints": {"include_charts": True},
        },
        "sections": [
            {
                "name": "sdg_executive_summary",
                "label": "Impact Overview",
                "type": "text",
                "description": "Narrative summary of portfolio SDG alignment and key impact outcomes.",
            },
            {
                "name": "sdg_scorecard",
                "label": "SDG Scorecard",
                "type": "metrics_grid",
                "description": "SDGs addressed, primary/secondary goals, and % portfolio aligned.",
            },
            {
                "name": "sdg_alignment",
                "label": "SDG Contribution Detail",
                "type": "table",
                "description": "Per-SDG: projects contributing, outcome indicators, contribution level.",
            },
            {
                "name": "impact_kpis",
                "label": "Impact KPIs",
                "type": "table",
                "description": "Quantified impact metrics: people reached, emissions avoided, etc.",
            },
            {
                "name": "esg_scores",
                "label": "Portfolio ESG Scores",
                "type": "table",
                "description": "Project-level ESG scores and reporting standard adopted.",
            },
        ],
    },
    {
        "name": "Carbon & Climate Risk Report",
        "category": ReportCategory.ESG,
        "description": (
            "TCFD-aligned climate risk report. Covers portfolio carbon footprint "
            "(Scope 1/2/3), carbon avoided, transition and physical risk exposure, "
            "Paris Agreement alignment, and net-zero pathway."
        ),
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "pdf",
            "required_parameters": ["date_from", "date_to"],
            "optional_parameters": ["portfolio_id"],
            "display_hints": {
                "reporting_standard": "TCFD",
                "include_charts": True,
            },
        },
        "sections": [
            {
                "name": "climate_executive_summary",
                "label": "Climate Risk Overview",
                "type": "text",
                "description": "TCFD executive summary covering governance, strategy, risk, and metrics.",
            },
            {
                "name": "carbon_kpis",
                "label": "Carbon KPIs",
                "type": "metrics_grid",
                "description": "Total GHG (tCO₂e), carbon intensity, avoided emissions, renewables %.",
            },
            {
                "name": "carbon_metrics",
                "label": "Emissions Breakdown",
                "type": "table",
                "description": "Per-project carbon footprint, avoided, and renewable energy data.",
            },
            {
                "name": "climate_risks",
                "label": "Transition & Physical Risks",
                "type": "table",
                "description": "Risk type, likelihood, potential impact, mitigation measures.",
            },
            {
                "name": "net_zero_pathway",
                "label": "Net-Zero Pathway",
                "type": "kv",
                "description": "2030/2040/2050 targets, current trajectory, and committed actions.",
            },
        ],
    },
    # ── COMPLIANCE ────────────────────────────────────────────────────────────
    {
        "name": "SFDR Compliance Report",
        "category": ReportCategory.COMPLIANCE,
        "description": (
            "SFDR periodic disclosure report for Article 8 and 9 funds. Covers "
            "product classification, principal adverse impact (PAI) indicators, "
            "sustainable investment percentages, taxonomy alignment, and pre- / "
            "post-contractual disclosure obligations."
        ),
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "pdf",
            "required_parameters": ["portfolio_id", "date_from", "date_to"],
            "display_hints": {
                "reporting_standard": "SFDR",
                "confidentiality_notice": True,
            },
        },
        "sections": [
            {
                "name": "sfdr_classification",
                "label": "SFDR Fund Classification",
                "type": "kv",
                "description": "Product category (Art. 6/8/9), sustainability objective, legal entity.",
            },
            {
                "name": "pai_indicators",
                "label": "Principal Adverse Impact Indicators",
                "type": "table",
                "description": "All 18 mandatory PAI indicators with metrics, data source, and actions.",
            },
            {
                "name": "sustainable_investment_pct",
                "label": "Sustainable Investment Share",
                "type": "metrics_grid",
                "description": "% sustainable investments, % taxonomy-aligned, % other ESG.",
            },
            {
                "name": "taxonomy_alignment",
                "label": "Taxonomy Alignment",
                "type": "table",
                "description": "Aligned activities, DNSH criteria, and minimum safeguards status.",
            },
            {
                "name": "esg_engagement",
                "label": "Engagement & Stewardship",
                "type": "text",
                "description": "ESG engagement activities, proxy voting, and exclusion policy summary.",
            },
            {
                "name": "disclosures",
                "label": "Regulatory Disclosures",
                "type": "text",
                "description": "Remuneration policy statement and additional SFDR disclosures.",
            },
        ],
    },
    {
        "name": "Investment Policy Compliance",
        "category": ReportCategory.COMPLIANCE,
        "description": (
            "Investment policy statement (IPS) compliance report. Tracks adherence "
            "to mandate constraints (sector limits, geography, stage, concentration), "
            "prohibited investments, and covenant compliance across the portfolio."
        ),
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "pdf",
            "required_parameters": ["portfolio_id", "date_from", "date_to"],
            "display_hints": {"confidentiality_notice": True},
        },
        "sections": [
            {
                "name": "compliance_summary",
                "label": "Compliance Summary",
                "type": "metrics_grid",
                "description": "Total constraints tracked, # violations, # warnings, compliance score.",
            },
            {
                "name": "concentration_risk",
                "label": "Concentration Limits",
                "type": "table",
                "description": "Sector, geography, and single-name limits vs. actual exposure.",
            },
            {
                "name": "covenant_status",
                "label": "Covenant Status",
                "type": "table",
                "description": "All covenants: type, threshold, actual, status (compliant/breach/waiver).",
            },
            {
                "name": "kpi_performance",
                "label": "KPI Performance vs. Targets",
                "type": "table",
                "description": "Monitored KPIs: target, actual, variance, and trend.",
            },
            {
                "name": "risk_assessment",
                "label": "Risk Assessment",
                "type": "kv",
                "description": "Mandate risk rating, key risk flags, and recommended actions.",
            },
        ],
    },
    {
        "name": "Due Diligence Checklist",
        "category": ReportCategory.COMPLIANCE,
        "description": (
            "Comprehensive legal, financial, technical, and ESG due diligence "
            "tracker. Shows document receipt status, completion percentage by "
            "workstream, identified gaps, and outstanding action items."
        ),
        "template_config": {
            "audience": "both",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "xlsx",
            "required_parameters": ["project_id"],
            "display_hints": {"confidentiality_notice": True},
        },
        "sections": [
            {
                "name": "dd_summary",
                "label": "DD Summary",
                "type": "metrics_grid",
                "description": "Completion % by workstream, total items, open items, target close.",
            },
            {
                "name": "required_documents",
                "label": "Document Checklist",
                "type": "checklist",
                "description": "All required documents with received / outstanding / waived status.",
            },
            {
                "name": "completion_status",
                "label": "Workstream Completion",
                "type": "table",
                "description": "Legal, financial, technical, ESG workstream % complete with notes.",
            },
            {
                "name": "missing_items",
                "label": "Outstanding Items",
                "type": "table",
                "description": "Items not yet received: description, owner, due date, priority.",
            },
            {
                "name": "recommendations",
                "label": "Findings & Recommendations",
                "type": "text",
                "description": "Key DD findings, risk flags, conditions precedent, and recommendations.",
            },
        ],
    },
    # ── PORTFOLIO ─────────────────────────────────────────────────────────────
    {
        "name": "Deal Memo",
        "category": ReportCategory.PORTFOLIO,
        "description": (
            "Investment committee-ready deal memorandum. Covers investment thesis, "
            "market opportunity, financial analysis (DCF, comparables, scenario "
            "analysis), risk assessment, ESG diligence summary, terms, and "
            "investment recommendation with key conditions."
        ),
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "pptx"],
            "default_format": "pdf",
            "required_parameters": ["project_id"],
            "optional_parameters": ["portfolio_id"],
            "display_hints": {
                "cover_style": "formal",
                "confidentiality_notice": True,
            },
        },
        "sections": [
            {
                "name": "investment_thesis",
                "label": "Investment Thesis",
                "type": "text",
                "description": "Thesis statement, market opportunity, and strategic fit.",
            },
            {
                "name": "project_overview",
                "label": "Company / Project Overview",
                "type": "kv",
                "description": "Stage, sector, geography, team, business model, and traction.",
            },
            {
                "name": "financial_analysis",
                "label": "Financial Analysis",
                "type": "table",
                "description": "Historical financials, DCF valuation, comparables, and scenarios.",
            },
            {
                "name": "valuation_summary",
                "label": "Valuation Summary",
                "type": "metrics_grid",
                "description": "Enterprise value, equity value, entry multiple, target return.",
            },
            {
                "name": "risk_assessment",
                "label": "Risk Assessment",
                "type": "table",
                "description": "Risk factors: category, description, severity, mitigation.",
            },
            {
                "name": "esg_overview",
                "label": "ESG Diligence",
                "type": "kv",
                "description": "ESG score, material risks, taxonomy eligibility, SDGs addressed.",
            },
            {
                "name": "recommendation",
                "label": "Recommendation & Terms",
                "type": "text",
                "description": "IC recommendation, proposed investment size, key terms, and conditions.",
            },
        ],
    },
    {
        "name": "Portfolio Valuation Summary",
        "category": ReportCategory.PORTFOLIO,
        "description": (
            "Fair value summary across the portfolio. Shows latest valuations by "
            "method (DCF, comparables, cost), mark movements quarter-over-quarter, "
            "unrealised gain/loss by holding, and sensitivity analysis. "
            "Suitable for LP reporting and audit support."
        ),
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "xlsx",
            "required_parameters": ["portfolio_id", "date_from", "date_to"],
            "display_hints": {
                "confidentiality_notice": True,
                "include_audit_trail": True,
            },
        },
        "sections": [
            {
                "name": "valuation_overview",
                "label": "Valuation Overview",
                "type": "metrics_grid",
                "description": "Total fair value, cost basis, unrealised G/L, and MOIC.",
            },
            {
                "name": "holdings_detail",
                "label": "Holdings Valuation Detail",
                "type": "table",
                "description": "Per-holding: cost, fair value, method, date, unrealised G/L, MOIC.",
            },
            {
                "name": "valuation_summary",
                "label": "Valuation by Method",
                "type": "table",
                "description": "Breakdown by valuation method: DCF, market comparables, cost.",
            },
            {
                "name": "mark_movements",
                "label": "Mark Movements (QoQ)",
                "type": "table",
                "description": "Quarter-over-quarter fair value changes by holding.",
            },
            {
                "name": "nav_summary",
                "label": "NAV Reconciliation",
                "type": "kv",
                "description": "Opening / closing NAV, management fee, performance fee, net NAV.",
            },
        ],
    },
    # ── PROJECT ───────────────────────────────────────────────────────────────
    {
        "name": "Project Status Report",
        "category": ReportCategory.PROJECT,
        "description": (
            "Detailed project status report for internal and investor audiences. "
            "Covers project overview, milestone progress (RAG status), budget vs. "
            "actuals, signal score analysis, risk register, and upcoming activities."
        ),
        "template_config": {
            "audience": "ally",
            "supported_formats": ["pdf", "xlsx", "pptx"],
            "default_format": "pdf",
            "required_parameters": ["project_id"],
            "display_hints": {"include_rag_status": True},
        },
        "sections": [
            {
                "name": "project_overview",
                "label": "Project Overview",
                "type": "kv",
                "description": "Name, stage, sector, geography, sponsor, funding target, and status.",
            },
            {
                "name": "signal_score_detail",
                "label": "Signal Score",
                "type": "metrics_grid",
                "description": "Overall signal score with dimension breakdown (viability, ESG, team…).",
            },
            {
                "name": "milestones",
                "label": "Milestone Tracker",
                "type": "checklist",
                "description": "All milestones with target date, status, and completion percentage.",
            },
            {
                "name": "budget_summary",
                "label": "Budget vs. Actuals",
                "type": "table",
                "description": "Budget items: approved amount, spend to date, variance, and notes.",
            },
            {
                "name": "risk_register",
                "label": "Risk Register",
                "type": "table",
                "description": "Current risks: description, category, likelihood, impact, mitigation.",
            },
            {
                "name": "recent_activity",
                "label": "Recent Activity",
                "type": "table",
                "description": "Latest project events, decisions, and document uploads.",
            },
        ],
    },
    {
        "name": "Investor Update",
        "category": ReportCategory.PROJECT,
        "description": (
            "Concise periodic update for investors on project progress. Covers "
            "executive summary, key highlights and achievements, financial status, "
            "ESG quick-facts, upcoming milestones, and ask (if applicable)."
        ),
        "template_config": {
            "audience": "ally",
            "supported_formats": ["pdf", "pptx"],
            "default_format": "pdf",
            "required_parameters": ["project_id"],
            "optional_parameters": ["date_from", "date_to"],
            "display_hints": {"cover_style": "modern"},
        },
        "sections": [
            {
                "name": "executive_summary",
                "label": "Executive Summary",
                "type": "text",
                "description": "Period highlights and overall project health narrative.",
            },
            {
                "name": "project_highlights",
                "label": "Key Highlights & Achievements",
                "type": "table",
                "description": "Bullet-point achievements, partnerships, and milestones hit.",
            },
            {
                "name": "financials",
                "label": "Financial Status",
                "type": "metrics_grid",
                "description": "Funding raised, runway, burn rate, and next funding milestone.",
            },
            {
                "name": "esg_overview",
                "label": "ESG & Impact Quick-Facts",
                "type": "kv",
                "description": "Carbon impact, jobs created, SDGs addressed, and reporting status.",
            },
            {
                "name": "milestones",
                "label": "Upcoming Milestones",
                "type": "table",
                "description": "Next 3–6 milestones with target dates and owners.",
            },
            {
                "name": "next_steps",
                "label": "Next Steps & Ask",
                "type": "text",
                "description": "Action items, investor asks, and closing remarks.",
            },
        ],
    },
]


def seed_templates() -> int:
    """Insert system templates idempotently. Returns count of new templates created."""
    engine = create_engine(settings.DATABASE_URL_SYNC)
    created = 0
    updated = 0

    with SyncSession(engine) as session:
        for tmpl_data in SYSTEM_TEMPLATES:
            existing = session.execute(
                select(ReportTemplate).where(
                    ReportTemplate.name == tmpl_data["name"],
                    ReportTemplate.is_system.is_(True),
                )
            ).scalar_one_or_none()

            if existing:
                # Update sections and config if the template already exists
                existing.description = tmpl_data["description"]
                existing.template_config = tmpl_data["template_config"]
                existing.sections = tmpl_data["sections"]
                existing.category = tmpl_data["category"]
                updated += 1
                logger.info("template_updated", name=tmpl_data["name"])
                continue

            template = ReportTemplate(
                org_id=None,
                name=tmpl_data["name"],
                category=tmpl_data["category"],
                description=tmpl_data["description"],
                template_config=tmpl_data["template_config"],
                sections=tmpl_data["sections"],
                is_system=True,
                version=1,
            )
            session.add(template)
            created += 1
            logger.info("template_created", name=tmpl_data["name"])

        session.commit()

    logger.info(
        "seed_complete",
        created=created,
        updated=updated,
        total=len(SYSTEM_TEMPLATES),
    )
    return created


if __name__ == "__main__":
    seed_templates()
