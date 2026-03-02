"""Celery tasks for the Risk module.

Currently a placeholder — background risk monitoring is driven by
`app.worker_tasks.risk_monitoring_cycle` which calls the risk service directly.
This module is imported by the Celery worker at startup so that any future
risk-specific tasks can be registered here.
"""
