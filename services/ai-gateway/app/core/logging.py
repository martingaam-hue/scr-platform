"""Structlog configuration for the AI Gateway service.

Identical contract to apps/api/app/core/logging.py — kept separate because
the two services have independent Python environments.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(service: str, log_level: int = logging.INFO) -> None:
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
        cache_logger_on_first_use=False,
    )

    structlog.contextvars.bind_contextvars(service=service)
