"""Standardized error responses across all API endpoints."""
from typing import Any

import sentry_sdk
import structlog
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error envelope returned by all API error handlers."""
    error: str
    message: str
    detail: Any = None
    request_id: str = "unknown"

logger = structlog.get_logger()


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions and return a consistent JSON envelope."""
    request_id = request.headers.get("x-request-id", "unknown")

    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        request_id=request_id,
    )

    sentry_sdk.capture_exception(exc)

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Our team has been notified.",
            "request_id": request_id,
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Standardize HTTPException responses into the same JSON envelope."""
    request_id = request.headers.get("x-request-id", "unknown")

    if isinstance(exc.detail, dict):
        error = exc.detail.get("error", f"http_{exc.status_code}")
        message = exc.detail.get("message", str(exc.detail))
        detail: Any = exc.detail.get("detail")
    else:
        error = f"http_{exc.status_code}"
        message = str(exc.detail)
        # Preserve plain-string detail so existing tests that check
        # resp.json()["detail"] continue to work.
        detail = exc.detail

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error,
            "message": message,
            "detail": detail,
            "request_id": request_id,
        },
        headers=dict(exc.headers or {}),
    )
