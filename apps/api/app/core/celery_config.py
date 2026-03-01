"""Celery queue topology: exchanges, queues, task routing, and per-task limits."""

from kombu import Exchange, Queue  # type: ignore[import-untyped]

# ── Exchanges ─────────────────────────────────────────────────────────────────

default_exchange = Exchange("default", type="direct")
priority_exchange = Exchange("priority", type="direct")

# ── Queues ────────────────────────────────────────────────────────────────────

CELERY_QUEUES = (
    # Critical — user-facing AI scoring; priority queue, limited concurrency
    Queue("critical", priority_exchange, routing_key="critical",
          queue_arguments={"x-max-priority": 10}),
    # Default — document processing, CRM sync, notifications
    Queue("default", default_exchange, routing_key="default"),
    # Bulk — nightly benchmarks, batch AI analysis, data refresh (low urgency)
    Queue("bulk", default_exchange, routing_key="bulk"),
    # Webhooks — isolated so delivery failures don't block other queues
    Queue("webhooks", default_exchange, routing_key="webhooks"),
    # Retention — data cleanup and archiving (lowest priority, never urgent)
    Queue("retention", default_exchange, routing_key="retention"),
)

# ── Task routing ──────────────────────────────────────────────────────────────

CELERY_TASK_ROUTES: dict[str, dict] = {
    # critical — compute-heavy, directly user-facing
    "calculate_signal_score_task":          {"queue": "critical"},
    "calculate_investor_signal_score":      {"queue": "critical"},
    "process_document":                     {"queue": "critical"},

    # webhooks — isolated queue
    "deliver_webhook":                      {"queue": "webhooks"},
    "tasks.retry_pending_webhooks":         {"queue": "webhooks"},

    # bulk — nightly / batch workloads
    "tasks.compute_nightly_benchmarks":     {"queue": "bulk"},
    "tasks.record_daily_snapshots":         {"queue": "bulk"},
    "app.worker_tasks.refresh_external_feed": {"queue": "bulk"},
    "tasks.fetch_daily_fx_rates":           {"queue": "bulk"},
    "tasks.fetch_market_data":              {"queue": "bulk"},
    "tasks.batch_blockchain_anchors":       {"queue": "bulk"},
    "tasks.backup_database":               {"queue": "bulk"},

    # retention — lowest priority
    "data_retention_cleanup":              {"queue": "retention"},
    "tasks.prune_old_backups":             {"queue": "retention"},

    # bulk — new external data connectors
    "tasks.fetch_irena_data":           {"queue": "bulk"},
    "tasks.fetch_eu_ets_data":          {"queue": "bulk"},
    "tasks.fetch_companies_house_data": {"queue": "bulk"},
    "tasks.fetch_alpha_vantage_data":   {"queue": "bulk"},
    "tasks.fetch_entsoe_data":          {"queue": "bulk"},
    "tasks.fetch_openweather_data":     {"queue": "bulk"},
    "tasks.fetch_eurostat_data":        {"queue": "bulk"},
    "tasks.fetch_iea_data":             {"queue": "bulk"},
    "tasks.fetch_sp_global_data":       {"queue": "bulk"},
    "tasks.fetch_bnef_data":            {"queue": "bulk"},
    "tasks.fetch_msci_esg_data":        {"queue": "bulk"},
    "tasks.fetch_un_sdg_data":          {"queue": "bulk"},
    "tasks.fetch_preqin_data":          {"queue": "bulk"},
    "tasks.fetch_eia_data":             {"queue": "bulk"},

    # default — everything else
    "app.worker_tasks.risk_monitoring_cycle":       {"queue": "default"},
    "app.worker_tasks.check_live_score_updates":    {"queue": "default"},
    "tasks.send_weekly_digests":                    {"queue": "default"},
    "tasks.check_upcoming_deadlines":               {"queue": "default"},
    "tasks.flag_overdue_deadlines":                 {"queue": "default"},
    "tasks.check_watchlists":                       {"queue": "default"},
    "tasks.check_qa_sla":                           {"queue": "default"},
    "tasks.check_all_covenants":                    {"queue": "default"},
    "tasks.sync_crm_connections":                   {"queue": "default"},
}

# ── Per-task rate limits and time limits ──────────────────────────────────────

CELERY_TASK_ANNOTATIONS: dict[str, dict] = {
    "calculate_signal_score_task": {
        "rate_limit": "20/m",
        "time_limit": 120,
        "soft_time_limit": 90,
    },
    "process_document": {
        "rate_limit": "30/m",
        "time_limit": 180,
        "soft_time_limit": 150,
    },
    "deliver_webhook": {
        "rate_limit": "100/m",
        "time_limit": 30,
        "soft_time_limit": 25,
    },
    "tasks.compute_nightly_benchmarks": {
        "time_limit": 600,
        "soft_time_limit": 540,
    },
    "data_retention_cleanup": {
        "time_limit": 900,
        "soft_time_limit": 840,
    },
    "tasks.backup_database": {
        "time_limit": 600,
        "soft_time_limit": 540,
    },
}
