"""Clerk RS256 JWT verification via JWKS.

Fetches Clerk's public keys from the well-known JWKS endpoint, caches them
in-process, and verifies RS256-signed session tokens.
"""

import time

import httpx
import structlog
from jose import JWTError, jwt

from app.core.config import settings

logger = structlog.get_logger()

# Module-level JWKS cache
_jwks_cache: dict | None = None
_jwks_cache_timestamp: float = 0.0


async def _fetch_jwks() -> dict:
    """Fetch JWKS from Clerk's well-known endpoint. Returns cached if fresh."""
    global _jwks_cache, _jwks_cache_timestamp

    now = time.time()
    if _jwks_cache and (now - _jwks_cache_timestamp) < settings.CLERK_JWKS_CACHE_TTL:
        return _jwks_cache

    jwks_url = f"{settings.CLERK_ISSUER_URL}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url, timeout=10.0)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cache_timestamp = now
        logger.info("clerk_jwks_refreshed", keys_count=len(_jwks_cache.get("keys", [])))
        return _jwks_cache


def _get_signing_key(jwks: dict, token: str) -> dict:
    """Match the JWT header's kid to the correct JWKS key."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    raise JWTError(f"No matching key found for kid={kid}")


async def verify_clerk_token(token: str) -> dict:
    """
    Verify a Clerk-issued RS256 JWT.

    Returns the decoded payload with claims (sub, email, etc.).
    Raises JWTError on any validation failure.
    """
    jwks = await _fetch_jwks()
    signing_key = _get_signing_key(jwks, token)

    payload = jwt.decode(
        token,
        signing_key,
        algorithms=["RS256"],
        issuer=settings.CLERK_ISSUER_URL,
        options={
            "verify_aud": False,  # Clerk may not set aud; enable if configured
            "verify_iss": bool(settings.CLERK_ISSUER_URL),
            "verify_exp": True,
        },
    )
    return payload


def clear_jwks_cache() -> None:
    """Clear the JWKS cache (useful for testing and key rotation)."""
    global _jwks_cache, _jwks_cache_timestamp
    _jwks_cache = None
    _jwks_cache_timestamp = 0.0
