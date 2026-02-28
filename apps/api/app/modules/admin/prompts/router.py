"""Admin Prompt Registry CRUD — manage prompt templates with A/B testing."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.ai import PromptTemplate
from app.schemas.auth import CurrentUser
from app.services.prompt_registry import PromptRegistry

logger = structlog.get_logger()

router = APIRouter(prefix="/admin/prompts", tags=["admin-prompts"])


# ── Request schemas ────────────────────────────────────────────────────────────

class PromptCreateRequest(BaseModel):
    task_type: str
    name: str
    system_prompt: str | None = None
    user_prompt_template: str
    output_format_instruction: str | None = None
    variables_schema: dict[str, Any] = {}
    model_override: str | None = None
    temperature_override: float | None = None
    max_tokens_override: int | None = None
    notes: str | None = None


class PromptTestRequest(BaseModel):
    template_id: str
    sample_variables: dict[str, Any]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_platform_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Restrict prompt management to platform admins."""
    # Platform admins have role=admin AND org_type=admin
    # We check role only here since org_type check is in admin module
    if str(current_user.role) not in ("admin",):
        raise HTTPException(status_code=403, detail="Platform admin required")
    return current_user


def _template_to_dict(t: PromptTemplate) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "task_type": t.task_type,
        "version": t.version,
        "name": t.name,
        "system_prompt": t.system_prompt,
        "user_prompt_template": t.user_prompt_template,
        "output_format_instruction": t.output_format_instruction,
        "variables_schema": t.variables_schema,
        "model_override": t.model_override,
        "temperature_override": t.temperature_override,
        "max_tokens_override": t.max_tokens_override,
        "is_active": t.is_active,
        "traffic_percentage": t.traffic_percentage,
        "total_uses": t.total_uses,
        "avg_confidence": t.avg_confidence,
        "positive_feedback_rate": t.positive_feedback_rate,
        "notes": t.notes,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
async def list_prompts(
    task_type: str | None = None,
    current_user: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all prompt templates grouped by task_type."""
    query = select(PromptTemplate).order_by(PromptTemplate.task_type, PromptTemplate.version.desc())
    if task_type:
        query = query.where(PromptTemplate.task_type == task_type)
    result = await db.execute(query)
    templates = result.scalars().all()

    grouped: dict[str, list] = {}
    for t in templates:
        grouped.setdefault(t.task_type, []).append(_template_to_dict(t))

    return {"prompts": grouped, "total_task_types": len(grouped)}


@router.get("/{task_type}/versions")
async def list_versions(
    task_type: str,
    current_user: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all versions for a task_type with quality metrics."""
    result = await db.execute(
        select(PromptTemplate)
        .where(PromptTemplate.task_type == task_type)
        .order_by(PromptTemplate.version.desc())
    )
    return {"versions": [_template_to_dict(t) for t in result.scalars()]}


@router.get("/detail/{template_id}")
async def get_template(
    template_id: str,
    current_user: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get full template detail."""
    template = await db.get(PromptTemplate, uuid.UUID(template_id))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_to_dict(template)


@router.post("")
async def create_version(
    data: PromptCreateRequest,
    current_user: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new prompt version. Starts inactive at 0% traffic."""
    latest = await db.execute(
        select(func.max(PromptTemplate.version)).where(PromptTemplate.task_type == data.task_type)
    )
    next_version = (latest.scalar() or 0) + 1

    template = PromptTemplate(
        task_type=data.task_type,
        version=next_version,
        name=data.name,
        system_prompt=data.system_prompt,
        user_prompt_template=data.user_prompt_template,
        output_format_instruction=data.output_format_instruction,
        variables_schema=data.variables_schema,
        model_override=data.model_override,
        temperature_override=data.temperature_override,
        max_tokens_override=data.max_tokens_override,
        is_active=False,
        traffic_percentage=0,
        created_by=current_user.user_id,
        notes=data.notes,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    logger.info("prompt.created", task_type=data.task_type, version=next_version, user_id=str(current_user.user_id))
    return {"id": str(template.id), "version": next_version}


@router.put("/{template_id}/activate")
async def activate_template(
    template_id: str,
    traffic_percentage: int = 100,
    current_user: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Activate a template and set its traffic percentage."""
    template = await db.get(PromptTemplate, uuid.UUID(template_id))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    template.is_active = True
    template.traffic_percentage = max(0, min(100, traffic_percentage))
    await db.commit()
    PromptRegistry(db).invalidate_cache(template.task_type)
    logger.info("prompt.activated", template_id=template_id, traffic=template.traffic_percentage)
    return {"status": "activated", "traffic_percentage": template.traffic_percentage}


@router.put("/{template_id}/deactivate")
async def deactivate_template(
    template_id: str,
    current_user: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deactivate a template (rollback). Sets traffic to 0."""
    template = await db.get(PromptTemplate, uuid.UUID(template_id))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    template.is_active = False
    template.traffic_percentage = 0
    await db.commit()
    PromptRegistry(db).invalidate_cache(template.task_type)
    logger.info("prompt.deactivated", template_id=template_id)
    return {"status": "deactivated"}


@router.get("/{template_id}/metrics")
async def get_template_metrics(
    template_id: str,
    current_user: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Quality metrics for a specific template version."""
    template = await db.get(PromptTemplate, uuid.UUID(template_id))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "template_id": template_id,
        "task_type": template.task_type,
        "version": template.version,
        "total_uses": template.total_uses,
        "avg_confidence": template.avg_confidence,
        "positive_feedback_rate": template.positive_feedback_rate,
    }


@router.get("/compare/{id1}/{id2}")
async def compare_templates(
    id1: str,
    id2: str,
    current_user: CurrentUser = Depends(_require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Side-by-side metrics comparison of two prompt versions."""
    t1 = await db.get(PromptTemplate, uuid.UUID(id1))
    t2 = await db.get(PromptTemplate, uuid.UUID(id2))
    if not t1 or not t2:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "template_1": {
            "id": str(t1.id), "version": t1.version, "name": t1.name,
            "total_uses": t1.total_uses, "avg_confidence": t1.avg_confidence,
            "positive_feedback_rate": t1.positive_feedback_rate,
        },
        "template_2": {
            "id": str(t2.id), "version": t2.version, "name": t2.name,
            "total_uses": t2.total_uses, "avg_confidence": t2.avg_confidence,
            "positive_feedback_rate": t2.positive_feedback_rate,
        },
    }
