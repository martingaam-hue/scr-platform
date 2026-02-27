"""Seed 8 system report templates.

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

SYSTEM_TEMPLATES = [
    {
        "name": "LP Quarterly Report",
        "category": ReportCategory.PERFORMANCE,
        "description": "Comprehensive quarterly report for limited partners covering portfolio performance, NAV, cash flows, and ESG metrics.",
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx", "pptx"],
            "default_format": "pdf",
            "required_parameters": ["portfolio_id", "date_from", "date_to"],
        },
        "sections": [
            {"name": "executive_summary", "label": "Executive Summary"},
            {"name": "portfolio_performance", "label": "Portfolio Performance"},
            {"name": "nav_summary", "label": "NAV Summary"},
            {"name": "cash_flows", "label": "Cash Flows"},
            {"name": "esg_overview", "label": "ESG Overview"},
        ],
    },
    {
        "name": "Portfolio Performance Report",
        "category": ReportCategory.PERFORMANCE,
        "description": "Detailed portfolio analytics including holdings breakdown, performance attribution, and benchmark comparison.",
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "xlsx",
            "required_parameters": ["portfolio_id"],
        },
        "sections": [
            {"name": "performance_summary", "label": "Performance Summary"},
            {"name": "holdings_detail", "label": "Holdings Detail"},
            {"name": "attribution", "label": "Attribution Analysis"},
            {"name": "benchmark_comparison", "label": "Benchmark Comparison"},
        ],
    },
    {
        "name": "ESG Impact Report",
        "category": ReportCategory.ESG,
        "description": "Environmental, social, and governance metrics including carbon reduction, taxonomy alignment, and impact KPIs.",
        "template_config": {
            "audience": "both",
            "supported_formats": ["pdf", "pptx"],
            "default_format": "pdf",
            "required_parameters": ["date_from", "date_to"],
        },
        "sections": [
            {"name": "carbon_metrics", "label": "Carbon Metrics"},
            {"name": "esg_scores", "label": "ESG Scores"},
            {"name": "taxonomy_alignment", "label": "EU Taxonomy Alignment"},
            {"name": "impact_kpis", "label": "Impact KPIs"},
        ],
    },
    {
        "name": "Project Status Report",
        "category": ReportCategory.PROJECT,
        "description": "Project overview with milestones, budget tracking, signal score analysis, and recent activity log.",
        "template_config": {
            "audience": "ally",
            "supported_formats": ["pdf", "xlsx", "pptx"],
            "default_format": "pdf",
            "required_parameters": ["project_id"],
        },
        "sections": [
            {"name": "project_overview", "label": "Project Overview"},
            {"name": "milestones", "label": "Milestones"},
            {"name": "budget_summary", "label": "Budget Summary"},
            {"name": "signal_score", "label": "Signal Score"},
            {"name": "recent_activity", "label": "Recent Activity"},
        ],
    },
    {
        "name": "Deal Memo",
        "category": ReportCategory.PORTFOLIO,
        "description": "Investment committee-ready deal memo with thesis, financial analysis, risk assessment, and recommendation.",
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "pptx"],
            "default_format": "pdf",
            "required_parameters": ["project_id", "portfolio_id"],
        },
        "sections": [
            {"name": "investment_thesis", "label": "Investment Thesis"},
            {"name": "financial_analysis", "label": "Financial Analysis"},
            {"name": "risk_assessment", "label": "Risk Assessment"},
            {"name": "recommendation", "label": "Recommendation"},
        ],
    },
    {
        "name": "SFDR Compliance Report",
        "category": ReportCategory.COMPLIANCE,
        "description": "SFDR regulatory disclosure including classification, PAI indicators, and sustainable investment percentages.",
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "pdf",
            "required_parameters": ["portfolio_id", "date_from", "date_to"],
        },
        "sections": [
            {"name": "sfdr_classification", "label": "SFDR Classification"},
            {"name": "pai_indicators", "label": "PAI Indicators"},
            {"name": "sustainable_investment_pct", "label": "Sustainable Investment %"},
            {"name": "disclosures", "label": "Disclosures"},
        ],
    },
    {
        "name": "Investor Update",
        "category": ReportCategory.PROJECT,
        "description": "Periodic update for investors on project progress, key highlights, financial status, and upcoming milestones.",
        "template_config": {
            "audience": "ally",
            "supported_formats": ["pdf", "pptx"],
            "default_format": "pdf",
            "required_parameters": ["project_id"],
        },
        "sections": [
            {"name": "executive_summary", "label": "Executive Summary"},
            {"name": "project_highlights", "label": "Project Highlights"},
            {"name": "financials", "label": "Financials"},
            {"name": "next_steps", "label": "Next Steps"},
        ],
    },
    {
        "name": "Due Diligence Checklist",
        "category": ReportCategory.COMPLIANCE,
        "description": "Comprehensive checklist tracking required documents, completion status, gaps, and recommendations.",
        "template_config": {
            "audience": "both",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "xlsx",
            "required_parameters": ["project_id"],
        },
        "sections": [
            {"name": "required_documents", "label": "Required Documents"},
            {"name": "completion_status", "label": "Completion Status"},
            {"name": "missing_items", "label": "Missing Items"},
            {"name": "recommendations", "label": "Recommendations"},
        ],
    },
]


def seed_templates() -> int:
    """Insert system templates idempotently. Returns count of new templates created."""
    engine = create_engine(settings.DATABASE_URL_SYNC)
    created = 0

    with SyncSession(engine) as session:
        for tmpl_data in SYSTEM_TEMPLATES:
            exists = session.execute(
                select(ReportTemplate).where(
                    ReportTemplate.name == tmpl_data["name"],
                    ReportTemplate.is_system.is_(True),
                )
            ).scalar_one_or_none()

            if exists:
                logger.info("template_exists", name=tmpl_data["name"])
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

    logger.info("seed_complete", created=created, total=len(SYSTEM_TEMPLATES))
    return created


if __name__ == "__main__":
    seed_templates()
