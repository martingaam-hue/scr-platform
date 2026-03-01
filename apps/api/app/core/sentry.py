"""Centralised Sentry initialisation for the SCR API and Celery worker."""

import structlog
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration

logger = structlog.get_logger()

_SENSITIVE_HEADERS = {"authorization", "cookie", "x-api-key"}


def _scrub_sensitive_data(event: dict, hint: dict) -> dict:
    """Remove auth headers before sending to Sentry."""
    request = event.get("request", {})
    headers = request.get("headers", {})
    for header in list(headers):
        if header.lower() in _SENSITIVE_HEADERS:
            headers[header] = "[REDACTED]"
    return event


def init_sentry(
    dsn: str | None,
    environment: str = "development",
    release: str | None = None,
) -> None:
    """Initialise Sentry with all relevant integrations.

    Call this BEFORE creating the FastAPI app or Celery instance so that
    auto-instrumentation can hook in at import time.

    No-op when dsn is None or empty — safe to call unconditionally.
    """
    if not dsn:
        logger.warning("sentry_disabled", reason="SENTRY_DSN not set")
        return

    is_prod = environment == "production"

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        # Sample 10% of transactions in prod; 100% elsewhere for full visibility
        traces_sample_rate=0.1 if is_prod else 1.0,
        # Profiling only in prod (high overhead)
        profiles_sample_rate=0.1 if is_prod else 0.0,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            CeleryIntegration(monitor_beat_tasks=True),
            RedisIntegration(),
            HttpxIntegration(),
        ],
        send_default_pii=False,      # GDPR: never send PII
        before_send=_scrub_sensitive_data,
        enable_tracing=True,
    )
    logger.info(
        "sentry_initialized",
        environment=environment,
        traces_sample_rate=0.1 if is_prod else 1.0,
    )
