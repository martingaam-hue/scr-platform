"""
Unified Celery worker for SCR Platform.

Start worker:    celery -A app.worker worker --loglevel=info
Start beat:      celery -A app.worker beat --loglevel=info
Start both:      celery -A app.worker worker --beat --loglevel=info
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "scr_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.modules.signal_score.tasks",
        "app.modules.deal_intelligence.tasks",
        "app.modules.reporting.tasks",
        "app.modules.matching.tasks",
        "app.modules.projects.tasks",
        "app.modules.risk.tasks",
        "app.modules.due_diligence.tasks",
        "app.worker_tasks",
        "app.tasks.weekly_digest",
        "app.tasks.fx_rates",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,  # 24h
)

celery_app.conf.beat_schedule = {
    # ── External data feed refresh ──────────────────────────────────────────
    "refresh-fred-data": {
        "task": "app.worker_tasks.refresh_external_feed",
        "args": ["fred"],
        "schedule": 3600.0,  # every hour
    },
    "refresh-yahoo-finance": {
        "task": "app.worker_tasks.refresh_external_feed",
        "args": ["yahoo_finance"],
        "schedule": 3600.0,
    },
    "refresh-climate-data": {
        "task": "app.worker_tasks.refresh_external_feed",
        "args": ["noaa_climate"],
        "schedule": 43200.0,  # every 12h
    },
    "refresh-regulatory-data": {
        "task": "app.worker_tasks.refresh_external_feed",
        "args": ["regulations_gov"],
        "schedule": 21600.0,  # every 6h
    },
    "refresh-world-bank": {
        "task": "app.worker_tasks.refresh_external_feed",
        "args": ["world_bank"],
        "schedule": 86400.0,  # daily
    },
    # ── Risk monitoring ─────────────────────────────────────────────────────
    "run-risk-monitoring": {
        "task": "app.worker_tasks.risk_monitoring_cycle",
        "schedule": 21600.0,  # every 6h
    },
    # ── Live score updates ──────────────────────────────────────────────────
    "update-live-scores": {
        "task": "app.worker_tasks.check_live_score_updates",
        "schedule": 3600.0,  # hourly
    },
    # ── Weekly email digest ─────────────────────────────────────────────────
    "weekly-digest": {
        "task": "tasks.send_weekly_digests",
        "schedule": crontab(hour=20, minute=0, day_of_week=0),  # Sunday 8pm UTC
    },
    # ── FX rates (ECB reference rates) ──────────────────────────────────────
    "fetch-daily-fx-rates": {
        "task": "tasks.fetch_daily_fx_rates",
        "schedule": crontab(hour=15, minute=0),  # 3pm UTC = 4pm CET
    },
}
