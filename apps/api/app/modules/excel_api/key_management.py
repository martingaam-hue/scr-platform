"""API key management helpers used by the settings / admin router.

These functions are intentionally framework-agnostic (no FastAPI specifics)
so they can be called from any router or background task.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_keys import OrgApiKey


async def generate_api_key(
    db: AsyncSession,
    org_id: uuid.UUID,
    name: str,
    scopes: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a new API key for the given org.

    The raw key is returned **once** in the response dict.  Only its
    SHA-256 hash and the first-8-character prefix are persisted.

    Returns:
        ``{"raw_key": str, "key_id": str, "prefix": str}``
    """
    raw_key = f"scr_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:8]

    key = OrgApiKey(
        org_id=org_id,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=scopes or ["read"],
    )
    db.add(key)
    await db.flush()
    await db.refresh(key)

    return {"raw_key": raw_key, "key_id": str(key.id), "prefix": key_prefix}


async def list_api_keys(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[OrgApiKey]:
    """Return all active API keys for the given org, newest first."""
    result = await db.execute(
        select(OrgApiKey)
        .where(
            OrgApiKey.org_id == org_id,
            OrgApiKey.is_active.is_(True),
        )
        .order_by(OrgApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_api_key(
    db: AsyncSession,
    key_id: uuid.UUID,
    org_id: uuid.UUID,
) -> bool:
    """Deactivate an API key by setting ``is_active = False``.

    Returns ``True`` if the key was found and deactivated, ``False`` if it
    did not exist or did not belong to the given org.
    """
    result = await db.execute(
        select(OrgApiKey).where(
            OrgApiKey.id == key_id,
            OrgApiKey.org_id == org_id,
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        return False
    key.is_active = False
    await db.flush()
    return True
