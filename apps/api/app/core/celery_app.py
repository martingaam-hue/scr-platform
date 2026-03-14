"""Shared Celery application instance.

Import this in task modules (instead of creating module-local Celery() instances).
worker.py imports this too and adds includes + beat schedule on top.

Using a shared app ensures tasks are always sent to the correct queues and are
registered in the worker's task registry — not in isolated per-module registries
that the worker's consumer can never find.

Correlation ID propagation
--------------------------
``before_task_publish`` reads the current structlog correlation_id from
contextvars and injects it into the task's Celery headers so it travels
through the broker to the worker.

``task_prerun`` reads the header back from the task request and binds it to
the worker's structlog contextvars, so every log line during the task carries
the originating request's correlation_id.

``task_postrun`` clears the contextvars to prevent context bleed between
tasks that run on the same worker process/thread.
"""

from __future__ import annotations

import uuid

import structlog
from celery import Celery
from celery.signals import before_task_publish, task_postrun, task_prerun

from app.core.celery_config import (
    CELERY_QUEUES,
    CELERY_TASK_ANNOTATIONS,
    CELERY_TASK_ROUTES,
)
from app.core.config import settings

celery_app = Celery(
    "scr_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,
    task_queues=CELERY_QUEUES,
    task_routes=CELERY_TASK_ROUTES,
    task_annotations=CELERY_TASK_ANNOTATIONS,
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
)

# ── Correlation ID propagation via Celery signals ─────────────────────────────


@before_task_publish.connect
def _inject_correlation_id(headers: dict, **_kw: object) -> None:
    """Copy the current request's correlation_id into the outgoing task headers.

    Called in the *publisher* process (API worker or another Celery task) just
    before the task message is sent to the broker.  The headers dict is mutable
    and its contents are preserved through the broker to the consumer side.
    """
    cid = structlog.contextvars.get_contextvars().get("correlation_id")
    if cid:
        headers["correlation_id"] = cid


@task_prerun.connect
def _bind_correlation_id(task: object, **_kw: object) -> None:
    """Bind correlation_id from task headers to structlog context.

    Called in the *consumer* (worker) process just before the task body runs.
    If no correlation_id arrived (e.g. task dispatched from a Beat schedule or
    a manual .delay() call outside a request context) a fresh UUID is generated
    so every task log line still has a traceable ID.
    """
    structlog.contextvars.clear_contextvars()
    request_headers: dict = getattr(getattr(task, "request", None), "headers", None) or {}
    cid: str = request_headers.get("correlation_id") or str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(correlation_id=cid, service="worker")


@task_postrun.connect
def _clear_correlation_id(**_kw: object) -> None:
    """Clear structlog contextvars after the task finishes."""
    structlog.contextvars.clear_contextvars()
