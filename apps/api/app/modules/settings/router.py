"""Settings API router: org profile, team, API keys, preferences, branding."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.models.enums import OrgType, SubscriptionStatus, SubscriptionTier
from app.modules.settings import service
from app.modules.settings.schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeyListResponse,
    BrandingResponse,
    BrandingUpdateRequest,
    InviteUserRequest,
    NotificationPreferences,
    OrgResponse,
    OrgUpdateRequest,
    PreferencesResponse,
    TeamListResponse,
    TeamMember,
    ToggleUserStatusRequest,
    UpdateUserRoleRequest,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/settings", tags=["settings"])


# ── Org ──────────────────────────────────────────────────────────────────────


@router.get("/org", response_model=OrgResponse)
async def get_org(
    current_user: CurrentUser = Depends(require_permission("view", "settings")),
    db: AsyncSession = Depends(get_db),
):
    """Get current organisation profile."""
    try:
        org = await service.get_org(db, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return OrgResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        type=org.type,
        logo_url=org.logo_url,
        settings={
            k: v
            for k, v in (org.settings or {}).items()
            if k != "api_keys"  # omit key store from general settings endpoint
        },
        subscription_tier=org.subscription_tier,
        subscription_status=org.subscription_status,
        created_at=org.created_at,
    )


@router.put("/org", response_model=OrgResponse)
async def update_org(
    body: OrgUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("admin", "settings")),
    db: AsyncSession = Depends(get_db),
):
    """Update org name, logo, or custom settings (admin only)."""
    try:
        org = await service.update_org(db, current_user.org_id, body)
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return OrgResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        type=org.type,
        logo_url=org.logo_url,
        settings={k: v for k, v in (org.settings or {}).items() if k != "api_keys"},
        subscription_tier=org.subscription_tier,
        subscription_status=org.subscription_status,
        created_at=org.created_at,
    )


# ── Team ─────────────────────────────────────────────────────────────────────


@router.get("/team", response_model=TeamListResponse)
async def list_team(
    current_user: CurrentUser = Depends(require_permission("view", "settings")),
    db: AsyncSession = Depends(get_db),
):
    """List all users in current org."""
    users = await service.list_org_users(db, current_user.org_id)
    items = [
        TeamMember(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            avatar_url=u.avatar_url,
            is_active=u.is_active,
            mfa_enabled=u.mfa_enabled,
            last_login_at=u.last_login_at,
            created_at=u.created_at,
        )
        for u in users
    ]
    return TeamListResponse(items=items, total=len(items))


@router.post(
    "/team/invite",
    response_model=TeamMember,
    status_code=status.HTTP_201_CREATED,
)
async def invite_user(
    body: InviteUserRequest,
    current_user: CurrentUser = Depends(require_permission("admin", "settings")),
    db: AsyncSession = Depends(get_db),
):
    """Invite a new user to the organisation."""
    try:
        user = await service.invite_user(db, current_user.org_id, body)
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return TeamMember(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        mfa_enabled=user.mfa_enabled,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.put("/team/{user_id}/role", response_model=TeamMember)
async def update_role(
    user_id: uuid.UUID,
    body: UpdateUserRoleRequest,
    current_user: CurrentUser = Depends(require_permission("admin", "settings")),
    db: AsyncSession = Depends(get_db),
):
    """Change a team member's role."""
    try:
        user = await service.update_user_role(
            db, current_user.org_id, user_id, body.role
        )
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return TeamMember(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        mfa_enabled=user.mfa_enabled,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.put("/team/{user_id}/status", response_model=TeamMember)
async def toggle_status(
    user_id: uuid.UUID,
    body: ToggleUserStatusRequest,
    current_user: CurrentUser = Depends(require_permission("admin", "settings")),
    db: AsyncSession = Depends(get_db),
):
    """Activate or deactivate a team member."""
    try:
        user = await service.toggle_user_status(
            db, current_user.org_id, user_id, body.is_active
        )
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return TeamMember(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        mfa_enabled=user.mfa_enabled,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


# ── API Keys ─────────────────────────────────────────────────────────────────


@router.get("/api-keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    current_user: CurrentUser = Depends(require_permission("admin", "settings")),
    db: AsyncSession = Depends(get_db),
):
    """List API keys for the org."""
    try:
        org = await service.get_org(db, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ApiKeyListResponse(items=service.list_api_keys(org))


@router.post(
    "/api-keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    body: ApiKeyCreateRequest,
    current_user: CurrentUser = Depends(require_permission("admin", "settings")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key (returned once — store it securely)."""
    try:
        org = await service.get_org(db, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    result = service.create_api_key(org, body.name)
    await db.commit()
    return result


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    current_user: CurrentUser = Depends(require_permission("admin", "settings")),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key."""
    try:
        org = await service.get_org(db, current_user.org_id)
        service.revoke_api_key(org, key_id)
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Preferences ──────────────────────────────────────────────────────────────


@router.get("/preferences", response_model=PreferencesResponse)
async def get_preferences(
    current_user: CurrentUser = Depends(require_permission("view", "settings")),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's notification preferences."""
    try:
        return await service.get_user_preferences(db, current_user.user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/preferences", response_model=PreferencesResponse)
async def update_preferences(
    body: NotificationPreferences,
    current_user: CurrentUser = Depends(require_permission("view", "settings")),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's notification preferences."""
    try:
        result = await service.update_user_preferences(
            db, current_user.user_id, notification=body, extra=None
        )
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Branding ──────────────────────────────────────────────────────────────────


@router.get("/branding", response_model=BrandingResponse)
async def get_branding(
    current_user: CurrentUser = Depends(require_permission("view", "settings")),
    db: AsyncSession = Depends(get_db),
):
    """Get organisation branding settings (returns defaults if not configured)."""
    try:
        branding = await service.get_branding(db, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return BrandingResponse(org_id=current_user.org_id, **branding.model_dump())


@router.put("/branding", response_model=BrandingResponse)
async def update_branding(
    body: BrandingUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("admin", "settings")),
    db: AsyncSession = Depends(get_db),
):
    """Update organisation branding settings (admin only)."""
    try:
        branding = await service.update_branding(db, current_user.org_id, body)
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return BrandingResponse(org_id=current_user.org_id, **branding.model_dump())
