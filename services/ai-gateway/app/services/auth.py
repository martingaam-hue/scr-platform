from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer()


def _valid_keys() -> set[str]:
    """Return the set of currently accepted API keys (current + optional previous)."""
    keys = {settings.AI_GATEWAY_API_KEY}
    if settings.AI_GATEWAY_API_KEY_PREVIOUS:
        keys.add(settings.AI_GATEWAY_API_KEY_PREVIOUS)
    return keys


def validate_api_key(api_key: str) -> bool:
    return api_key in _valid_keys()


def verify_gateway_key(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    if not validate_api_key(credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid AI Gateway API key",
        )
    return credentials.credentials
