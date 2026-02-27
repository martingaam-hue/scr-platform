"""Settings service: org management, team, API keys, preferences."""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Organization, User
from app.models.enums import UserRole
from app.modules.settings.schemas import (
    ApiKeyCreatedResponse,
    ApiKeyItem,
    InviteUserRequest,
    NotificationPreferences,
    OrgUpdateRequest,
    PreferencesResponse,
)

logger = structlog.get_logger()

# ── Org ──────────────────────────────────────────────────────────────────────


async def get_org(db: AsyncSession, org_id: uuid.UUID) -> Organization:
    org = await db.get(Organization, org_id)
    if not org or org.is_deleted:
        raise LookupError(f"Organization {org_id} not found")
    return org


async def update_org(
    db: AsyncSession,
    org_id: uuid.UUID,
    body: OrgUpdateRequest,
) -> Organization:
    org = await get_org(db, org_id)
    if body.name is not None:
        org.name = body.name
    if body.logo_url is not None:
        org.logo_url = body.logo_url
    if body.settings is not None:
        # Merge — preserve api_keys and other system keys
        existing = dict(org.settings or {})
        for k, v in body.settings.items():
            existing[k] = v
        org.settings = existing
    return org


# ── Team ─────────────────────────────────────────────────────────────────────


async def list_org_users(db: AsyncSession, org_id: uuid.UUID) -> list[User]:
    result = await db.execute(
        select(User)
        .where(User.org_id == org_id, User.is_deleted.is_(False))
        .order_by(User.created_at)
    )
    return list(result.scalars().all())


async def get_user(
    db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID
) -> User:
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.org_id == org_id,
            User.is_deleted.is_(False),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise LookupError(f"User {user_id} not found in org")
    return user


async def update_user_role(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    role: UserRole,
) -> User:
    user = await get_user(db, org_id, user_id)
    user.role = role
    return user


async def toggle_user_status(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    is_active: bool,
) -> User:
    user = await get_user(db, org_id, user_id)
    user.is_active = is_active
    return user


async def invite_user(
    db: AsyncSession,
    org_id: uuid.UUID,
    body: InviteUserRequest,
) -> User:
    # Check for existing
    existing = await db.execute(
        select(User).where(User.email == body.email, User.is_deleted.is_(False))
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"A user with email {body.email} already exists")

    # Create pending user (external_auth_id will be linked on first Clerk sign-in)
    user = User(
        org_id=org_id,
        email=str(body.email),
        full_name=body.full_name,
        role=body.role,
        external_auth_id=f"pending_{uuid.uuid4().hex}",  # placeholder
        is_active=False,  # not active until they complete sign-up
    )
    db.add(user)
    logger.info("user_invited", email=body.email, org_id=str(org_id))
    return user


# ── API Keys ─────────────────────────────────────────────────────────────────
# Keys stored in org.settings["api_keys"] as a list of metadata dicts.
# The actual key is never stored; only a SHA-256 hash is kept for verification.


def _key_store(org: Organization) -> list[dict[str, Any]]:
    settings = org.settings or {}
    return list(settings.get("api_keys", []))


def list_api_keys(org: Organization) -> list[ApiKeyItem]:
    return [
        ApiKeyItem(
            id=k["id"],
            name=k["name"],
            prefix=k["prefix"],
            is_active=k["is_active"],
            created_at=k["created_at"],
            last_used_at=k.get("last_used_at"),
        )
        for k in _key_store(org)
    ]


def create_api_key(org: Organization, name: str) -> ApiKeyCreatedResponse:
    raw_key = f"scr_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_id = uuid.uuid4().hex[:16]
    now = datetime.now(timezone.utc).isoformat()

    entry: dict[str, Any] = {
        "id": key_id,
        "name": name,
        "prefix": raw_key[:8],
        "key_hash": key_hash,
        "is_active": True,
        "created_at": now,
        "last_used_at": None,
    }

    settings = dict(org.settings or {})
    keys = list(settings.get("api_keys", []))
    keys.append(entry)
    settings["api_keys"] = keys
    org.settings = settings

    return ApiKeyCreatedResponse(
        id=key_id,
        name=name,
        key=raw_key,
        created_at=now,
    )


def revoke_api_key(org: Organization, key_id: str) -> bool:
    settings = dict(org.settings or {})
    keys = list(settings.get("api_keys", []))
    updated = False
    for k in keys:
        if k["id"] == key_id:
            k["is_active"] = False
            updated = True
            break
    if not updated:
        raise LookupError(f"API key {key_id} not found")
    settings["api_keys"] = keys
    org.settings = settings
    return True


# ── Preferences ──────────────────────────────────────────────────────────────

_NOTIF_DEFAULTS: dict[str, Any] = {
    "email_match_alerts": True,
    "email_project_updates": True,
    "email_report_ready": True,
    "email_weekly_digest": False,
    "in_app_mentions": True,
    "in_app_match_alerts": True,
    "in_app_status_changes": True,
    "digest_frequency": "weekly",
}


async def get_user_preferences(
    db: AsyncSession, user_id: uuid.UUID
) -> PreferencesResponse:
    user = await db.get(User, user_id)
    if not user:
        raise LookupError(f"User {user_id} not found")
    raw = dict(user.preferences or {})
    notif_raw = {**_NOTIF_DEFAULTS, **raw.get("notification", {})}
    return PreferencesResponse(
        notification=NotificationPreferences(**notif_raw),
        raw=raw,
    )


async def update_user_preferences(
    db: AsyncSession,
    user_id: uuid.UUID,
    notification: NotificationPreferences | None,
    extra: dict[str, Any] | None,
) -> PreferencesResponse:
    user = await db.get(User, user_id)
    if not user:
        raise LookupError(f"User {user_id} not found")
    raw = dict(user.preferences or {})
    if notification is not None:
        raw["notification"] = notification.model_dump()
    if extra:
        for k, v in extra.items():
            if k != "notification":
                raw[k] = v
    user.preferences = raw
    notif_raw = {**_NOTIF_DEFAULTS, **raw.get("notification", {})}
    return PreferencesResponse(
        notification=NotificationPreferences(**notif_raw),
        raw=raw,
    )
