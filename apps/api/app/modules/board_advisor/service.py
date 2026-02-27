"""Board Advisor service."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advisory import BoardAdvisorApplication, BoardAdvisorProfile
from app.models.enums import AdvisorAvailabilityStatus, BoardAdvisorApplicationStatus
from app.modules.board_advisor.schemas import (
    AdvisorProfileCreate,
    AdvisorProfileUpdate,
    AdvisorSearchResult,
    ApplicationCreate,
    ApplicationStatusUpdate,
)

logger = structlog.get_logger()


# ── Profile helpers ───────────────────────────────────────────────────────────


async def _get_profile_by_user(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> BoardAdvisorProfile | None:
    stmt = select(BoardAdvisorProfile).where(BoardAdvisorProfile.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_profile_or_raise(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> BoardAdvisorProfile:
    profile = await _get_profile_by_user(db, user_id)
    if not profile:
        raise LookupError(f"No board advisor profile found for user {user_id}")
    return profile


# ── Public service functions ──────────────────────────────────────────────────


async def get_or_create_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    body: AdvisorProfileCreate,
) -> BoardAdvisorProfile:
    """Upsert advisor profile: select by user_id first, create if not exists."""
    existing = await _get_profile_by_user(db, user_id)
    if existing:
        return existing

    # Map availability_status string to enum (case-insensitive)
    try:
        avail_status = AdvisorAvailabilityStatus(body.availability_status.lower())
    except ValueError:
        avail_status = AdvisorAvailabilityStatus.AVAILABLE

    from app.models.enums import AdvisorCompensationPreference

    try:
        comp_pref = AdvisorCompensationPreference(body.compensation_preference.lower())
    except ValueError:
        comp_pref = AdvisorCompensationPreference.NEGOTIABLE

    profile = BoardAdvisorProfile(
        user_id=user_id,
        org_id=org_id,
        expertise_areas=body.expertise_areas,
        industry_experience=body.industry_experience,
        board_positions_held=body.board_positions_held,
        availability_status=avail_status,
        compensation_preference=comp_pref,
        bio=body.bio,
        linkedin_url=body.linkedin_url,
        verified=False,
        match_count=0,
        is_active=True,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return profile


async def update_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    body: AdvisorProfileUpdate,
) -> BoardAdvisorProfile:
    """Update existing advisor profile fields."""
    profile = await _get_profile_or_raise(db, user_id)

    from app.models.enums import AdvisorAvailabilityStatus, AdvisorCompensationPreference

    if body.expertise_areas is not None:
        profile.expertise_areas = body.expertise_areas
    if body.industry_experience is not None:
        profile.industry_experience = body.industry_experience
    if body.board_positions_held is not None:
        profile.board_positions_held = body.board_positions_held
    if body.availability_status is not None:
        try:
            profile.availability_status = AdvisorAvailabilityStatus(
                body.availability_status.lower()
            )
        except ValueError:
            pass
    if body.compensation_preference is not None:
        try:
            profile.compensation_preference = AdvisorCompensationPreference(
                body.compensation_preference.lower()
            )
        except ValueError:
            pass
    if body.bio is not None:
        profile.bio = body.bio
    if body.linkedin_url is not None:
        profile.linkedin_url = body.linkedin_url
    if body.is_active is not None:
        profile.is_active = body.is_active

    await db.flush()
    await db.refresh(profile)
    return profile


def _compute_match_score(
    profile: BoardAdvisorProfile,
    expertise_filter: str | None,
) -> int:
    """
    Deterministic match score 0-100:
    - Expertise keyword overlap with filter: up to 50 pts
    - Availability == AVAILABLE: 30 pts
    - Verified: 20 pts
    """
    score = 0

    # Expertise overlap: up to 50 pts
    if expertise_filter:
        keyword = expertise_filter.lower()
        areas = profile.expertise_areas or {}
        # Check keys and string values for keyword match
        matched = any(
            keyword in k.lower() or (isinstance(v, str) and keyword in v.lower())
            for k, v in areas.items()
        )
        if matched:
            score += 50
    else:
        # No filter: give full expertise points if they have any expertise listed
        if profile.expertise_areas:
            score += 50

    # Availability: 30 pts
    if profile.availability_status == AdvisorAvailabilityStatus.AVAILABLE:
        score += 30

    # Verified: 20 pts
    if profile.verified:
        score += 20

    return min(score, 100)


async def search_advisors(
    db: AsyncSession,
    org_id: uuid.UUID,
    expertise: str | None = None,
    availability: str | None = None,
) -> list[AdvisorSearchResult]:
    """Query all is_active profiles, apply optional filters, compute deterministic match_score."""
    stmt = select(BoardAdvisorProfile).where(
        BoardAdvisorProfile.is_active.is_(True),
    )

    if availability:
        try:
            avail_enum = AdvisorAvailabilityStatus(availability.lower())
            stmt = stmt.where(BoardAdvisorProfile.availability_status == avail_enum)
        except ValueError:
            pass

    result = await db.execute(stmt)
    profiles = result.scalars().all()

    search_results: list[AdvisorSearchResult] = []
    for profile in profiles:
        match_score = _compute_match_score(profile, expertise)

        # If expertise filter provided, skip profiles with 0 score (no match)
        if expertise and match_score == 0:
            continue

        avg_rating = float(profile.avg_rating) if profile.avg_rating is not None else None

        search_results.append(
            AdvisorSearchResult(
                id=profile.id,
                user_id=profile.user_id,
                expertise_areas=profile.expertise_areas,
                availability_status=profile.availability_status.value,
                compensation_preference=profile.compensation_preference.value,
                bio=profile.bio,
                verified=profile.verified,
                board_positions_held=profile.board_positions_held,
                avg_rating=avg_rating,
                match_score=match_score,
            )
        )

    # Sort by match_score descending
    search_results.sort(key=lambda x: x.match_score, reverse=True)
    return search_results


async def apply_to_project(
    db: AsyncSession,
    advisor_user_id: uuid.UUID,
    advisor_org_id: uuid.UUID,
    body: ApplicationCreate,
) -> BoardAdvisorApplication:
    """Find advisor profile by user_id, create application with stub signal_score_impact."""
    profile = await _get_profile_or_raise(db, advisor_user_id)

    equity = Decimal(str(body.equity_offered)) if body.equity_offered is not None else None

    application = BoardAdvisorApplication(
        project_id=body.project_id,
        advisor_profile_id=profile.id,
        ally_org_id=advisor_org_id,
        status=BoardAdvisorApplicationStatus.PENDING,
        message=body.message,
        role_offered=body.role_offered,
        equity_offered=equity,
        compensation_terms=body.compensation_terms,
        signal_score_impact=Decimal("5.0"),  # stub
    )
    db.add(application)
    await db.flush()
    await db.refresh(application)
    return application


async def get_applications(
    db: AsyncSession,
    org_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
) -> list[BoardAdvisorApplication]:
    """List applications for org, optionally filtered by project_id."""
    stmt = select(BoardAdvisorApplication).where(
        BoardAdvisorApplication.ally_org_id == org_id,
    )
    if project_id is not None:
        stmt = stmt.where(BoardAdvisorApplication.project_id == project_id)

    stmt = stmt.order_by(BoardAdvisorApplication.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_application_status(
    db: AsyncSession,
    application_id: uuid.UUID,
    org_id: uuid.UUID,
    body: ApplicationStatusUpdate,
) -> BoardAdvisorApplication:
    """Update application status; set started_at when status transitions to ACCEPTED."""
    stmt = select(BoardAdvisorApplication).where(
        BoardAdvisorApplication.id == application_id,
        BoardAdvisorApplication.ally_org_id == org_id,
    )
    result = await db.execute(stmt)
    application = result.scalar_one_or_none()
    if not application:
        raise LookupError(f"Application {application_id} not found for org {org_id}")

    try:
        new_status = BoardAdvisorApplicationStatus(body.status.lower())
    except ValueError:
        raise ValueError(f"Invalid application status: {body.status}")

    application.status = new_status

    if new_status == BoardAdvisorApplicationStatus.ACCEPTED and application.started_at is None:
        application.started_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(application)
    return application
