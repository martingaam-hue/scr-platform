"""
Unified Celery worker for SCR Platform.

Start worker:    celery -A app.worker worker --loglevel=info
Start beat:      celery -A app.worker beat --loglevel=info
Start both:      celery -A app.worker worker --beat --loglevel=info
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration as SentryCeleryIntegration

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
        "app.tasks.compliance",
        "app.tasks.watchlists",
        "app.tasks.blockchain",
        "app.tasks.benchmarks",
        "app.tasks.qa_sla",
        "app.tasks.monitoring",
        "app.tasks.crm_sync",
        "app.modules.expert_insights.tasks",
        "app.modules.webhooks.tasks",
        "app.modules.redaction.tasks",
        "app.modules.market_data.tasks",
        "app.tasks.backup",
    ],
)

if getattr(settings, "SENTRY_DSN", ""):
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=getattr(settings, "SENTRY_ENVIRONMENT", "development"),
        traces_sample_rate=getattr(settings, "SENTRY_TRACES_SAMPLE_RATE", 0.1),
        integrations=[SentryCeleryIntegration()],
        send_default_pii=False,
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
    # ── Compliance deadlines ─────────────────────────────────────────────────
    "check-upcoming-deadlines": {
        "task": "tasks.check_upcoming_deadlines",
        "schedule": crontab(hour=8, minute=0),  # 8am UTC daily
    },
    "flag-overdue-deadlines": {
        "task": "tasks.flag_overdue_deadlines",
        "schedule": crontab(hour=9, minute=0),  # 9am UTC daily
    },
    # ── Watchlist monitoring ─────────────────────────────────────────────────
    "check-watchlists": {
        "task": "tasks.check_watchlists",
        "schedule": crontab(minute="*/15"),  # every 15 minutes
    },
    # ── Blockchain anchor batching ────────────────────────────────────────────
    "batch-blockchain-anchors": {
        "task": "tasks.batch_blockchain_anchors",
        "schedule": crontab(hour="*/6", minute=0),  # every 6 hours
    },
    # ── Nightly benchmark aggregation ─────────────────────────────────────────
    "compute-nightly-benchmarks": {
        "task": "tasks.compute_nightly_benchmarks",
        "schedule": crontab(hour=3, minute=0),  # 3am UTC daily
    },
    # ── Daily metric snapshots ────────────────────────────────────────────────
    "record-daily-snapshots": {
        "task": "tasks.record_daily_snapshots",
        "schedule": crontab(hour=2, minute=0),  # 2am UTC daily
    },
    # ── Q&A SLA breach monitoring ─────────────────────────────────────────────
    "check-qa-sla": {
        "task": "tasks.check_qa_sla",
        "schedule": crontab(minute="*/30"),  # every 30 minutes
    },
    # ── Covenant & KPI compliance check ──────────────────────────────────────
    "check-all-covenants": {
        "task": "tasks.check_all_covenants",
        "schedule": crontab(hour=6, minute=0),  # 6am UTC daily
    },
    # ── CRM sync ─────────────────────────────────────────────────────────────
    "sync-crm-connections": {
        "task": "tasks.sync_crm_connections",
        "schedule": crontab(minute="*/15"),  # every 15 minutes
    },
    # ── Webhook retry ─────────────────────────────────────────────────────────
    "retry-pending-webhooks": {
        "task": "tasks.retry_pending_webhooks",
        "schedule": crontab(minute="*/5"),  # every 5 minutes
    },
    # ── Public market data (FRED + World Bank) ────────────────────────────────
    "fetch-market-data": {
        "task": "tasks.fetch_market_data",
        "schedule": crontab(hour=6, minute=30),  # 6:30am UTC daily (after FRED updates)
    },
    # ── Database backups ──────────────────────────────────────────────────────
    "backup-database-daily": {
        "task": "tasks.backup_database",
        "schedule": crontab(hour=3, minute=30),  # 03:30 UTC daily (after benchmarks at 03:00)
    },
    "prune-old-backups-weekly": {
        "task": "tasks.prune_old_backups",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),  # Sunday 04:00 UTC
    },
}
