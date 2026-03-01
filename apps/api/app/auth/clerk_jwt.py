"""Clerk RS256 JWT verification via JWKS.

Fetches Clerk's public keys from the well-known JWKS endpoint, caches them
in Redis (shared across all worker processes) with an in-process fallback,
and verifies RS256-signed tokens.
"""

import json

import httpx
import structlog
from jose import JWTError, jwt

from app.core.config import settings

logger = structlog.get_logger()

_REDIS_KEY = "clerk:jwks"


async def _redis_client():
    """Return a short-lived Redis client, or None if Redis is unavailable."""
    try:
        from redis.asyncio import from_url  # type: ignore[import-untyped]
        return from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:  # noqa: BLE001
        return None


async def _fetch_jwks() -> dict:
    """Fetch JWKS from Clerk's well-known endpoint.

    Strategy:
    1. Try Redis cache (shared across all worker processes).
    2. Fetch from Clerk and repopulate Redis.
    Falls back gracefully if Redis is down.
    """
    # 1. Try Redis
    redis = await _redis_client()
    if redis:
        try:
            cached = await redis.get(_REDIS_KEY)
            if cached:
                await redis.aclose()
                return json.loads(cached)
        except Exception:  # noqa: BLE001
            pass
        finally:
            try:
                await redis.aclose()
            except Exception:  # noqa: BLE001
                pass

    # 2. Fetch from Clerk
    jwks_url = f"{settings.CLERK_ISSUER_URL}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url, timeout=10.0)
        response.raise_for_status()
        jwks = response.json()

    logger.info("clerk_jwks_refreshed", keys_count=len(jwks.get("keys", [])))

    # 3. Store in Redis with TTL
    redis = await _redis_client()
    if redis:
        try:
            await redis.setex(_REDIS_KEY, settings.CLERK_JWKS_CACHE_TTL, json.dumps(jwks))
        except Exception:  # noqa: BLE001
            pass
        finally:
            try:
                await redis.aclose()
            except Exception:  # noqa: BLE001
                pass

    return jwks


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


async def clear_jwks_cache() -> None:
    """Clear the JWKS cache in Redis (useful for testing and key rotation)."""
    redis = await _redis_client()
    if redis:
        try:
            await redis.delete(_REDIS_KEY)
        except Exception:  # noqa: BLE001
            pass
        finally:
            try:
                await redis.aclose()
            except Exception:  # noqa: BLE001
                pass
