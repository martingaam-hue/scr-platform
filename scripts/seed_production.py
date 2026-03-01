#!/usr/bin/env python3
"""Production seed script — SCR Platform.

Seeds all required reference data: report templates, legal templates,
prompt registry entries, gamification badges, industry taxonomy, and
feature flags.

Usage:
    # From the repo root:
    cd apps/api && poetry run python ../../scripts/seed_production.py
    cd apps/api && poetry run python ../../scripts/seed_production.py --dry-run
    cd apps/api && poetry run python ../../scripts/seed_production.py --demo

Flags:
    --dry-run   Print what would be seeded without committing anything.
    --demo      Also seed demo organisations and projects (staging / demo env only).
"""

from __future__ import annotations

import argparse
import sys
import os

# Allow running from the repo root or from apps/api/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from app.core.config import settings
from app.models.enums import LegalDocumentType, ReportCategory
from app.models.gamification import Badge
from app.models.launch import FeatureFlag
from app.models.legal import LegalTemplate
from app.models.ai import PromptTemplate
from app.models.reporting import ReportTemplate
from app.models.taxonomy import IndustryTaxonomy

# Import Base so all tables are registered before create_engine is called.
from app.core.database import Base  # noqa: F401

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as SyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------

# ── Report Templates ────────────────────────────────────────────────────────

REPORT_TEMPLATES = [
    {
        "name": "LP Quarterly Report",
        "category": ReportCategory.PERFORMANCE,
        "description": "Standard LP quarterly performance report",
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
        "is_system": True,
        "version": 1,
    },
    {
        "name": "LP Annual Report",
        "category": ReportCategory.PERFORMANCE,
        "description": "Annual LP report with full year performance",
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx", "pptx"],
            "default_format": "pdf",
            "required_parameters": ["portfolio_id", "year"],
        },
        "sections": [
            {"name": "executive_summary", "label": "Executive Summary"},
            {"name": "annual_performance", "label": "Annual Performance"},
            {"name": "portfolio_composition", "label": "Portfolio Composition"},
            {"name": "returns_analysis", "label": "Returns Analysis"},
            {"name": "esg_impact", "label": "ESG Impact"},
            {"name": "outlook", "label": "Outlook"},
        ],
        "is_system": True,
        "version": 1,
    },
    {
        "name": "Project Summary",
        "category": ReportCategory.PROJECT,
        "description": "Project executive summary",
        "template_config": {
            "audience": "both",
            "supported_formats": ["pdf", "pptx"],
            "default_format": "pdf",
            "required_parameters": ["project_id"],
        },
        "sections": [
            {"name": "project_overview", "label": "Project Overview"},
            {"name": "financial_highlights", "label": "Financial Highlights"},
            {"name": "signal_score", "label": "Signal Score"},
            {"name": "key_risks", "label": "Key Risks"},
        ],
        "is_system": True,
        "version": 1,
    },
    {
        "name": "Risk Report",
        "category": ReportCategory.COMPLIANCE,
        "description": "Comprehensive risk assessment report",
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "pdf",
            "required_parameters": ["project_id"],
        },
        "sections": [
            {"name": "risk_summary", "label": "Risk Summary"},
            {"name": "risk_matrix", "label": "Risk Matrix"},
            {"name": "mitigation_strategies", "label": "Mitigation Strategies"},
            {"name": "residual_risks", "label": "Residual Risks"},
        ],
        "is_system": True,
        "version": 1,
    },
    {
        "name": "ESG Report",
        "category": ReportCategory.ESG,
        "description": "ESG performance and impact report",
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
            {"name": "sdg_mapping", "label": "SDG Mapping"},
        ],
        "is_system": True,
        "version": 1,
    },
    {
        "name": "Portfolio Overview",
        "category": ReportCategory.PORTFOLIO,
        "description": "Portfolio-wide performance overview",
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx", "pptx"],
            "default_format": "pdf",
            "required_parameters": ["portfolio_id"],
        },
        "sections": [
            {"name": "portfolio_summary", "label": "Portfolio Summary"},
            {"name": "holdings_breakdown", "label": "Holdings Breakdown"},
            {"name": "performance_attribution", "label": "Performance Attribution"},
            {"name": "geographic_distribution", "label": "Geographic Distribution"},
        ],
        "is_system": True,
        "version": 1,
    },
    {
        "name": "Covenant Status",
        "category": ReportCategory.COMPLIANCE,
        "description": "Covenant monitoring and compliance status",
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "xlsx",
            "required_parameters": ["portfolio_id", "date_from", "date_to"],
        },
        "sections": [
            {"name": "covenant_summary", "label": "Covenant Summary"},
            {"name": "financial_covenants", "label": "Financial Covenants"},
            {"name": "operational_covenants", "label": "Operational Covenants"},
            {"name": "breach_history", "label": "Breach History"},
            {"name": "remediation_actions", "label": "Remediation Actions"},
        ],
        "is_system": True,
        "version": 1,
    },
    {
        "name": "Pacing Report",
        "category": ReportCategory.PORTFOLIO,
        "description": "Capital deployment pacing and J-curve analysis",
        "template_config": {
            "audience": "investor",
            "supported_formats": ["pdf", "xlsx"],
            "default_format": "pdf",
            "required_parameters": ["portfolio_id", "date_from", "date_to"],
        },
        "sections": [
            {"name": "deployment_summary", "label": "Deployment Summary"},
            {"name": "j_curve", "label": "J-Curve Analysis"},
            {"name": "vintage_analysis", "label": "Vintage Analysis"},
            {"name": "remaining_capacity", "label": "Remaining Capacity"},
        ],
        "is_system": True,
        "version": 1,
    },
]

# ── Legal Templates ─────────────────────────────────────────────────────────

LEGAL_TEMPLATES = [
    {
        "name": "NDA (Standard)",
        "doc_type": LegalDocumentType.NDA,
        "content": (
            "NON-DISCLOSURE AGREEMENT\n\n"
            "This Non-Disclosure Agreement (\"Agreement\") is entered into as of {{effective_date}} "
            "between {{party_a}} (\"Disclosing Party\") and {{party_b}} (\"Receiving Party\").\n\n"
            "1. CONFIDENTIAL INFORMATION\n"
            "The Receiving Party agrees to hold in strict confidence all Confidential Information "
            "received from the Disclosing Party.\n\n"
            "2. TERM\n"
            "This Agreement shall remain in effect for a period of {{term_years}} years.\n\n"
            "[ADDITIONAL STANDARD NDA CLAUSES TO BE INSERTED]\n"
        ),
        "variables": {
            "effective_date": "string",
            "party_a": "string",
            "party_b": "string",
            "term_years": "integer",
        },
        "is_system": True,
        "version": 1,
    },
    {
        "name": "Term Sheet",
        "doc_type": LegalDocumentType.TERM_SHEET,
        "content": (
            "TERM SHEET\n\n"
            "Project: {{project_name}}\n"
            "Date: {{date}}\n"
            "Investor: {{investor_name}}\n\n"
            "PROPOSED INVESTMENT TERMS\n\n"
            "Investment Amount: {{investment_amount}}\n"
            "Instrument: {{instrument_type}}\n"
            "Valuation: {{valuation}}\n"
            "Use of Proceeds: {{use_of_proceeds}}\n\n"
            "[ADDITIONAL TERM SHEET PROVISIONS TO BE INSERTED]\n\n"
            "This term sheet is non-binding and subject to final due diligence and definitive agreements."
        ),
        "variables": {
            "project_name": "string",
            "date": "string",
            "investor_name": "string",
            "investment_amount": "string",
            "instrument_type": "string",
            "valuation": "string",
            "use_of_proceeds": "string",
        },
        "is_system": True,
        "version": 1,
    },
    {
        "name": "Investment Agreement",
        "doc_type": LegalDocumentType.SUBSCRIPTION_AGREEMENT,
        "content": (
            "INVESTMENT AGREEMENT\n\n"
            "This Investment Agreement is entered into as of {{effective_date}} between "
            "{{investor_name}} (\"Investor\") and {{company_name}} (\"Company\").\n\n"
            "1. SUBSCRIPTION\n"
            "The Investor hereby subscribes for {{units}} units/shares at a price of "
            "{{price_per_unit}} per unit for a total investment of {{total_investment}}.\n\n"
            "2. CONDITIONS PRECEDENT\n"
            "[CONDITIONS TO BE SPECIFIED]\n\n"
            "3. REPRESENTATIONS AND WARRANTIES\n"
            "[REPRESENTATIONS TO BE INSERTED]\n\n"
            "[ADDITIONAL AGREEMENT PROVISIONS]\n"
        ),
        "variables": {
            "effective_date": "string",
            "investor_name": "string",
            "company_name": "string",
            "units": "number",
            "price_per_unit": "string",
            "total_investment": "string",
        },
        "is_system": True,
        "version": 1,
    },
    {
        "name": "Power Purchase Agreement",
        "doc_type": LegalDocumentType.SIDE_LETTER,
        "content": (
            "POWER PURCHASE AGREEMENT\n\n"
            "This Power Purchase Agreement (\"PPA\") is entered into as of {{effective_date}} "
            "between {{seller_name}} (\"Seller\") and {{buyer_name}} (\"Buyer\").\n\n"
            "PROJECT DETAILS\n"
            "Project Name: {{project_name}}\n"
            "Installed Capacity: {{capacity_mw}} MW\n"
            "Location: {{location}}\n\n"
            "1. TERM: {{term_years}} years commencing on {{commencement_date}}\n\n"
            "2. PRICE: {{price_per_mwh}} per MWh ({{price_escalation}}% annual escalation)\n\n"
            "3. DELIVERY POINT: {{delivery_point}}\n\n"
            "[ADDITIONAL PPA PROVISIONS TO BE INSERTED]\n"
        ),
        "variables": {
            "effective_date": "string",
            "seller_name": "string",
            "buyer_name": "string",
            "project_name": "string",
            "capacity_mw": "number",
            "location": "string",
            "term_years": "integer",
            "commencement_date": "string",
            "price_per_mwh": "string",
            "price_escalation": "number",
            "delivery_point": "string",
        },
        "is_system": True,
        "version": 1,
    },
    {
        "name": "Development Services Agreement",
        "doc_type": LegalDocumentType.AMENDMENT,
        "content": (
            "DEVELOPMENT SERVICES AGREEMENT\n\n"
            "This Development Services Agreement is entered into as of {{effective_date}} "
            "between {{client_name}} (\"Client\") and {{developer_name}} (\"Developer\").\n\n"
            "1. SCOPE OF SERVICES\n"
            "Developer agrees to provide development services for {{project_name}} including:\n"
            "{{scope_of_services}}\n\n"
            "2. FEES\n"
            "Total Development Fee: {{total_fee}}\n"
            "Payment Schedule: {{payment_schedule}}\n\n"
            "3. TERM\n"
            "Commencement Date: {{start_date}}\n"
            "Target Completion: {{end_date}}\n\n"
            "[ADDITIONAL DSA PROVISIONS TO BE INSERTED]\n"
        ),
        "variables": {
            "effective_date": "string",
            "client_name": "string",
            "developer_name": "string",
            "project_name": "string",
            "scope_of_services": "string",
            "total_fee": "string",
            "payment_schedule": "string",
            "start_date": "string",
            "end_date": "string",
        },
        "is_system": True,
        "version": 1,
    },
]

# ── Prompt Registry ─────────────────────────────────────────────────────────
# Field mapping:  task_type, version (int), name, system_prompt,
#                 user_prompt_template, model_override, is_active

PROMPT_TEMPLATES = [
    {
        "task_type": "score_quality",
        "version": 1,
        "name": "Document Quality Scorer v1",
        "system_prompt": (
            "You are an expert renewable energy investment analyst evaluating "
            "project documentation quality."
        ),
        "user_prompt_template": (
            "Evaluate the quality of this document for the criterion '{{criterion_name}}':\n\n"
            "{{document_text}}\n\n"
            "Respond with JSON: {\"score\": 0-100, \"rationale\": \"...\", \"key_issues\": []}"
        ),
        "model_override": "claude-opus-4-20250514",
        "is_active": True,
    },
    {
        "task_type": "deal_screening",
        "version": 1,
        "name": "Deal Screener v1",
        "system_prompt": (
            "You are a senior investment analyst screening renewable energy deals."
        ),
        "user_prompt_template": (
            "Screen this deal for investment relevance:\n\n{{deal_text}}\n\n"
            "Provide: executive summary, investment highlights, red flags, "
            "recommendation (pass/review/reject), confidence score."
        ),
        "model_override": "claude-sonnet-4-20250514",
        "is_active": True,
    },
    {
        "task_type": "investment_memo",
        "version": 1,
        "name": "Investment Memo Writer v1",
        "system_prompt": (
            "You are a managing director writing institutional-quality investment memoranda."
        ),
        "user_prompt_template": (
            "Write an investment memo for:\n\n"
            "Project: {{project_name}}\n"
            "Type: {{asset_type}}\n"
            "Capacity: {{capacity_mw}} MW\n"
            "Location: {{geography}}\n\n"
            "Key data: {{project_data}}\n\n"
            "Include: Executive Summary, Investment Thesis, Financial Analysis, "
            "Risk Factors, ESG Considerations, Recommendation."
        ),
        "model_override": "claude-opus-4-20250514",
        "is_active": True,
    },
    {
        "task_type": "risk_mitigation",
        "version": 1,
        "name": "Risk Mitigation Analyst v1",
        "system_prompt": (
            "You are a risk management expert for renewable energy investments."
        ),
        "user_prompt_template": (
            "Identify and analyze risks for this project:\n\n{{project_context}}\n\n"
            "For each risk provide: category, severity (1-5), likelihood (1-5), "
            "description, mitigation strategy."
        ),
        "model_override": "claude-sonnet-4-20250514",
        "is_active": True,
    },
    {
        "task_type": "meeting_preparation",
        "version": 1,
        "name": "Meeting Prep Briefer v1",
        "system_prompt": (
            "You are an expert investment professional preparing for investor meetings."
        ),
        "user_prompt_template": (
            "Prepare a comprehensive briefing for a meeting about:\n\n"
            "Project: {{project_name}}\n"
            "Investor profile: {{investor_profile}}\n"
            "Project stage: {{stage}}\n\n"
            "Include: key talking points, anticipated questions, financial highlights, "
            "risk discussion points."
        ),
        "model_override": "claude-sonnet-4-20250514",
        "is_active": True,
    },
    {
        "task_type": "legal_document_review",
        "version": 1,
        "name": "Legal Document Reviewer v1",
        "system_prompt": (
            "You are an expert legal reviewer specializing in renewable energy "
            "and infrastructure contracts."
        ),
        "user_prompt_template": (
            "Review this legal document:\n\n{{document_text}}\n\n"
            "Identify: key terms, unusual clauses, missing standard provisions, "
            "risk flags, recommendations."
        ),
        "model_override": "claude-opus-4-20250514",
        "is_active": True,
    },
    {
        "task_type": "legal_document_completion",
        "version": 1,
        "name": "Legal Document Completer v1",
        "system_prompt": (
            "You are a legal expert specializing in renewable energy contracts."
        ),
        "user_prompt_template": (
            "Complete the missing sections of this document:\n\n{{document_text}}\n\n"
            "Context: {{project_context}}\n\n"
            "Provide the completed sections maintaining consistent legal language and format."
        ),
        "model_override": "claude-opus-4-20250514",
        "is_active": True,
    },
    {
        "task_type": "review_contract",
        "version": 1,
        "name": "Contract Clause Reviewer v1",
        "system_prompt": (
            "You are a contract review specialist for infrastructure investments."
        ),
        "user_prompt_template": (
            "Review this contract clause:\n\n{{clause_text}}\n\n"
            "Assess: legal soundness, commercial fairness, risk allocation, suggested amendments."
        ),
        "model_override": "gemini-3.1-pro",
        "is_active": True,
    },
    {
        "task_type": "generate_lp_narrative",
        "version": 1,
        "name": "LP Narrative Writer v1",
        "system_prompt": (
            "You are an investor relations expert writing institutional LP reports."
        ),
        "user_prompt_template": (
            "Write the narrative section for this LP report:\n\n"
            "Period: {{period}}\n"
            "Fund: {{fund_name}}\n"
            "Portfolio performance: {{performance_data}}\n"
            "Key events: {{events}}\n\n"
            "Write in a professional, informative tone appropriate for institutional investors."
        ),
        "model_override": "claude-sonnet-4-20250514",
        "is_active": True,
    },
    {
        "task_type": "classify_document",
        "version": 1,
        "name": "Document Classifier v1",
        "system_prompt": (
            "You are a document classification expert for investment due diligence."
        ),
        "user_prompt_template": (
            "Classify this document:\n\n{{document_text}}\n\n"
            "Respond with JSON: {\"document_type\": \"...\", \"sub_category\": \"...\", "
            "\"confidence\": 0.0-1.0, \"key_entities\": []}"
        ),
        "model_override": "grok-4.1-fast",
        "is_active": True,
    },
    {
        "task_type": "generate_digest",
        "version": 1,
        "name": "Digest Summariser v1",
        "system_prompt": (
            "You are a concise news summarizer for investment professionals."
        ),
        "user_prompt_template": (
            "Summarize these updates for a weekly digest:\n\n{{updates}}\n\n"
            "Create a concise, actionable summary organized by topic. "
            "Highlight what matters most."
        ),
        "model_override": "deepseek-v3",
        "is_active": True,
    },
    {
        "task_type": "esg_assessment",
        "version": 1,
        "name": "ESG Assessor v1",
        "system_prompt": (
            "You are an ESG specialist evaluating renewable energy projects."
        ),
        "user_prompt_template": (
            "Perform an ESG assessment for:\n\n"
            "Project: {{project_name}}\n"
            "Type: {{asset_type}}\n"
            "Location: {{geography}}\n"
            "Data: {{project_data}}\n\n"
            "Score Environmental (0-100), Social (0-100), Governance (0-100). "
            "Provide detailed rationale for each."
        ),
        "model_override": "claude-sonnet-4-20250514",
        "is_active": True,
    },
    {
        "task_type": "expert_insight_enrichment",
        "version": 1,
        "name": "Expert Insight Enricher v1",
        "system_prompt": (
            "You are an investment intelligence analyst enriching expert insights."
        ),
        "user_prompt_template": (
            "Analyze this expert note and extract structured intelligence:\n\n"
            "{{note_text}}\n"
            "Source: {{expert_profile}}\n\n"
            "Extract: key claims, risk indicators, market signals, actionable insights, "
            "confidence level."
        ),
        "model_override": "claude-sonnet-4-20250514",
        "is_active": True,
    },
    {
        "task_type": "ai_redaction",
        "version": 1,
        "name": "AI Redaction Expert v1",
        "system_prompt": (
            "You are a document redaction expert identifying sensitive information."
        ),
        "user_prompt_template": (
            "Identify all sensitive information requiring redaction in:\n\n{{document_text}}\n\n"
            "Return JSON array of: [{\"type\": \"PII|COMMERCIAL|LEGAL|FINANCIAL\", "
            "\"text\": \"...\", \"start\": int, \"end\": int, \"confidence\": 0-1}]"
        ),
        "model_override": "claude-opus-4-20250514",
        "is_active": True,
    },
    {
        "task_type": "signal_score_explanation",
        "version": 1,
        "name": "Signal Score Explainer v1",
        "system_prompt": (
            "You are a signal score analyst explaining investment quality assessments."
        ),
        "user_prompt_template": (
            "Explain the signal score for this project:\n\n"
            "Project: {{project_name}}\n"
            "Score: {{total_score}}\n"
            "Dimension scores: {{dimension_scores}}\n"
            "Documents analyzed: {{doc_count}}\n\n"
            "Write a clear explanation of what drove this score and what could improve it."
        ),
        "model_override": "claude-sonnet-4-20250514",
        "is_active": True,
    },
    {
        "task_type": "market_intelligence",
        "version": 1,
        "name": "Market Intelligence Analyst v1",
        "system_prompt": (
            "You are a renewable energy market analyst."
        ),
        "user_prompt_template": (
            "Analyze market conditions for:\n\n"
            "Asset type: {{asset_type}}\n"
            "Geography: {{geography}}\n"
            "Market data: {{market_data}}\n\n"
            "Provide: market overview, comparable transactions, pricing benchmarks, market outlook."
        ),
        "model_override": "claude-sonnet-4-20250514",
        "is_active": True,
    },
]

# ── Gamification Badges ─────────────────────────────────────────────────────
# Badge model fields: slug, name, description, icon, category, criteria (JSONB),
#                     points, rarity

BADGES = [
    {
        "slug": "first_steps",
        "name": "First Steps",
        "description": "Completed onboarding",
        "icon": "🎯",
        "category": "onboarding",
        "criteria": {"event": "onboarding_complete"},
        "points": 100,
        "rarity": "common",
    },
    {
        "slug": "document_master",
        "name": "Document Master",
        "description": "Uploaded 10+ documents",
        "icon": "📄",
        "category": "data_room",
        "criteria": {"event": "document_upload", "count": 10},
        "points": 250,
        "rarity": "uncommon",
    },
    {
        "slug": "due_diligence_pro",
        "name": "Due Diligence Pro",
        "description": "Completed full due diligence checklist",
        "icon": "🔍",
        "category": "due_diligence",
        "criteria": {"event": "dd_item_complete", "count": 10},
        "points": 500,
        "rarity": "rare",
    },
    {
        "slug": "signal_score_master",
        "name": "Signal Score Master",
        "description": "Achieved Signal Score > 80",
        "icon": "⭐",
        "category": "signal_score",
        "criteria": {"signal_score_min": 80},
        "points": 750,
        "rarity": "epic",
    },
    {
        "slug": "deal_closer",
        "name": "Deal Closer",
        "description": "First successful match with investor",
        "icon": "🤝",
        "category": "matching",
        "criteria": {"event": "investor_match", "count": 1},
        "points": 1000,
        "rarity": "rare",
    },
    {
        "slug": "esg_champion",
        "name": "ESG Champion",
        "description": "ESG score > 85 on a project",
        "icon": "🌱",
        "category": "signal_score",
        "criteria": {"signal_score_min": 85},
        "points": 500,
        "rarity": "rare",
    },
    {
        "slug": "data_room_expert",
        "name": "Data Room Expert",
        "description": "Created a complete data room",
        "icon": "🏛️",
        "category": "data_room",
        "criteria": {"event": "document_upload", "count": 5},
        "points": 300,
        "rarity": "uncommon",
    },
    {
        "slug": "certified_project",
        "name": "Certified Project",
        "description": "Project achieved certification",
        "icon": "✅",
        "category": "certification",
        "criteria": {"event": "certification_earned"},
        "points": 1500,
        "rarity": "legendary",
    },
    {
        "slug": "portfolio_builder",
        "name": "Portfolio Builder",
        "description": "3+ projects in portfolio",
        "icon": "📊",
        "category": "onboarding",
        "criteria": {"event": "onboarding_complete", "count": 1},
        "points": 400,
        "rarity": "uncommon",
    },
    {
        "slug": "early_adopter",
        "name": "Early Adopter",
        "description": "One of the first 100 users",
        "icon": "🚀",
        "category": "onboarding",
        "criteria": {"event": "onboarding_complete"},
        "points": 200,
        "rarity": "common",
    },
    {
        "slug": "active_investor",
        "name": "Active Investor",
        "description": "Evaluated 20+ projects",
        "icon": "💼",
        "category": "matching",
        "criteria": {"event": "investor_match", "count": 20},
        "points": 600,
        "rarity": "rare",
    },
    {
        "slug": "speed_reviewer",
        "name": "Speed Reviewer",
        "description": "Completed Q&A within SLA 10 times",
        "icon": "⚡",
        "category": "due_diligence",
        "criteria": {"event": "dd_item_complete", "count": 10},
        "points": 300,
        "rarity": "uncommon",
    },
]

# ── Industry Taxonomy ────────────────────────────────────────────────────────
# IndustryTaxonomy model fields: code, parent_code, name, level, is_leaf, meta

def _build_taxonomy_rows(tree: list[dict], parent_code: str | None = None, level: int = 1) -> list[dict]:
    """Flatten the nested taxonomy tree into a list of DB row dicts."""
    rows = []
    for node in tree:
        children = node.get("children", [])
        is_leaf = len(children) == 0
        row = {
            "code": node["slug"],
            "parent_code": parent_code,
            "name": node["name"],
            "level": level,
            "is_leaf": is_leaf,
            "meta": {},
        }
        rows.append(row)
        if children:
            rows.extend(_build_taxonomy_rows(children, parent_code=node["slug"], level=level + 1))
    return rows


_TAXONOMY_TREE = [
    {
        "name": "Renewable Energy",
        "slug": "renewable_energy",
        "children": [
            {"name": "Solar", "slug": "solar", "children": [
                {"name": "Utility Scale Solar", "slug": "utility_solar"},
                {"name": "Distributed Solar", "slug": "distributed_solar"},
                {"name": "Floating Solar", "slug": "floating_solar"},
            ]},
            {"name": "Wind", "slug": "wind", "children": [
                {"name": "Onshore Wind", "slug": "onshore_wind"},
                {"name": "Offshore Wind", "slug": "offshore_wind"},
            ]},
            {"name": "Hydro", "slug": "hydro", "children": [
                {"name": "Run of River", "slug": "run_of_river"},
                {"name": "Reservoir", "slug": "reservoir"},
            ]},
            {"name": "Biomass", "slug": "biomass"},
            {"name": "Geothermal", "slug": "geothermal"},
            {"name": "Battery Storage", "slug": "bess"},
            {"name": "Hydrogen", "slug": "hydrogen"},
        ],
    },
    {
        "name": "Infrastructure",
        "slug": "infrastructure",
        "children": [
            {"name": "Transport", "slug": "transport"},
            {"name": "Digital Infrastructure", "slug": "digital_infrastructure"},
            {"name": "Social Infrastructure", "slug": "social_infrastructure"},
            {"name": "Energy Efficiency", "slug": "energy_efficiency"},
        ],
    },
    {
        "name": "Real Estate",
        "slug": "real_estate",
        "children": [
            {"name": "Residential", "slug": "residential_re"},
            {"name": "Commercial", "slug": "commercial_re"},
            {"name": "Industrial", "slug": "industrial_re"},
        ],
    },
    {
        "name": "Private Equity",
        "slug": "private_equity",
        "children": [
            {"name": "Growth Equity", "slug": "growth_equity"},
            {"name": "Buyout", "slug": "buyout"},
            {"name": "Venture Capital", "slug": "venture_capital"},
        ],
    },
    {
        "name": "Private Credit",
        "slug": "private_credit",
        "children": [
            {"name": "Senior Secured", "slug": "senior_secured"},
            {"name": "Mezzanine", "slug": "mezzanine"},
            {"name": "Distressed", "slug": "distressed"},
        ],
    },
]

TAXONOMY_ROWS = _build_taxonomy_rows(_TAXONOMY_TREE)

# ── Feature Flags ────────────────────────────────────────────────────────────
# FeatureFlag model fields: name, description, enabled_globally, rollout_pct

FEATURE_FLAGS = [
    {"name": "phase_b_data_moat", "description": "Phase B: Data Moat", "enabled_globally": True, "rollout_pct": 100},
    {"name": "phase_c_enterprise", "description": "Phase C: Enterprise Features", "enabled_globally": True, "rollout_pct": 100},
    {"name": "phase_d_competitive", "description": "Phase D: Competitive Edge", "enabled_globally": True, "rollout_pct": 100},
    {"name": "phase_e_growth", "description": "Phase E: Growth", "enabled_globally": True, "rollout_pct": 100},
    {"name": "ralph_ai", "description": "Ralph AI Assistant", "enabled_globally": True, "rollout_pct": 100},
    {"name": "blockchain_audit", "description": "Blockchain Audit Trail", "enabled_globally": True, "rollout_pct": 100},
    {"name": "comps_valuation", "description": "Comps-based Valuation", "enabled_globally": True, "rollout_pct": 100},
    {"name": "excel_addin", "description": "Excel Add-in", "enabled_globally": True, "rollout_pct": 100},
    {"name": "demo_data", "description": "Demo Data Mode", "enabled_globally": False, "rollout_pct": 0},
    {"name": "waitlist", "description": "Waitlist / Beta Access", "enabled_globally": False, "rollout_pct": 0},
    {"name": "white_label", "description": "White-Label Branding", "enabled_globally": True, "rollout_pct": 100},
    {"name": "expert_insights", "description": "Expert Insights", "enabled_globally": True, "rollout_pct": 100},
    {"name": "ai_redaction", "description": "AI-Powered Redaction", "enabled_globally": True, "rollout_pct": 100},
    {"name": "score_backtesting", "description": "Score Backtesting", "enabled_globally": True, "rollout_pct": 100},
    {"name": "crm_hubspot", "description": "HubSpot CRM Integration", "enabled_globally": True, "rollout_pct": 100},
    {"name": "crm_salesforce", "description": "Salesforce CRM Integration", "enabled_globally": True, "rollout_pct": 100},
]

# ---------------------------------------------------------------------------
# Seeder functions
# ---------------------------------------------------------------------------


def seed_report_templates(session: SyncSession, dry_run: bool) -> int:
    created = 0
    for tmpl in REPORT_TEMPLATES:
        existing = session.execute(
            select(ReportTemplate).where(
                ReportTemplate.name == tmpl["name"],
                ReportTemplate.is_system.is_(True),
            )
        ).scalar_one_or_none()
        if existing:
            print(f"  [skip]    ReportTemplate '{tmpl['name']}' already exists")
            continue
        print(f"  [create]  ReportTemplate '{tmpl['name']}'")
        if not dry_run:
            session.add(ReportTemplate(
                org_id=None,
                name=tmpl["name"],
                category=tmpl["category"],
                description=tmpl["description"],
                template_config=tmpl["template_config"],
                sections=tmpl["sections"],
                is_system=True,
                version=tmpl["version"],
            ))
        created += 1
    return created


def seed_legal_templates(session: SyncSession, dry_run: bool) -> int:
    created = 0
    for tmpl in LEGAL_TEMPLATES:
        existing = session.execute(
            select(LegalTemplate).where(
                LegalTemplate.name == tmpl["name"],
                LegalTemplate.is_system.is_(True),
            )
        ).scalar_one_or_none()
        if existing:
            print(f"  [skip]    LegalTemplate '{tmpl['name']}' already exists")
            continue
        print(f"  [create]  LegalTemplate '{tmpl['name']}'")
        if not dry_run:
            session.add(LegalTemplate(
                org_id=None,
                name=tmpl["name"],
                doc_type=tmpl["doc_type"],
                content=tmpl["content"],
                variables=tmpl["variables"],
                is_system=True,
                version=tmpl["version"],
            ))
        created += 1
    return created


def seed_prompt_templates(session: SyncSession, dry_run: bool) -> int:
    created = 0
    for tmpl in PROMPT_TEMPLATES:
        existing = session.execute(
            select(PromptTemplate).where(
                PromptTemplate.task_type == tmpl["task_type"],
                PromptTemplate.version == tmpl["version"],
            )
        ).scalar_one_or_none()
        if existing:
            print(f"  [skip]    PromptTemplate '{tmpl['task_type']}' v{tmpl['version']} already exists")
            continue
        print(f"  [create]  PromptTemplate '{tmpl['task_type']}' v{tmpl['version']}")
        if not dry_run:
            session.add(PromptTemplate(
                task_type=tmpl["task_type"],
                version=tmpl["version"],
                name=tmpl["name"],
                system_prompt=tmpl["system_prompt"],
                user_prompt_template=tmpl["user_prompt_template"],
                model_override=tmpl["model_override"],
                is_active=tmpl["is_active"],
                traffic_percentage=100,
                variables_schema={},
            ))
        created += 1
    return created


def seed_badges(session: SyncSession, dry_run: bool) -> int:
    created = 0
    for badge_data in BADGES:
        existing = session.execute(
            select(Badge).where(Badge.slug == badge_data["slug"])
        ).scalar_one_or_none()
        if existing:
            print(f"  [skip]    Badge '{badge_data['slug']}' already exists")
            continue
        print(f"  [create]  Badge '{badge_data['slug']}' ({badge_data['name']})")
        if not dry_run:
            session.add(Badge(
                slug=badge_data["slug"],
                name=badge_data["name"],
                description=badge_data["description"],
                icon=badge_data["icon"],
                category=badge_data["category"],
                criteria=badge_data["criteria"],
                points=badge_data["points"],
                rarity=badge_data["rarity"],
            ))
        created += 1
    return created


def seed_taxonomy(session: SyncSession, dry_run: bool) -> int:
    created = 0
    for row in TAXONOMY_ROWS:
        existing = session.execute(
            select(IndustryTaxonomy).where(IndustryTaxonomy.code == row["code"])
        ).scalar_one_or_none()
        if existing:
            print(f"  [skip]    Taxonomy '{row['code']}' already exists")
            continue
        indent = "  " * (row["level"] - 1)
        print(f"  [create]  Taxonomy {indent}'{row['code']}' — {row['name']}")
        if not dry_run:
            session.add(IndustryTaxonomy(
                code=row["code"],
                parent_code=row["parent_code"],
                name=row["name"],
                level=row["level"],
                is_leaf=row["is_leaf"],
                meta=row["meta"],
            ))
        created += 1
    return created


def seed_feature_flags(session: SyncSession, dry_run: bool) -> int:
    created = 0
    updated = 0
    for flag_data in FEATURE_FLAGS:
        existing = session.execute(
            select(FeatureFlag).where(FeatureFlag.name == flag_data["name"])
        ).scalar_one_or_none()
        if existing:
            # Update enabled_globally if it has changed
            if existing.enabled_globally != flag_data["enabled_globally"]:
                print(
                    f"  [update]  FeatureFlag '{flag_data['name']}' "
                    f"enabled_globally {existing.enabled_globally} -> {flag_data['enabled_globally']}"
                )
                if not dry_run:
                    existing.enabled_globally = flag_data["enabled_globally"]
                    existing.rollout_pct = flag_data["rollout_pct"]
                updated += 1
            else:
                print(f"  [skip]    FeatureFlag '{flag_data['name']}' already exists")
            continue
        print(
            f"  [create]  FeatureFlag '{flag_data['name']}' "
            f"(enabled={flag_data['enabled_globally']})"
        )
        if not dry_run:
            session.add(FeatureFlag(
                name=flag_data["name"],
                description=flag_data["description"],
                enabled_globally=flag_data["enabled_globally"],
                rollout_pct=flag_data["rollout_pct"],
            ))
        created += 1
    return created + updated


# ---------------------------------------------------------------------------
# Demo seed (staging / demo environments only)
# ---------------------------------------------------------------------------


def seed_demo(session: SyncSession, dry_run: bool) -> None:
    """Seed demo organisations, users, and projects for staging/demo environments."""
    import uuid
    from app.models.core import Organization, User

    print("\n  [demo] Seeding demo organisations...")

    demo_orgs = [
        {
            "name": "Greenfield Capital Partners",
            "slug": "greenfield-capital",
            "org_type": "investor",
        },
        {
            "name": "SolarPath Developments",
            "slug": "solarpath-dev",
            "org_type": "ally",
        },
    ]

    for org_data in demo_orgs:
        existing = session.execute(
            select(Organization).where(Organization.slug == org_data["slug"])
        ).scalar_one_or_none()
        if existing:
            print(f"  [skip]    Demo org '{org_data['slug']}' already exists")
            continue
        print(f"  [create]  Demo org '{org_data['name']}'")
        if not dry_run:
            session.add(Organization(
                name=org_data["name"],
                slug=org_data["slug"],
                org_type=org_data["org_type"],
            ))

    if not dry_run:
        session.flush()
    print("  [demo] Demo seed complete (organisations only — users/projects require Clerk auth).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="SCR Platform production seed script")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be seeded without writing to the database",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Also seed demo organisations and projects (staging/demo only)",
    )
    args = parser.parse_args()

    dry_run: bool = args.dry_run

    if dry_run:
        print("=" * 60)
        print("DRY RUN — no changes will be committed")
        print("=" * 60)

    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)

    totals: dict[str, int] = {}

    with SyncSession(engine) as session:
        print("\n--- Report Templates ---")
        totals["report_templates"] = seed_report_templates(session, dry_run)

        print("\n--- Legal Templates ---")
        totals["legal_templates"] = seed_legal_templates(session, dry_run)

        print("\n--- Prompt Registry ---")
        totals["prompt_templates"] = seed_prompt_templates(session, dry_run)

        print("\n--- Gamification Badges ---")
        totals["badges"] = seed_badges(session, dry_run)

        print("\n--- Industry Taxonomy ---")
        totals["taxonomy"] = seed_taxonomy(session, dry_run)

        print("\n--- Feature Flags ---")
        totals["feature_flags"] = seed_feature_flags(session, dry_run)

        if args.demo:
            print("\n--- Demo Data ---")
            seed_demo(session, dry_run)

        if not dry_run:
            session.commit()
            print("\n[OK] All changes committed.")
        else:
            session.rollback()
            print("\n[DRY RUN] No changes committed.")

    print("\n=== Seed Summary ===")
    for category, count in totals.items():
        print(f"  {category:25s}: {count} rows created/updated")
    total = sum(totals.values())
    print(f"  {'TOTAL':25s}: {total} rows")

    if dry_run:
        print("\nRe-run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
