"""Alley Development Advisor service — AI strategic guidance for project developers."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.middleware.tenant import tenant_filter
from app.models.projects import Project, SignalScore
from app.modules.alley.advisor.schemas import (
    AdvisorQueryResponse,
    FinancingReadinessResponse,
    MarketPositioningResponse,
    MilestonePlanResponse,
    RegulatoryGuidanceResponse,
)

logger = structlog.get_logger()


async def _get_project_with_score(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> tuple[Project, SignalScore | None]:
    stmt = select(Project).where(Project.id == project_id, Project.is_deleted.is_(False))
    stmt = tenant_filter(stmt, org_id, Project)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise LookupError(f"Project {project_id} not found")

    score_result = await db.execute(
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.desc())
        .limit(1)
    )
    score = score_result.scalar_one_or_none()
    return project, score


def _project_context(project: Project, score: SignalScore | None) -> str:
    score_text = (
        f"Signal Score: {score.overall_score}/100 "
        f"(Viability: {score.project_viability_score}, "
        f"Financial: {score.financial_planning_score}, "
        f"Team: {score.team_strength_score}, "
        f"Risk: {score.risk_assessment_score}, "
        f"ESG: {score.esg_score}, "
        f"Market: {score.market_opportunity_score})"
        if score else "No score calculated yet."
    )
    return (
        f"Project: {project.name}\n"
        f"Type: {project.project_type.value}\n"
        f"Stage: {project.stage.value}\n"
        f"Geography: {project.geography_country}\n"
        f"Investment Required: {project.total_investment_required} {project.currency}\n"
        f"Capacity: {project.capacity_mw} MW\n"
        f"Description: {(project.description or '')[:500]}\n"
        f"{score_text}"
    )


async def _call_ai(prompt: str, task_type: str, max_tokens: int = 1500) -> str:
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={"prompt": prompt, "task_type": task_type, "max_tokens": max_tokens, "temperature": 0.4},
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
            )
        resp.raise_for_status()
        return resp.json().get("content", "")
    except Exception as exc:
        logger.warning("advisor_ai_call_failed", task_type=task_type, error=str(exc))
        return ""


async def query_advisor(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    question: str,
) -> AdvisorQueryResponse:
    import uuid as _uuid
    project, score = await _get_project_with_score(db, project_id, org_id)
    ctx = _project_context(project, score)
    prompt = (
        f"You are a Development Advisor for sustainable infrastructure projects. "
        f"Answer the developer's question with practical, actionable guidance.\n\n"
        f"PROJECT CONTEXT:\n{ctx}\n\n"
        f"QUESTION: {question}\n\n"
        "Give a clear, structured answer focused on what the developer should DO next."
    )
    answer = await _call_ai(prompt, "alley_advisor_query", max_tokens=1000)
    if not answer:
        answer = "I apologise — I couldn't generate a response at this time. Please try again shortly."
    return AdvisorQueryResponse(
        answer=answer,
        conversation_id=str(_uuid.uuid4()),
        model_used="claude-sonnet-4",
    )


async def get_financing_readiness(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> FinancingReadinessResponse:
    project, score = await _get_project_with_score(db, project_id, org_id)
    ctx = _project_context(project, score)
    prompt = (
        f"You are a project finance advisor. Assess this project's readiness for investor conversations.\n\n"
        f"PROJECT CONTEXT:\n{ctx}\n\n"
        "Respond ONLY with valid JSON:\n"
        '{"readiness_score": <0-100>, "summary": "<2-3 sentences>", '
        '"checklist": [{"item": "...", "status": "complete|partial|missing", "action": "..."}], '
        '"recommended_structure": "<debt/equity/blended finance recommendation>"}'
    )
    import json, re
    raw = await _call_ai(prompt, "alley_financing_readiness", max_tokens=1200)
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(match.group()) if match else {}
    except Exception:
        data = {}

    return FinancingReadinessResponse(
        project_id=project_id,
        readiness_score=data.get("readiness_score", score.overall_score if score else 50),
        summary=data.get("summary", "Assessment in progress."),
        checklist=data.get("checklist", []),
        recommended_structure=data.get("recommended_structure", "Blended finance recommended."),
        generated_at=datetime.now(timezone.utc),
    )


async def get_market_positioning(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> MarketPositioningResponse:
    project, score = await _get_project_with_score(db, project_id, org_id)
    ctx = _project_context(project, score)
    prompt = (
        f"You are a market strategist for sustainable infrastructure. Analyse this project's market position.\n\n"
        f"PROJECT CONTEXT:\n{ctx}\n\n"
        "Respond ONLY with valid JSON:\n"
        '{"strengths": ["..."], "weaknesses": ["..."], '
        '"timing_assessment": "<market timing analysis>", "score_percentile": <estimated 1-100>}'
    )
    import json, re
    raw = await _call_ai(prompt, "alley_market_positioning", max_tokens=1000)
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(match.group()) if match else {}
    except Exception:
        data = {}

    return MarketPositioningResponse(
        project_id=project_id,
        strengths=data.get("strengths", []),
        weaknesses=data.get("weaknesses", []),
        timing_assessment=data.get("timing_assessment", ""),
        score_percentile=data.get("score_percentile", 50),
        generated_at=datetime.now(timezone.utc),
    )


async def get_milestone_plan(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> MilestonePlanResponse:
    project, score = await _get_project_with_score(db, project_id, org_id)
    ctx = _project_context(project, score)
    prompt = (
        f"You are a development manager for sustainable infrastructure projects. "
        f"Create a prioritised milestone plan for this project.\n\n"
        f"PROJECT CONTEXT:\n{ctx}\n\n"
        "Respond ONLY with valid JSON:\n"
        '{"next_milestones": [{"title": "...", "description": "...", "estimated_weeks": <int>, "priority": "critical|high|medium"}], '
        '"critical_path_item": "<the single most important next action>"}'
    )
    import json, re
    raw = await _call_ai(prompt, "alley_development_milestones", max_tokens=1200)
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(match.group()) if match else {}
    except Exception:
        data = {}

    return MilestonePlanResponse(
        project_id=project_id,
        current_stage=project.stage.value,
        next_milestones=data.get("next_milestones", []),
        critical_path_item=data.get("critical_path_item", ""),
        generated_at=datetime.now(timezone.utc),
    )


async def get_regulatory_guidance(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> RegulatoryGuidanceResponse:
    project, score = await _get_project_with_score(db, project_id, org_id)
    prompt = (
        f"You are a regulatory expert for sustainable energy projects.\n\n"
        f"Asset type: {project.project_type.value}\n"
        f"Jurisdiction: {project.geography_country}\n"
        f"Stage: {project.stage.value}\n\n"
        "Respond ONLY with valid JSON:\n"
        '{"permit_requirements": [{"permit": "...", "timeline": "...", "authority": "...", "notes": "..."}], '
        '"common_pitfalls": ["..."]}'
    )
    import json, re
    raw = await _call_ai(prompt, "alley_regulatory_guidance", max_tokens=1200)
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(match.group()) if match else {}
    except Exception:
        data = {}

    return RegulatoryGuidanceResponse(
        project_id=project_id,
        jurisdiction=project.geography_country,
        asset_type=project.project_type.value,
        permit_requirements=data.get("permit_requirements", []),
        common_pitfalls=data.get("common_pitfalls", []),
        generated_at=datetime.now(timezone.utc),
    )
