# DEPRECATED: Use app.auth.dependencies.get_current_user for Clerk RS256 auth.
# This module is retained for potential service-to-service HS256 tokens
# (e.g. API-to-AI-Gateway internal calls).

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer()

ALGORITHM = "HS256"


def create_access_token(data: dict[str, str | datetime], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict[str, str]:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        org_id: str | None = payload.get("org_id")
        if user_id is None or org_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing claims",
            )
        return {"user_id": user_id, "org_id": org_id, "role": payload.get("role", "viewer")}
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from e
