"""Per-org monthly AI token budget enforcement."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.launch import UsageEvent

logger = structlog.get_logger()

# Monthly token limits by subscription tier (matches SubscriptionTier enum values)
TIER_LIMITS: dict[str, int] = {
    "foundation": 2_000_000,      # 2M tokens/month
    "professional": 20_000_000,   # 20M tokens/month
    "enterprise": 200_000_000,    # 200M tokens/month — effectively unlimited
}
DEFAULT_LIMIT = 2_000_000


async def get_monthly_usage(db: AsyncSession, org_id: Any) -> int:
    """Return total AI tokens used by org in the current calendar month."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    cast(
                        func.jsonb_extract_path_text(
                            UsageEvent.event_metadata, "tokens"
                        ),
                        Integer,
                    )
                ),
                0,
            )
        ).where(
            UsageEvent.org_id == org_id,
            UsageEvent.event_type == "ai_tokens_used",
            UsageEvent.created_at >= month_start,
        )
    )
    return int(result.scalar_one() or 0)


async def check_budget(
    db: AsyncSession,
    org_id: Any,
    estimated_tokens: int,
    tier: str = "foundation",
) -> tuple[bool, int, int]:
    """
    Check if org has budget for estimated_tokens.

    Returns: (allowed, current_usage, limit)
    """
    limit = TIER_LIMITS.get(tier.lower(), DEFAULT_LIMIT)
    current = await get_monthly_usage(db, org_id)
    allowed = (current + estimated_tokens) <= limit
    if not allowed:
        logger.warning(
            "token_budget.exceeded",
            org_id=str(org_id),
            current=current,
            estimated=estimated_tokens,
            limit=limit,
            tier=tier,
        )
    return allowed, current, limit


async def record_token_usage(
    db: AsyncSession,
    org_id: Any,
    user_id: Any,
    tokens_used: int,
    task_type: str,
    model: str,
) -> None:
    """Record AI token usage as a UsageEvent."""
    event = UsageEvent(
        org_id=org_id,
        user_id=user_id,
        event_type="ai_tokens_used",
        entity_type="ai_call",
        event_metadata={
            "tokens": tokens_used,
            "task_type": task_type,
            "model": model,
        },
    )
    db.add(event)
    # Use flush (not commit) — caller manages transaction
    await db.flush()
