"""Board Advisor API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.board_advisor import service
from app.modules.board_advisor.schemas import (
    AdvisorProfileCreate,
    AdvisorProfileResponse,
    AdvisorProfileUpdate,
    AdvisorSearchResult,
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatusUpdate,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/board-advisors", tags=["board-advisor"])


# ── Fixed paths ───────────────────────────────────────────────────────────────


@router.get("/search", response_model=list[AdvisorSearchResult])
async def search_advisors(
    expertise: str | None = Query(None, description="Expertise keyword filter"),
    availability: str | None = Query(None, description="Availability status filter"),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Search active board advisors with optional expertise and availability filters."""
    return await service.search_advisors(
        db,
        org_id=current_user.org_id,
        expertise=expertise,
        availability=availability,
    )


@router.get("/my-profile", response_model=AdvisorProfileResponse)
async def get_my_profile(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's board advisor profile."""
    try:
        profile = await service._get_profile_or_raise(db, current_user.user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return profile


@router.post(
    "/my-profile",
    response_model=AdvisorProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_my_profile(
    body: AdvisorProfileCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or return existing board advisor profile for the current user."""
    profile = await service.get_or_create_profile(
        db,
        user_id=current_user.user_id,
        org_id=current_user.org_id,
        body=body,
    )
    await db.commit()
    await db.refresh(profile)
    return profile


@router.put("/my-profile", response_model=AdvisorProfileResponse)
async def update_my_profile(
    body: AdvisorProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's board advisor profile."""
    try:
        profile = await service.update_profile(
            db,
            user_id=current_user.user_id,
            org_id=current_user.org_id,
            body=body,
        )
        await db.commit()
        await db.refresh(profile)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return profile


@router.post(
    "/apply",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def apply_to_project(
    body: ApplicationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a board advisor application to a project."""
    try:
        application = await service.apply_to_project(
            db,
            advisor_user_id=current_user.user_id,
            advisor_org_id=current_user.org_id,
            body=body,
        )
        await db.commit()
        await db.refresh(application)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return application


@router.get("/applications", response_model=list[ApplicationResponse])
async def get_applications(
    project_id: uuid.UUID | None = Query(None, description="Filter by project ID"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List board advisor applications for the current user's org."""
    return await service.get_applications(
        db,
        org_id=current_user.org_id,
        project_id=project_id,
    )


# ── Parameterised endpoints ───────────────────────────────────────────────────


@router.put(
    "/applications/{application_id}/status",
    response_model=ApplicationResponse,
)
async def update_application_status(
    application_id: uuid.UUID,
    body: ApplicationStatusUpdate,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Update the status of a board advisor application."""
    try:
        application = await service.update_application_status(
            db,
            application_id=application_id,
            org_id=current_user.org_id,
            body=body,
        )
        await db.commit()
        await db.refresh(application)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return application
