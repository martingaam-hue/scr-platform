"""Per-org AI spend tracking and budget enforcement.

Usage (FastAPI dependency):
    from app.services.ai_budget import enforce_ai_budget

    @router.post("/signal-score/calculate")
    async def calculate(
        _: None = Depends(enforce_ai_budget),
        ...
    ):
        ...
"""
from __future__ import annotations

import calendar
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.models.ai import AITaskLog
from app.models.core import Organization
from app.models.enums import SubscriptionTier
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

# Tier-default monthly USD budgets (can be overridden per org in DB)
_TIER_BUDGETS: dict[SubscriptionTier, float] = {
    SubscriptionTier.FOUNDATION:   50.0,    # ~$50/month
    SubscriptionTier.PROFESSIONAL: 500.0,   # ~$500/month
    SubscriptionTier.ENTERPRISE:   5000.0,  # ~$5k/month
}


async def get_org_monthly_spend(db: AsyncSession, org_id: str) -> Decimal:
    """Return total USD spent by *org_id* in the current calendar month."""
    now = datetime.now(timezone.utc)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    from uuid import UUID
    org_uuid = UUID(str(org_id))

    result = await db.execute(
        select(func.coalesce(func.sum(AITaskLog.cost_usd), 0)).where(
            AITaskLog.org_id == org_uuid,
            AITaskLog.cost_usd.isnot(None),
            AITaskLog.created_at >= first_of_month,
        )
    )
    return Decimal(str(result.scalar_one()))


async def get_org_budget(db: AsyncSession, org_id: str) -> float:
    """Return effective monthly USD budget for this org.

    Uses the explicit DB override if set; falls back to the tier default.
    """
    from uuid import UUID
    org_uuid = UUID(str(org_id))

    result = await db.execute(
        select(Organization.ai_monthly_budget, Organization.subscription_tier).where(
            Organization.id == org_uuid
        )
    )
    row = result.first()
    if row is None:
        return _TIER_BUDGETS[SubscriptionTier.FOUNDATION]

    budget_override, tier = row
    if budget_override is not None:
        return float(budget_override)

    return _TIER_BUDGETS.get(tier, _TIER_BUDGETS[SubscriptionTier.FOUNDATION])


async def check_budget(db: AsyncSession, org_id: str) -> None:
    """Raise HTTP 429 if the org has exhausted its monthly AI budget.

    Called as a FastAPI dependency before AI-generating endpoints.
    Fails *open* on DB errors to avoid blocking legitimate requests.
    """
    if not settings.AI_TOKEN_BUDGET_ENABLED:
        return

    try:
        spend = await get_org_monthly_spend(db, org_id)
        budget = await get_org_budget(db, org_id)

        if float(spend) >= budget:
            logger.warning(
                "ai_budget_exceeded",
                org_id=org_id,
                spend_usd=float(spend),
                budget_usd=budget,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "ai_budget_exceeded",
                    "message": (
                        f"Monthly AI budget of ${budget:.2f} has been reached. "
                        "Contact support to increase your limit."
                    ),
                    "spend_usd": float(spend),
                    "budget_usd": budget,
                },
            )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("ai_budget_check_failed", error=str(exc))
        # Fail open — don't block requests on DB errors


async def enforce_ai_budget(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(lambda: None),  # overridden below
) -> None:
    """FastAPI dependency that enforces org-level AI budget."""
    pass  # placeholder — real implementation below


# Proper dependency using FastAPI's DI
def _make_budget_dep():
    from app.core.database import get_db

    async def _enforce(
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        await check_budget(db, str(current_user.org_id))

    return _enforce


enforce_ai_budget = _make_budget_dep()
