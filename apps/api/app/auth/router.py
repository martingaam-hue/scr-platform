"""Auth API router: webhook, profile, preferences, permissions."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk_webhook import EVENT_HANDLERS, verify_webhook_signature
from app.auth.dependencies import get_current_user
from app.auth.rbac import get_permissions_for_role
from app.core.database import get_db
from app.models.core import Organization, User
from app.schemas.auth import (
    CurrentUser,
    PermissionMatrixResponse,
    SwitchOrgRequest,
    SwitchOrgResponse,
    UpdatePreferencesRequest,
    UserProfileResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/webhook", status_code=200)
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Clerk webhook receiver. Verifies signature, dispatches to handler."""
    payload = await verify_webhook_signature(request)
    event_type = payload.get("type", "")
    data = payload.get("data", {})

    handler = EVENT_HANDLERS.get(event_type)
    if handler:
        await handler(data, db)
        logger.info("webhook_processed", event_type=event_type)
    else:
        logger.info("webhook_event_ignored", event_type=event_type)

    return {"status": "ok"}


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current user profile with organization details and permissions."""
    stmt = (
        select(User, Organization)
        .join(Organization, User.org_id == Organization.id)
        .where(User.id == current_user.user_id)
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user, org = row.tuple()
    permissions = get_permissions_for_role(current_user.role)

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        org_id=org.id,
        org_name=org.name,
        org_type=org.type,
        org_slug=org.slug,
        avatar_url=user.avatar_url,
        mfa_enabled=user.mfa_enabled,
        preferences=user.preferences,
        permissions=permissions,
    )


@router.put("/me/preferences")
async def update_preferences(
    body: UpdatePreferencesRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's preferences (partial merge)."""
    stmt = select(User).where(User.id == current_user.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one()

    merged = {**user.preferences, **body.preferences}
    user.preferences = merged
    await db.flush()

    return {"preferences": merged}


@router.post("/switch-org", response_model=SwitchOrgResponse)
async def switch_org(
    body: SwitchOrgRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Switch active organization (placeholder for multi-org support)."""
    if current_user.org_id != body.org_id:
        # Future: check org_memberships table
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this organization",
        )

    stmt = select(Organization).where(Organization.id == body.org_id)
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    return SwitchOrgResponse(
        org_id=org.id,
        org_name=org.name,
        role=current_user.role,
    )


@router.get("/permissions", response_model=PermissionMatrixResponse)
async def get_permissions(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return the current user's permission matrix."""
    permissions = get_permissions_for_role(current_user.role)
    return PermissionMatrixResponse(
        role=current_user.role,
        permissions=permissions,
    )
