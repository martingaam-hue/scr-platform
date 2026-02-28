"""Investor Risk Profile API."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.models.investor_risk import InvestorRiskProfile
from app.modules.risk_profile.schemas import AssessmentRequest, RiskProfileResponse
from app.modules.risk_profile.scoring import calculate_risk_scores
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()
router = APIRouter(prefix="/risk-profile", tags=["risk-profile"])


@router.post("/assess", response_model=RiskProfileResponse)
async def submit_assessment(
    body: AssessmentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RiskProfileResponse:
    """Submit risk assessment. Creates or updates the investor's risk profile."""
    answers = body.model_dump()
    scores = calculate_risk_scores(answers)

    stmt = select(InvestorRiskProfile).where(
        InvestorRiskProfile.user_id == current_user.user_id
    )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if profile:
        for key, value in {**answers, **scores}.items():
            setattr(profile, key, value)
    else:
        profile = InvestorRiskProfile(
            user_id=current_user.user_id,
            org_id=current_user.org_id,
            **answers,
            **scores,
        )
        db.add(profile)

    await db.commit()
    await db.refresh(profile)

    logger.info(
        "risk_profile_assessed",
        user_id=str(current_user.user_id),
        category=scores["risk_category"],
    )

    return RiskProfileResponse(
        has_profile=True,
        risk_category=scores["risk_category"],
        sophistication_score=scores["sophistication_score"],
        risk_appetite_score=scores["risk_appetite_score"],
        recommended_allocation=scores["recommended_allocation"],
        **answers,
    )


@router.get("/me", response_model=RiskProfileResponse)
async def get_my_profile(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RiskProfileResponse:
    """Get current user's risk profile."""
    stmt = select(InvestorRiskProfile).where(
        InvestorRiskProfile.user_id == current_user.user_id
    )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        return RiskProfileResponse(has_profile=False)

    return RiskProfileResponse(
        has_profile=True,
        risk_category=profile.risk_category,
        sophistication_score=profile.sophistication_score,
        risk_appetite_score=profile.risk_appetite_score,
        recommended_allocation=profile.recommended_allocation,
        experience_level=profile.experience_level,
        investment_horizon_years=profile.investment_horizon_years,
        loss_tolerance_percentage=profile.loss_tolerance_percentage,
        liquidity_needs=profile.liquidity_needs,
        concentration_max_percentage=profile.concentration_max_percentage,
        max_drawdown_tolerance=profile.max_drawdown_tolerance,
    )
