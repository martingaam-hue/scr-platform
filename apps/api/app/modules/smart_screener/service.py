"""Smart Screener service — NL query parsing and search execution."""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.screener import SavedSearch
from app.modules.smart_screener.schemas import ParsedFilters, ScreenerResult

logger = structlog.get_logger()


async def parse_query(query: str) -> ParsedFilters:
    """Use Haiku via the AI gateway to parse natural language into structured filters."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={
                    "task_type": "parse_screener_query",
                    "messages": [{"role": "user", "content": query}],
                    "context": {"query": query},
                },
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()

        validated = data.get("validated_data") or {}
        if validated:
            return ParsedFilters(**{k: v for k, v in validated.items() if v is not None})

        # Fallback: treat as keyword search
        content = data.get("content", "")
        try:
            raw = json.loads(content)
            return ParsedFilters(**{k: v for k, v in raw.items() if v is not None})
        except Exception:
            pass
    except Exception as exc:
        logger.warning("screener_parse_failed", error=str(exc))

    return ParsedFilters(sector_keywords=query.split()[:10])


async def execute_search(
    db: AsyncSession,
    filters: ParsedFilters,
    org_id: uuid.UUID,
    limit: int = 50,
) -> list[ScreenerResult]:
    """Execute parsed filters against marketplace/project data."""
    from sqlalchemy import and_, or_

    from app.models.projects import Project, SignalScore

    conditions = [Project.org_id == org_id, Project.is_deleted.is_(False)]

    if filters.project_types:
        conditions.append(
            or_(*[Project.project_type.ilike(f"%{pt}%") for pt in filters.project_types])
        )
    if filters.geographies:
        conditions.append(
            or_(*[Project.geography_country.ilike(f"%{g}%") for g in filters.geographies])
        )
    if filters.stages:
        conditions.append(Project.stage.in_(filters.stages))
    if filters.min_ticket_size is not None:
        conditions.append(
            Project.total_investment_required >= filters.min_ticket_size * 1_000_000
        )
    if filters.max_ticket_size is not None:
        conditions.append(
            Project.total_investment_required <= filters.max_ticket_size * 1_000_000
        )

    stmt = (
        select(Project)
        .where(and_(*conditions))
        .order_by(Project.updated_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    projects = result.scalars().all()

    # Fetch signal scores for these projects
    if projects:
        project_ids = [p.id for p in projects]
        score_stmt = select(SignalScore).where(
            SignalScore.project_id.in_(project_ids),
            SignalScore.is_live.is_(True),
        )
        score_result = await db.execute(score_stmt)
        scores_by_project = {s.project_id: s.overall_score for s in score_result.scalars()}
    else:
        scores_by_project = {}

    results = [
        ScreenerResult(
            id=p.id,
            name=p.name,
            project_type=p.project_type,
            geography_country=p.geography_country,
            stage=p.stage,
            total_investment_required=float(p.total_investment_required)
            if p.total_investment_required
            else None,
            currency=p.currency,
            signal_score=scores_by_project.get(p.id),
            status=p.status,
        )
        for p in projects
    ]

    # Apply signal score filter post-fetch (score comes from separate table)
    if filters.min_signal_score is not None:
        results = [r for r in results if r.signal_score is None or r.signal_score >= filters.min_signal_score]
    if filters.max_signal_score is not None:
        results = [r for r in results if r.signal_score is None or r.signal_score <= filters.max_signal_score]

    # Sort
    if filters.sort_by == "signal_score":
        results.sort(key=lambda x: x.signal_score or 0, reverse=True)

    return results


def merge_filters(parsed: ParsedFilters, existing: dict[str, Any]) -> ParsedFilters:
    """Merge parsed NLP filters with user-adjusted filter pills."""
    data = parsed.model_dump()
    for key, value in existing.items():
        if value is not None:
            data[key] = value
    return ParsedFilters(**data)


def generate_suggestions(filters: ParsedFilters, result_count: int) -> list[str]:
    """Suggest query refinements based on current filters and result count."""
    suggestions: list[str] = []

    if result_count == 0:
        if filters.min_signal_score and filters.min_signal_score > 60:
            suggestions.append("Try lowering the Signal Score threshold")
        if filters.geographies:
            suggestions.append(f"Try expanding beyond {', '.join(filters.geographies[:2])}")
        if not filters.project_types:
            suggestions.append(
                "Try specifying a project type (solar, wind, real estate, etc.)"
            )

    elif result_count > 30:
        if not filters.min_signal_score:
            suggestions.append(
                "Add 'with Signal Score above 70' to focus on higher quality deals"
            )
        if not filters.stages:
            suggestions.append(
                "Add a development stage filter (e.g., 'operational' or 'construction')"
            )

    return suggestions


# ── Saved searches ────────────────────────────────────────────────────────────


async def save_search(
    db: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    name: str,
    query: str,
    filters: dict[str, Any],
    notify_new_matches: bool = False,
) -> SavedSearch:
    saved = SavedSearch(
        user_id=user_id,
        org_id=org_id,
        name=name,
        query=query,
        filters=filters,
        notify_new_matches=notify_new_matches,
    )
    db.add(saved)
    await db.flush()
    await db.refresh(saved)
    return saved


async def list_saved_searches(
    db: AsyncSession, user_id: uuid.UUID
) -> list[SavedSearch]:
    stmt = (
        select(SavedSearch)
        .where(SavedSearch.user_id == user_id)
        .order_by(SavedSearch.last_used.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
