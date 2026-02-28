"""Seed canonical prompt templates into the database.

Run once after the prompt_templates migration:
    cd apps/api && poetry run python -c "
    import asyncio
    from app.core.database import async_session_factory
    from app.services.seed_prompts import seed_prompts

    async def main():
        async with async_session_factory() as db:
            await seed_prompts(db)

    asyncio.run(main())
    "
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import PromptTemplate

logger = structlog.get_logger()

SEED_PROMPTS: list[dict] = [
    {
        "task_type": "classify_document",
        "version": 1,
        "name": "Document classifier v1",
        "system_prompt": None,
        "user_prompt_template": (
            "Classify this document into one of these categories: "
            "financial_statement, legal_agreement, technical_study, "
            "business_plan, pitch_deck, environmental_assessment, "
            "regulatory_filing, insurance_policy, valuation_report, "
            "due_diligence_report, tax_document, other.\n\n"
            "Document name: {filename}\n"
            "First 2000 characters:\n{document_preview}"
        ),
        "output_format_instruction": (
            'Respond with ONLY a JSON object:\n'
            '{"classification": "<category>", "confidence": <float 0-1>}'
        ),
        "variables_schema": {"filename": "str", "document_preview": "str"},
        "traffic_percentage": 100,
        "is_active": True,
    },
    {
        "task_type": "extract_kpis",
        "version": 1,
        "name": "KPI extractor v1",
        "system_prompt": (
            "You are a financial data extraction specialist. Extract concrete, "
            "verifiable KPIs from documents. Always include units and time periods. "
            "Never fabricate numbers."
        ),
        "user_prompt_template": (
            "Extract key performance indicators from this {document_type} document.\n\n"
            "Document text:\n{document_text}"
        ),
        "output_format_instruction": (
            'Respond with ONLY a JSON object:\n'
            '{"kpis": [{"name": "<str>", "value": "<str>", "unit": "<str>", '
            '"period": "<str>", "confidence": <float 0-1>}, ...]}'
        ),
        "variables_schema": {"document_type": "str", "document_text": "str"},
        "traffic_percentage": 100,
        "is_active": True,
    },
    {
        "task_type": "score_quality",
        "version": 1,
        "name": "Signal Score — document quality evaluator v1",
        "system_prompt": (
            "You are an investment analyst evaluating document quality for alternative "
            "investment assets. You score documents objectively based on completeness, "
            "specificity, credibility, and recency. You never fabricate data."
        ),
        "user_prompt_template": (
            "Evaluate this {criterion} document for a {project_type} project "
            "in {geography}.\n\n"
            "Score the document quality from 0-100 based on:\n"
            "- Completeness: Does it cover all expected sections?\n"
            "- Specificity: Are numbers, dates, and details concrete?\n"
            "- Credibility: Are sources cited? Is methodology sound?\n"
            "- Recency: Is the information current (within 12 months)?\n\n"
            "Document text:\n{document_text}\n\n"
            "Project context:\n{project_context}"
        ),
        "output_format_instruction": (
            'Respond with ONLY a JSON object:\n'
            '{"score": <int 0-100>, "reasoning": "<2-3 sentences>", '
            '"strengths": ["<str>", ...], "weaknesses": ["<str>", ...], '
            '"recommendation": "<specific action>"}'
        ),
        "variables_schema": {
            "criterion": "str", "project_type": "str", "geography": "str",
            "document_text": "str", "project_context": "dict",
        },
        "traffic_percentage": 100,
        "is_active": True,
    },
    {
        "task_type": "score_deal_readiness",
        "version": 1,
        "name": "Deal screening report v1",
        "system_prompt": (
            "You are a senior investment analyst conducting deal screening for an "
            "institutional investor. Never invent financial figures."
        ),
        "user_prompt_template": (
            "Screen this investment opportunity against the investor's mandate.\n\n"
            "PROJECT DATA:\n{project_data}\n\n"
            "DOCUMENT EXTRACTIONS:\n{extractions}\n\n"
            "INVESTOR MANDATE:\n{mandate_data}"
        ),
        "output_format_instruction": (
            'Respond with ONLY a JSON object:\n'
            '{"fit_score": <int 0-100>, "recommendation": "<proceed|pass|need_more_info>", '
            '"executive_summary": "<3-5 sentences>", "strengths": [...], "risks": [...], '
            '"questions_to_ask": [...]}'
        ),
        "variables_schema": {"project_data": "dict", "extractions": "dict", "mandate_data": "dict"},
        "traffic_percentage": 100,
        "is_active": True,
    },
    {
        "task_type": "suggest_assumptions",
        "version": 1,
        "name": "DCF assumption suggestions v1",
        "system_prompt": (
            "You are a valuation analyst. Suggest reasonable DCF assumptions. "
            "All rates as decimals (e.g. 0.08 for 8%)."
        ),
        "user_prompt_template": (
            "Suggest DCF valuation assumptions for:\n"
            "- Project type: {project_type}\n- Geography: {geography}\n"
            "- Stage: {stage}\n- Currency: {currency}\n\n"
            "Context:\n{project_context}"
        ),
        "output_format_instruction": (
            'Respond with ONLY a JSON object:\n'
            '{"discount_rate": <float>, "growth_rate": <float>, '
            '"terminal_multiple": <float>, "risk_premium": <float>, '
            '"reasoning": "<2-4 sentences>"}'
        ),
        "variables_schema": {
            "project_type": "str", "geography": "str",
            "stage": "str", "currency": "str", "project_context": "dict",
        },
        "traffic_percentage": 100,
        "is_active": True,
    },
    {
        "task_type": "chat_with_tools",
        "version": 1,
        "name": "Ralph AI system prompt v1",
        "system_prompt": (
            "You are Ralph, an AI investment analyst for the SCR Platform. "
            "You help investors evaluate alternative investment opportunities "
            "across all asset types (infrastructure, real estate, private equity, "
            "natural resources, private credit, digital assets, impact investments, "
            "specialty assets), and help project developers prepare for institutional investment.\n\n"
            "Guidelines:\n"
            "- Always cite specific data when available\n"
            "- Show your reasoning\n"
            "- Flag uncertainties and data gaps\n"
            "- Never fabricate financial numbers\n"
            "- Use tools for calculations, never calculate yourself\n"
            "- State all currencies explicitly\n"
            "- This is analysis, not investment advice"
        ),
        "user_prompt_template": "{user_message}",
        "output_format_instruction": None,
        "variables_schema": {"user_message": "str"},
        "traffic_percentage": 100,
        "is_active": True,
    },
    {
        "task_type": "review_legal_doc",
        "version": 1,
        "name": "Legal document review v1",
        "system_prompt": (
            "You are a legal analyst reviewing investment documents. "
            "You are NOT providing legal advice — you are flagging items for review by qualified counsel."
        ),
        "user_prompt_template": (
            "Review this {document_type} document.\n\n"
            "Review mode: {review_mode}\n"
            "Jurisdiction: {jurisdiction}\n\n"
            "Document text:\n{document_text}"
        ),
        "output_format_instruction": (
            'Respond with ONLY a JSON object:\n'
            '{"risk_score": <int 0-100>, "summary": "<3-5 sentences>", '
            '"clause_analyses": [{"clause": "<str>", "risk_level": "<low|medium|high|critical>", "analysis": "<str>"},...], '
            '"missing_clauses": [...], "recommendations": [...]}'
        ),
        "variables_schema": {
            "document_type": "str", "review_mode": "str",
            "jurisdiction": "str", "document_text": "str",
        },
        "traffic_percentage": 100,
        "is_active": True,
    },
    {
        "task_type": "parse_screener_query",
        "version": 1,
        "name": "Smart Screener NL query parser v1",
        "system_prompt": None,
        "user_prompt_template": (
            "Parse this investment deal search query into structured filters.\n\n"
            "Query: {query}\n\n"
            "Extract any of these filter types that are mentioned or clearly implied:\n"
            "- project_types: solar, wind, hydro, biomass, real_estate, infrastructure, "
            "private_equity, private_credit, natural_resources, digital_assets, impact\n"
            "- geographies: country names, regions, continents\n"
            "- stages: early_stage, development, construction, operational, brownfield\n"
            "- min_signal_score / max_signal_score: integer 0-100\n"
            "- min_ticket_size / max_ticket_size: number in millions EUR\n"
            "- min_capacity_mw / max_capacity_mw: number for energy projects\n"
            "- sector_keywords: any other relevant terms\n"
            "- esg_requirements: article_6, article_8, article_9\n"
            "- sort_by: signal_score (default), match_score, created_at"
        ),
        "output_format_instruction": (
            "Respond with ONLY a JSON object. Only include fields explicitly mentioned or "
            "clearly implied. Example: "
            '{{"project_types": ["solar"], "geographies": ["Spain"], "min_capacity_mw": 50}}'
        ),
        "variables_schema": {"query": "str"},
        "traffic_percentage": 100,
        "is_active": True,
    },
    {
        "task_type": "generate_memo",
        "version": 1,
        "name": "Investment memo generator v1",
        "system_prompt": (
            "You are a senior investment analyst writing institutional-grade investment memos. "
            "Use specific data, cite sources, flag uncertainties. State all currencies explicitly."
        ),
        "user_prompt_template": (
            "Generate an investment memo for this opportunity.\n\n"
            "Project data:\n{project_data}\n\n"
            "Signal Score:\n{signal_score}\n\n"
            "Risk assessment:\n{risk_assessment}\n\n"
            "Valuation:\n{valuation}\n\n"
            "Investor mandate:\n{mandate}"
        ),
        "output_format_instruction": (
            'Respond with ONLY a JSON object:\n'
            '{"content": "<full memo in markdown format>"}'
        ),
        "variables_schema": {
            "project_data": "dict", "signal_score": "dict",
            "risk_assessment": "dict", "valuation": "dict", "mandate": "dict",
        },
        "traffic_percentage": 100,
        "is_active": True,
    },
    {
        "task_type": "dd_review_item",
        "version": 1,
        "name": "DD checklist item review v1",
        "system_prompt": "You are a due diligence analyst reviewing documents for investment readiness. Be precise and identify specific gaps.",
        "user_prompt_template": (
            "Review this document against the following due diligence requirement:\n\n"
            "REQUIREMENT: {item_criteria}\n\n"
            "DOCUMENT ({document_name}):\n{document_text}"
        ),
        "output_format_instruction": (
            'Respond with ONLY a JSON object:\n'
            '{"satisfied": true/false, "confidence": 0.0-1.0, '
            '"summary": "<what the document covers>", '
            '"gaps": ["<missing element 1>", ...], '
            '"recommendation": "<what to do next>"}'
        ),
        "variables_schema": {"item_criteria": "str", "document_name": "str", "document_text": "str"},
        "traffic_percentage": 100,
        "is_active": True,
    },
    {
        "task_type": "generate_digest_summary",
        "version": 1,
        "name": "Weekly digest summary v1",
        "system_prompt": (
            "You are a concise business analyst writing a weekly digest for an investment platform. "
            "Write 2-3 sentences in a professional but friendly tone summarizing the week's AI activity. "
            "Focus on business impact, not technical details. Use plain text, no markdown."
        ),
        "user_prompt_template": (
            "Generate a brief weekly digest summary for {org_name}.\n\n"
            "Activity data:\n{activity_summary}"
        ),
        "output_format_instruction": "Respond with 2-3 sentences of plain prose. No bullet points, no markdown.",
        "variables_schema": {"org_name": "str", "activity_summary": "str"},
        "traffic_percentage": 100,
        "is_active": True,
    },
]


async def seed_prompts(db: AsyncSession) -> None:
    """Insert seed prompts. Idempotent — skips if task_type+version already exists."""
    seeded = 0
    skipped = 0

    for prompt_data in SEED_PROMPTS:
        existing = await db.execute(
            select(PromptTemplate).where(
                PromptTemplate.task_type == prompt_data["task_type"],
                PromptTemplate.version == prompt_data["version"],
            )
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        template = PromptTemplate(**prompt_data)
        db.add(template)
        seeded += 1

    await db.commit()
    logger.info("seed_prompts.complete", seeded=seeded, skipped=skipped)
