"""Prompt Registry — centralised LLM prompt management with versioning and A/B testing.

Usage in any module:
    registry = PromptRegistry(db)
    messages, template_id, version = await registry.render("score_quality", {
        "document_text": doc.text[:8000],
        "criterion": "financial_planning",
        "project_context": project.to_dict(),
    })
    # Pass messages directly to the AI gateway
"""

from __future__ import annotations

import json
import random
import time
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import PromptTemplate

logger = structlog.get_logger()


class PromptRegistry:
    """Manages active prompt templates with in-process caching and A/B split routing."""

    _CACHE_TTL = 300  # 5 minutes

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._cache: dict[str, tuple[list[PromptTemplate], float]] = {}

    async def render(
        self,
        task_type: str,
        variables: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str | None, int | None]:
        """Get the active prompt for task_type, fill variables, return messages.

        Returns:
            (messages, template_id, version)
            template_id / version are None when no registry template exists (fallback mode).
        """
        template = await self._select_template(task_type)
        if not template:
            return [], None, None

        self._validate_variables(template, variables)

        messages: list[dict[str, Any]] = []
        if template.system_prompt:
            messages.append({
                "role": "system",
                "content": self._fill(template.system_prompt, variables),
            })

        user_text = self._fill(template.user_prompt_template, variables)
        if template.output_format_instruction:
            user_text += f"\n\n{template.output_format_instruction}"

        messages.append({"role": "user", "content": user_text})

        await self._increment_usage(template.id)
        return messages, str(template.id), template.version

    async def update_quality_metrics(self, template_id: str, confidence: float) -> None:
        """Update rolling average confidence after an AI call."""
        template = await self._db.get(PromptTemplate, template_id)
        if not template:
            return
        if template.avg_confidence is None:
            template.avg_confidence = confidence
        else:
            template.avg_confidence = round(template.avg_confidence * 0.95 + confidence * 0.05, 4)

    def invalidate_cache(self, task_type: str | None = None) -> None:
        """Flush in-process cache. Call after admin edits a template."""
        if task_type:
            self._cache.pop(task_type, None)
        else:
            self._cache.clear()

    # ── Private ───────────────────────────────────────────────────────────────

    async def _select_template(self, task_type: str) -> PromptTemplate | None:
        templates = await self._get_active(task_type)
        if not templates:
            return None
        if len(templates) == 1:
            return templates[0]

        total = sum(t.traffic_percentage for t in templates)
        if total == 0:
            return templates[0]
        roll = random.randint(1, total)
        cumulative = 0
        for t in templates:
            cumulative += t.traffic_percentage
            if roll <= cumulative:
                return t
        return templates[0]

    async def _get_active(self, task_type: str) -> list[PromptTemplate]:
        now = time.monotonic()
        if task_type in self._cache:
            cached, ts = self._cache[task_type]
            if now - ts < self._CACHE_TTL:
                return cached

        result = await self._db.execute(
            select(PromptTemplate)
            .where(PromptTemplate.task_type == task_type)
            .where(PromptTemplate.is_active.is_(True))
            .order_by(PromptTemplate.version.desc())
        )
        templates = list(result.scalars().all())
        self._cache[task_type] = (templates, now)
        return templates

    def _fill(self, template_text: str, variables: dict[str, Any]) -> str:
        result = template_text
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            if placeholder in result:
                if isinstance(value, (dict, list)):
                    result = result.replace(placeholder, json.dumps(value, indent=2, default=str))
                else:
                    result = result.replace(placeholder, str(value))
        return result

    def _validate_variables(self, template: PromptTemplate, variables: dict[str, Any]) -> None:
        schema = template.variables_schema or {}
        missing = [k for k in schema if k not in variables]
        if missing:
            raise ValueError(
                f"Missing variables for {template.task_type} v{template.version}: {missing}"
            )

    async def _increment_usage(self, template_id: Any) -> None:
        await self._db.execute(
            update(PromptTemplate)
            .where(PromptTemplate.id == template_id)
            .values(total_uses=PromptTemplate.total_uses + 1)
        )
