"""API key authentication for the Excel Add-in endpoints.

Validates the ``X-SCR-API-Key`` header, looks up the hashed key in
``org_api_keys``, and returns the associated ``org_id``.  The raw key is
never stored — only its SHA-256 hex digest.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db


async def verify_api_key(
    x_scr_api_key: str = Header(alias="X-SCR-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """Validate the ``X-SCR-API-Key`` request header and return the org_id.

    Raises ``401`` if the header is missing, the key is not found, or the
    key has been deactivated.
    """
    if not x_scr_api_key:
        raise HTTPException(status_code=401, detail="Missing X-SCR-API-Key header")

    key_hash = hashlib.sha256(x_scr_api_key.encode()).hexdigest()

    # Import here to avoid circular imports at module load time.
    from app.models.api_keys import OrgApiKey  # noqa: PLC0415

    stmt = select(OrgApiKey).where(
        OrgApiKey.key_hash == key_hash,
        OrgApiKey.is_active.is_(True),
    )
    result = await db.execute(stmt)
    key_row = result.scalar_one_or_none()

    if not key_row:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")

    # Stamp last_used_at — best-effort inside a savepoint so that a failure
    # here does not abort the outer transaction (and therefore the response).
    try:
        async with db.begin_nested():
            key_row.last_used_at = datetime.now(timezone.utc)
    except Exception:
        pass

    return key_row.org_id
