"""Onboarding API router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.onboarding.schemas import (
    OnboardingCompleteRequest,
    OnboardingCompleteResponse,
)
from app.modules.onboarding.service import complete_onboarding
from app.schemas.auth import CurrentUser

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.put("/complete", response_model=OnboardingCompleteResponse)
async def complete_onboarding_endpoint(
    body: OnboardingCompleteRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Complete the onboarding wizard, setting up the organisation and default entities."""
    result = await complete_onboarding(db, current_user, body)
    await db.commit()
    return result
