"""
Unified Celery worker for SCR Platform.

Start worker:    celery -A app.worker worker --loglevel=info
Start beat:      celery -A app.worker beat --loglevel=info
Start both:      celery -A app.worker worker --beat --loglevel=info
"""

from celery.schedules import crontab

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.sentry import init_sentry

# Sentry must be initialised before Celery tasks are registered
init_sentry(settings.SENTRY_DSN, settings.SENTRY_ENVIRONMENT, settings.APP_VERSION)

celery_app.conf.include = [
    "app.modules.signal_score.tasks",
    "app.modules.deal_intelligence.tasks",
    "app.modules.reporting.tasks",
    "app.modules.matching.tasks",
    "app.modules.projects.tasks",
    "app.modules.risk.tasks",
    "app.modules.due_diligence.tasks",
    "app.modules.legal.tasks",
    "app.modules.tax_credits.tasks",
    "app.modules.valuation.tasks",
    "app.modules.dataroom.tasks",
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
    "app.tasks.data_retention",
    "app.tasks.partition_manager",
    "app.tasks.external_data",
    "app.tasks.stuck_docs",
    "app.modules.alley.signal_score.tasks",
    "app.modules.alley.risk.tasks",
    "app.modules.alley.advisor.tasks",
    "app.modules.alley.score_performance.tasks",
    "app.modules.market_enrichment.tasks",
]

celery_app.conf.beat_schedule = {
    # ── Matching score refresh ────────────────────────────────────────────────
    "batch-match-refresh": {
        "task": "app.modules.matching.tasks.batch_calculate_matches",
        "schedule": crontab(hour=2, minute=0),  # daily 02:00 UTC
    },
    # ── Stuck document cleanup ───────────────────────────────────────────────
    "cleanup-stuck-documents": {
        "task": "tasks.cleanup_stuck_documents",
        "schedule": crontab(minute="*/5"),  # every 5 minutes
    },
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
    # ── Backup orchestrator (replaces Gap Fix Block 10 tasks) ─────────────────
    "nightly-backup": {
        "task": "tasks.nightly_backup",
        "schedule": crontab(hour=2, minute=0),  # 02:00 UTC daily
    },
    "weekly-backup-test": {
        "task": "tasks.weekly_backup_test",
        "schedule": crontab(hour=5, minute=0, day_of_week=0),  # Sunday 05:00 UTC
    },
    # ── Data retention cleanup ────────────────────────────────────────────────
    "data-retention-cleanup": {
        "task": "data_retention_cleanup",
        "schedule": crontab(hour=4, minute=30),  # 04:30 UTC daily (after backups)
    },
    # ── Partition pre-creation ────────────────────────────────────────────────
    "ensure-partitions": {
        "task": "ensure_partitions_exist",
        "schedule": crontab(hour=0, minute=30, day_of_month=28),  # 28th of each month
    },
    # ── New external data connectors ──────────────────────────────────────────
    # Hourly
    "fetch-alpha-vantage-hourly": {
        "task": "tasks.fetch_alpha_vantage_data",
        "schedule": crontab(minute=15),  # :15 past each hour (offset from FRED)
    },
    # Every 6 hours
    "fetch-eu-ets-6h": {
        "task": "tasks.fetch_eu_ets_data",
        "schedule": crontab(minute=30, hour="*/6"),
    },
    "fetch-entsoe-6h": {
        "task": "tasks.fetch_entsoe_data",
        "schedule": crontab(minute=45, hour="*/6"),
    },
    # Every 12 hours
    "fetch-openweather-12h": {
        "task": "tasks.fetch_openweather_data",
        "schedule": crontab(minute=20, hour="1,13"),
    },
    # Daily
    "fetch-irena-daily": {
        "task": "tasks.fetch_irena_data",
        "schedule": crontab(minute=0, hour=5),
    },
    "fetch-companies-house-daily": {
        "task": "tasks.fetch_companies_house_data",
        "schedule": crontab(minute=15, hour=5),
    },
    "fetch-sp-global-daily": {
        "task": "tasks.fetch_sp_global_data",
        "schedule": crontab(minute=30, hour=5),
    },
    "fetch-bnef-daily": {
        "task": "tasks.fetch_bnef_data",
        "schedule": crontab(minute=45, hour=5),
    },
    "fetch-msci-esg-daily": {
        "task": "tasks.fetch_msci_esg_data",
        "schedule": crontab(minute=0, hour=7),
    },
    "fetch-preqin-daily": {
        "task": "tasks.fetch_preqin_data",
        "schedule": crontab(minute=15, hour=7),
    },
    # Weekly
    "fetch-eurostat-weekly": {
        "task": "tasks.fetch_eurostat_data",
        "schedule": crontab(minute=0, hour=4, day_of_week=1),
    },
    "fetch-iea-weekly": {
        "task": "tasks.fetch_iea_data",
        "schedule": crontab(minute=30, hour=4, day_of_week=1),
    },
    "fetch-eia-weekly": {
        "task": "tasks.fetch_eia_data",
        "schedule": crontab(minute=0, hour=4, day_of_week=3),
    },
    # Monthly
    "fetch-un-sdg-monthly": {
        "task": "tasks.fetch_un_sdg_data",
        "schedule": crontab(minute=0, hour=3, day_of_month=1),
    },
    # ── Market Enrichment scheduled fetches ───────────────────────────────────
    "market-enrichment-tier1-hourly": {
        "task": "market_enrichment.run_scheduled_fetches",
        "schedule": crontab(minute=0),  # :00 each hour
        "kwargs": {"tier": 1},
    },
    "market-enrichment-tier2-4hourly": {
        "task": "market_enrichment.run_scheduled_fetches",
        "schedule": crontab(hour="0,4,8,12,16,20", minute=30),
        "kwargs": {"tier": 2},
    },
}
