"""Celery tasks for covenant & KPI monitoring + CloudWatch metrics."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from typing import Any

import boto3
import redis
import structlog
from celery import shared_task

from app.core.config import settings

logger = structlog.get_logger()

_CELERY_QUEUES = ("critical", "default", "bulk", "webhooks")


def _cw_client() -> Any:
    return boto3.client(
        "cloudwatch",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION,
    )


@shared_task(name="app.tasks.monitoring.publish_queue_metrics")
def publish_queue_metrics() -> dict:
    """Publish Celery queue depths to CloudWatch (SCR/Celery namespace).

    Runs every 60 s via Celery Beat. A single put_metric_data call batches
    all four queues so we stay within the CloudWatch 20-metric-per-call limit.
    Fails open on both Redis and CloudWatch errors — a missed data point is
    better than a crashed worker.
    """
    try:
        r = redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=5,
            socket_timeout=5,
            decode_responses=True,
        )
    except Exception as exc:
        logger.warning("queue_metrics_redis_connect_failed", error=str(exc))
        return {"status": "skipped", "reason": "redis_connect_failed"}

    now = datetime.now(UTC)
    metric_data: list[dict] = []
    depths: dict[str, int] = {}

    for queue in _CELERY_QUEUES:
        try:
            length: int = r.llen(f"celery:{queue}")
            depths[queue] = length
            metric_data.append(
                {
                    "MetricName": "QueueDepth",
                    "Dimensions": [
                        {"Name": "QueueName", "Value": queue},
                        {"Name": "Environment", "Value": settings.APP_ENV},
                    ],
                    "Value": float(length),
                    "Unit": "Count",
                    "Timestamp": now,
                }
            )
        except Exception as exc:
            logger.warning("queue_metrics_llen_failed", queue=queue, error=str(exc))

    with contextlib.suppress(Exception):
        r.close()

    if not metric_data:
        return {"status": "skipped", "reason": "no_metrics_collected"}

    try:
        _cw_client().put_metric_data(Namespace="SCR/Celery", MetricData=metric_data)
        logger.info("queue_metrics_published", depths=depths, env=settings.APP_ENV)
    except Exception as exc:
        logger.warning("queue_metrics_cloudwatch_failed", error=str(exc))
        return {"status": "error", "reason": str(exc), "depths": depths}

    return {"status": "ok", "published": len(metric_data), "depths": depths}


@shared_task(name="tasks.check_all_covenants")
def check_all_covenants() -> dict:
    """Run daily at 6am. Checks all non-waived covenants across all orgs."""
    import asyncio

    async def _run():
        from sqlalchemy import distinct, select

        from app.core.database import async_session_factory
        from app.models.monitoring import Covenant
        from app.modules.monitoring.service import MonitoringService

        async with async_session_factory() as db:
            org_ids = (
                (
                    await db.execute(
                        select(distinct(Covenant.org_id)).where(
                            Covenant.status != "waived",
                            Covenant.is_deleted.is_(False),
                        )
                    )
                )
                .scalars()
                .all()
            )

            total_changes = 0
            for org_id in org_ids:
                svc = MonitoringService(db, org_id)
                try:
                    changes = await svc.check_covenants()
                    total_changes += len(changes)
                except Exception as exc:
                    logger.warning(
                        "check_covenants_org_failed",
                        org_id=str(org_id),
                        error=str(exc),
                    )

            await db.commit()
            return {"org_count": len(org_ids), "status_changes": total_changes}

    result = asyncio.run(_run())
    logger.info("check_all_covenants_complete", **result)
    return result
