"""FastAPI auth dependencies: get_current_user, require_role, require_permission, require_org_access."""

import uuid

import redis.asyncio as aioredis
import sentry_sdk
import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk_jwt import verify_clerk_token
from app.auth.rbac import check_object_permission, check_permission
from app.core.config import settings
from app.core.database import get_db
from app.models.core import Organization, User
from app.models.enums import UserRole
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """
    Verify Clerk JWT and resolve the SCR platform user.

    Decodes JWT -> gets Clerk's `sub` claim (external_auth_id) ->
    looks up User in DB to get internal user_id, org_id, role.
    Always checks is_active and is_deleted.
    """
    token = credentials.credentials
    try:
        payload = await verify_clerk_token(token)
    except (JWTError, Exception) as e:
        logger.warning("jwt_verification_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    # Look up user by Clerk external ID (unique index: ix_users_external_auth_id)
    stmt = select(User).where(
        User.external_auth_id == clerk_user_id,
        User.is_active.is_(True),
        User.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("user_not_found_for_clerk_id", clerk_id=clerk_user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    current_user = CurrentUser(
        user_id=user.id,
        org_id=user.org_id,
        role=user.role,
        email=user.email,
        external_auth_id=clerk_user_id,
    )

    # Enrich Sentry scope with identity (PII-free: no email)
    sentry_sdk.set_user({"id": str(user.id)})
    sentry_sdk.set_tag("org_id", str(user.org_id))
    sentry_sdk.set_tag("user_role", user.role.value)

    # Cache org subscription tier in Redis so the rate limiter can apply tier-based
    # limits without a DB lookup on every request (TTL 300 s, best-effort).
    try:
        org = (
            await db.execute(select(Organization).where(Organization.id == user.org_id))
        ).scalar_one_or_none()
        if org:
            r = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            await r.setex(f"org:tier:{user.org_id}", 300, org.subscription_tier.value)
            await r.aclose()
    except Exception:
        pass  # Non-blocking: rate limiter falls back to foundation limits on cache miss

    return current_user


def require_role(allowed_roles: list[UserRole]):
    """
    Dependency factory: checks if current user has one of the allowed roles.

    Usage:
        @router.post("/projects", dependencies=[Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))])
    """

    async def _check_role(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' not authorized. Required: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return _check_role


def require_permission(action: str, resource_type: str):
    """
    Dependency factory: checks a specific (action, resource_type) permission.

    Usage:
        @router.post("/projects", dependencies=[Depends(require_permission("create", "project"))])
    """

    async def _check_perm(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not check_permission(current_user.role, action, resource_type):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {action} on {resource_type}",
            )
        return current_user

    return _check_perm


def require_object_permission(
    action: str,
    resource_type: str,
    id_param: str = "id",
    rbac_resource_type: str | None = None,
):
    """Dependency factory for object-level permission checks.

    Performs a two-stage check:
      1. Role-level: does the user's role allow `action` on `resource_type`?
      2. Object-level: does the user have an ownership record for this specific
         resource_id? (skipped for manager/admin — they always pass)

    When OBJECT_LEVEL_RBAC_ENABLED=False (default/audit mode):
        Logs a warning but allows access so the flag can be deployed safely.
    When OBJECT_LEVEL_RBAC_ENABLED=True:
        Returns 403 if no valid ownership record exists.

    Usage:
        @router.get("/{doc_id}", dependencies=[Depends(
            require_object_permission("download", "document", id_param="doc_id")
        )])
    """

    async def _check_object_perm(
        request: Request,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> CurrentUser:
        from app.core.config import settings

        # Stage 1: role-level permission (use rbac_resource_type when resource_type
        # is a fine-grained ownership type not present in the permission matrix)
        _rbac_type = rbac_resource_type or resource_type
        if not check_permission(current_user.role, action, _rbac_type):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {action} on {_rbac_type}",
            )

        # Stage 2: object-level — extract resource_id from path params
        raw_id = request.path_params.get(id_param)
        if raw_id is None:
            # No resource ID in path — skip object check (collection endpoints)
            return current_user

        try:
            resource_id = uuid.UUID(str(raw_id))
        except (ValueError, AttributeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid resource ID",
            ) from exc

        allowed = await check_object_permission(
            db=db,
            user_id=current_user.user_id,
            org_id=current_user.org_id,
            role=current_user.role,
            resource_type=resource_type,
            resource_id=resource_id,
            required_level="viewer",
        )

        if not allowed:
            if not settings.OBJECT_LEVEL_RBAC_ENABLED:
                logger.warning(
                    "object_rbac_would_deny",
                    user_id=str(current_user.user_id),
                    resource_type=resource_type,
                    resource_id=str(resource_id),
                    action=action,
                )
                return current_user
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(f"Access denied: no {resource_type} permission for resource {resource_id}"),
            )

        return current_user

    return _check_object_perm


async def require_org_access(
    org_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Ensure the current user belongs to the specified organization."""
    if current_user.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: user does not belong to this organization",
        )
    return current_user


async def get_db_user(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Load the full SQLAlchemy User model. Use when you need the complete record."""
    stmt = select(User).where(User.id == current_user.user_id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def set_tenant_context(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Set org_id and user_id on request.state for middleware consumption."""
    request.state.org_id = current_user.org_id
    request.state.user_id = current_user.user_id
    return current_user
