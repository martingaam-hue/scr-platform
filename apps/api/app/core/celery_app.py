"""Shared Celery application instance.

Import this in task modules (instead of creating module-local Celery() instances).
worker.py imports this too and adds includes + beat schedule on top.

Using a shared app ensures tasks are always sent to the correct queues and are
registered in the worker's task registry — not in isolated per-module registries
that the worker's consumer can never find.
"""

from celery import Celery

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
