"""Tests for Celery task infrastructure — queue config, task routing, AI costs."""
import pytest


# ── Queue topology ──────────────────────────────────────────────────────────


def test_queue_topology_defined() -> None:
    from app.core.celery_config import CELERY_QUEUES, CELERY_TASK_ROUTES

    assert len(CELERY_QUEUES) >= 4, "Expected at least 4 queues"
    assert len(CELERY_TASK_ROUTES) >= 10, "Expected at least 10 task routes"


def test_task_annotations_have_timeouts() -> None:
    from app.core.celery_config import CELERY_TASK_ANNOTATIONS

    for task, annotations in CELERY_TASK_ANNOTATIONS.items():
        assert "time_limit" in annotations, f"Task {task} missing time_limit"


def test_all_queues_have_names() -> None:
    from app.core.celery_config import CELERY_QUEUES

    queue_names = {q.name for q in CELERY_QUEUES}
    for required in ("critical", "default", "bulk", "webhooks"):
        assert required in queue_names, f"Queue '{required}' not found"


# ── Shared DB session ───────────────────────────────────────────────────────


def test_shared_session_factory_importable() -> None:
    from app.core.celery_db import get_celery_db_session

    assert callable(get_celery_db_session)


# ── AI cost utilities ───────────────────────────────────────────────────────


def test_calculate_cost_known_model() -> None:
    from app.core.ai_costs import calculate_cost
    from decimal import Decimal

    cost = calculate_cost("claude-sonnet-4-6", 1000, 500)
    assert cost > Decimal("0")
    assert cost < Decimal("1"), "Single call should cost less than $1"


def test_calculate_cost_unknown_model_uses_default() -> None:
    from app.core.ai_costs import calculate_cost
    from decimal import Decimal

    cost = calculate_cost("unknown-model-xyz-9999", 1000, 500)
    assert cost > Decimal("0"), "Unknown model should use DEFAULT_COST, not crash"


def test_calculate_cost_zero_tokens() -> None:
    from app.core.ai_costs import calculate_cost
    from decimal import Decimal

    cost = calculate_cost("claude-sonnet-4-6", 0, 0)
    assert cost == Decimal("0")


def test_calculate_cost_none_model() -> None:
    from app.core.ai_costs import calculate_cost
    from decimal import Decimal

    cost = calculate_cost(None, 1000, 500)
    assert cost == Decimal("0")


# ── Data retention ──────────────────────────────────────────────────────────


def test_retention_policies_importable() -> None:
    """Data retention module should define RETENTION_POLICIES or _POLICIES."""
    import app.tasks.data_retention as dr

    # Accept either name
    policies = getattr(dr, "RETENTION_POLICIES", None) or getattr(dr, "_POLICIES", None)
    assert policies is not None, "data_retention must define retention policies"
