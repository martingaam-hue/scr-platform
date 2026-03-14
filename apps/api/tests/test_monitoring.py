"""Unit tests for Celery monitoring tasks — no Redis or AWS required."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ── publish_queue_metrics ──────────────────────────────────────────────────────


class TestPublishQueueMetrics:
    """Tests for the queue-depth CloudWatch publisher."""

    def _run(self, redis_mock: MagicMock, cw_mock: MagicMock) -> dict:
        """Patch Redis and CloudWatch then call the task synchronously."""
        from app.tasks.monitoring import publish_queue_metrics

        with (
            patch("app.tasks.monitoring.redis.from_url", return_value=redis_mock),
            patch("app.tasks.monitoring._cw_client", return_value=cw_mock),
        ):
            return publish_queue_metrics()

    def _redis_mock(self, depths: dict[str, int]) -> MagicMock:
        r = MagicMock()
        r.llen.side_effect = lambda key: depths.get(key.removeprefix("celery:"), 0)
        return r

    # ── happy path ─────────────────────────────────────────────────────────────

    def test_publishes_all_four_queues(self):
        depths = {"critical": 3, "default": 12, "bulk": 0, "webhooks": 1}
        r = self._redis_mock(depths)
        cw = MagicMock()
        result = self._run(r, cw)

        assert result["status"] == "ok"
        assert result["published"] == 4

    def test_correct_namespace(self):
        cw = MagicMock()
        result = self._run(self._redis_mock({}), cw)

        if result["status"] == "ok":
            call_kwargs = cw.put_metric_data.call_args.kwargs
            assert call_kwargs["Namespace"] == "SCR/Celery"

    def test_metric_name_is_queue_depth(self):
        cw = MagicMock()
        self._run(self._redis_mock({"critical": 5}), cw)

        call_kwargs = cw.put_metric_data.call_args.kwargs
        names = {m["MetricName"] for m in call_kwargs["MetricData"]}
        assert "QueueDepth" in names

    def test_dimensions_include_queue_name(self):
        cw = MagicMock()
        self._run(self._redis_mock({"critical": 2}), cw)

        call_kwargs = cw.put_metric_data.call_args.kwargs
        dim_names = {d["Name"] for m in call_kwargs["MetricData"] for d in m["Dimensions"]}
        assert "QueueName" in dim_names

    def test_dimensions_include_environment(self):
        cw = MagicMock()
        self._run(self._redis_mock({}), cw)

        if cw.put_metric_data.called:
            call_kwargs = cw.put_metric_data.call_args.kwargs
            dim_names = {d["Name"] for m in call_kwargs["MetricData"] for d in m["Dimensions"]}
            assert "Environment" in dim_names

    def test_returns_depths_in_result(self):
        depths = {"critical": 7, "default": 0, "bulk": 3, "webhooks": 1}
        cw = MagicMock()
        result = self._run(self._redis_mock(depths), cw)

        assert result["depths"]["critical"] == 7
        assert result["depths"]["default"] == 0
        assert result["depths"]["bulk"] == 3
        assert result["depths"]["webhooks"] == 1

    def test_single_put_metric_data_call(self):
        """All four queues batched into one API call."""
        cw = MagicMock()
        self._run(self._redis_mock({"critical": 1, "default": 2, "bulk": 0, "webhooks": 0}), cw)
        assert cw.put_metric_data.call_count == 1

    def test_unit_is_count(self):
        cw = MagicMock()
        self._run(self._redis_mock({"critical": 5}), cw)

        call_kwargs = cw.put_metric_data.call_args.kwargs
        units = {m["Unit"] for m in call_kwargs["MetricData"]}
        assert units == {"Count"}

    # ── Redis key format ────────────────────────────────────────────────────────

    def test_queries_celery_prefixed_key(self):
        r = MagicMock()
        r.llen.return_value = 0
        cw = MagicMock()
        self._run(r, cw)

        queried_keys = [call.args[0] for call in r.llen.call_args_list]
        assert all(k.startswith("celery:") for k in queried_keys)

    @pytest.mark.parametrize("queue", ["critical", "default", "bulk", "webhooks"])
    def test_all_queue_keys_queried(self, queue: str):
        r = MagicMock()
        r.llen.return_value = 0
        cw = MagicMock()
        self._run(r, cw)

        queried_keys = [call.args[0] for call in r.llen.call_args_list]
        assert f"celery:{queue}" in queried_keys

    # ── Fault tolerance ────────────────────────────────────────────────────────

    def test_redis_connection_failure_returns_skipped(self):
        from app.tasks.monitoring import publish_queue_metrics

        with patch("app.tasks.monitoring.redis.from_url", side_effect=Exception("refused")):
            result = publish_queue_metrics()

        assert result["status"] == "skipped"
        assert "redis" in result["reason"].lower()

    def test_cloudwatch_failure_returns_error_with_depths(self):
        cw = MagicMock()
        cw.put_metric_data.side_effect = Exception("AccessDenied")
        result = self._run(self._redis_mock({"critical": 2}), cw)

        assert result["status"] == "error"
        assert "depths" in result  # depths still returned for diagnostics

    def test_single_llen_failure_does_not_abort_others(self):
        r = MagicMock()
        call_count = 0

        def _llen(key: str) -> int:
            nonlocal call_count
            call_count += 1
            if "critical" in key:
                raise Exception("timeout")
            return 0

        r.llen.side_effect = _llen
        cw = MagicMock()
        result = self._run(r, cw)

        # 3 successful queues still published; critical was skipped
        assert result["status"] == "ok"
        assert result["published"] == 3

    def test_redis_closed_after_success(self):
        r = self._redis_mock({"critical": 0})
        cw = MagicMock()
        self._run(r, cw)
        r.close.assert_called_once()


# ── Beat schedule registration ─────────────────────────────────────────────────


class TestBeatSchedule:
    def test_publish_queue_metrics_in_beat_schedule(self):
        from app.worker import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "publish-queue-metrics" in schedule

    def test_beat_schedule_task_name(self):
        from app.worker import celery_app

        entry = celery_app.conf.beat_schedule["publish-queue-metrics"]
        assert entry["task"] == "app.tasks.monitoring.publish_queue_metrics"

    def test_beat_schedule_interval_is_60s(self):
        from app.worker import celery_app

        entry = celery_app.conf.beat_schedule["publish-queue-metrics"]
        assert entry["schedule"] == 60.0


# ── Module-level constant invariants ──────────────────────────────────────────


class TestQueueConstants:
    def test_exactly_four_queues(self):
        from app.tasks.monitoring import _CELERY_QUEUES

        assert len(_CELERY_QUEUES) == 4

    def test_expected_queue_names(self):
        from app.tasks.monitoring import _CELERY_QUEUES

        assert set(_CELERY_QUEUES) == {"critical", "default", "bulk", "webhooks"}
