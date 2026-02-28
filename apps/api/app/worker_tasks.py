"""Celery background tasks for scheduled jobs.

These run in the Celery beat worker, not in the FastAPI process.
All DB operations use SyncSession pattern (same as signal_score/tasks.py).
"""
import structlog

logger = structlog.get_logger()


def _get_celery_app():
    from app.worker import celery_app
    return celery_app


# Lazy import celery_app to avoid circular imports
from app.core.config import settings
from celery import Celery

_celery = Celery("scr_worker", broker=settings.CELERY_BROKER_URL)


@_celery.task(name="app.worker_tasks.refresh_external_feed", bind=True, max_retries=2)
def refresh_external_feed(self, feed_name: str) -> dict:
    """Trigger feed refresh in AI Gateway via HTTP."""
    import httpx

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{settings.AI_GATEWAY_URL}/v1/feeds/{feed_name}/refresh",
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
            )
            resp.raise_for_status()
            logger.info("feed_refreshed", feed=feed_name)
            return resp.json()
    except Exception as exc:
        logger.error("feed_refresh_failed", feed=feed_name, error=str(exc))
        raise self.retry(exc=exc, countdown=60) from exc


@_celery.task(name="app.worker_tasks.risk_monitoring_cycle", bind=True, max_retries=1)
def risk_monitoring_cycle(self) -> dict:
    """Run risk monitoring check for all active portfolios."""
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    try:
        engine = create_engine(settings.DATABASE_URL_SYNC)
        with Session(engine) as session:
            from app.models.projects import Portfolio  # type: ignore[attr-defined]
            stmt = select(Portfolio).where(Portfolio.is_deleted.is_(False))  # type: ignore[attr-defined]
            portfolios = session.execute(stmt).scalars().all()

            count = 0
            for portfolio in portfolios:
                try:
                    # Trigger risk monitoring for each portfolio
                    import httpx
                    with httpx.Client(timeout=10.0) as client:
                        client.post(
                            f"{settings.API_BASE_URL if hasattr(settings, 'API_BASE_URL') else 'http://localhost:8000'}/risk/monitoring/{portfolio.id}/trigger",
                            headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
                        )
                    count += 1
                except Exception as e:
                    logger.warning("portfolio_monitoring_failed", portfolio_id=str(portfolio.id), error=str(e))

        logger.info("risk_monitoring_cycle_complete", portfolios_checked=count)
        return {"portfolios_checked": count}
    except Exception as exc:
        logger.error("risk_monitoring_cycle_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300) from exc


@_celery.task(name="app.worker_tasks.check_live_score_updates", bind=True, max_retries=1)
def check_live_score_updates(self) -> dict:
    """Check for projects with live scoring enabled and trigger updates."""
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    try:
        engine = create_engine(settings.DATABASE_URL_SYNC)
        with Session(engine) as session:
            from app.models.projects import SignalScore
            stmt = select(SignalScore).where(SignalScore.is_live.is_(True))
            scores = session.execute(stmt).scalars().all()

            updated = 0
            for score in scores[:50]:  # Limit per cycle to avoid overload
                try:
                    from app.modules.signal_score.tasks import calculate_signal_score_task
                    calculate_signal_score_task.delay(str(score.project_id))
                    updated += 1
                except Exception as e:
                    logger.warning("live_score_update_failed", project_id=str(score.project_id), error=str(e))

        logger.info("live_score_updates_triggered", count=updated)
        return {"updated": updated}
    except Exception as exc:
        logger.error("live_score_cycle_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=120) from exc
