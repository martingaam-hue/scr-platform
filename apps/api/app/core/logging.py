"""Structlog configuration with contextvars support.

Call ``configure_logging(service)`` once at application startup — before any
logger is first used — to activate correlation ID propagation.  Calling it
more than once is safe (structlog.configure is idempotent for our use-case).

The ``service`` label ("api", "worker", "ai-gateway") is bound globally so
every log line emitted by that process carries it, which allows CloudWatch
Insights to filter by service without relying on log-group names alone.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(service: str, log_level: int = logging.INFO) -> None:
    """Configure structlog processors for the given service.

    Processor chain:
    1. merge_contextvars  — injects correlation_id / org_id / … bound via
                            structlog.contextvars.bind_contextvars()
    2. add_log_level      — adds "level" key
    3. TimeStamper        — ISO-8601 "timestamp" key
    4. StackInfoRenderer  — renders stack_info if present
    5. ConsoleRenderer    — human-readable on TTY (dev)
       JSONRenderer       — machine-readable elsewhere (staging / production)

    Binding the service name here means every log line includes it, letting
    CloudWatch Insights correlate logs across api / worker / ai-gateway.
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    renderer: Any = (
        structlog.dev.ConsoleRenderer()
        if sys.stdout.isatty()
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        # cache_logger_on_first_use must be False so that contextvars (bound
        # per-request) are evaluated at log-call time, not at logger creation.
        cache_logger_on_first_use=False,
    )

    # Bind the service name permanently for this process.
    structlog.contextvars.bind_contextvars(service=service)
