"""Integration tests for the Metrics module.

Covers:
- MetricSnapshotService direct service tests
- GET /v1/metrics/trend/{entity_type}/{entity_id}/{metric_name}
- GET /v1/metrics/rank/{entity_type}/{entity_id}/{metric_name}
- GET /v1/metrics/benchmark/list
- POST /v1/metrics/benchmark/compute
- SAVEPOINT pattern for best-effort snapshot inserts
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import User
from app.models.enums import UserRole
from app.models.metrics import BenchmarkAggregate, MetricSnapshot
from app.modules.metrics.snapshot_service import MetricSnapshotService
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio

# Unique UUIDs for this module
MM_ORG_ID = uuid.UUID("00000000-0000-0000-00bb-000000000001")


@pytest.fixture
async def metrics_client(db: AsyncSession, sample_user: User) -> AsyncClient:
    """Authenticated client with all DB overrides needed for metrics endpoints.

    The metrics router uses both get_db (for write endpoints) and get_readonly_db
    (for read endpoints). Both must be overridden to use the same test session.
    """
    from app.auth.dependencies import get_current_user, require_permission
    from app.core.database import get_db, get_readonly_db, get_readonly_session
    from app.main import app as _app

    cu = CurrentUser(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        org_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        role=UserRole.ADMIN,
        email="test@example.com",
        external_auth_id="user_test_clerk_123",
    )
    # Override require_permission to always pass (returns the same CurrentUser)
    _app.dependency_overrides[get_current_user] = lambda: cu
    _app.dependency_overrides[get_db] = lambda: db
    _app.dependency_overrides[get_readonly_db] = lambda: db
    _app.dependency_overrides[get_readonly_session] = lambda: db

    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as ac:
        yield ac

    _app.dependency_overrides.pop(get_current_user, None)
    _app.dependency_overrides.pop(get_db, None)
    _app.dependency_overrides.pop(get_readonly_db, None)
    _app.dependency_overrides.pop(get_readonly_session, None)


# Unique UUIDs for this module to avoid collisions with other test files
MM_ENTITY_ID = uuid.UUID("00000000-0000-0000-00bb-000000000010")
MM_ENTITY_ID_2 = uuid.UUID("00000000-0000-0000-00bb-000000000011")


def _make_snapshot(
    entity_id: uuid.UUID = MM_ENTITY_ID,
    entity_type: str = "project",
    metric_name: str = "signal_score",
    value: float = 75.0,
    previous_value: float | None = None,
    trigger_event: str | None = None,
    recorded_at: datetime | None = None,
) -> MetricSnapshot:
    """Build a MetricSnapshot ORM object for test insertion."""
    kwargs: dict = dict(
        id=uuid.uuid4(),
        org_id=MM_ORG_ID,
        entity_type=entity_type,
        entity_id=entity_id,
        metric_name=metric_name,
        value=value,
        previous_value=previous_value,
        metadata_={},
        trigger_event=trigger_event,
    )
    if recorded_at is not None:
        kwargs["recorded_at"] = recorded_at
    return MetricSnapshot(**kwargs)


# ── TestMetricSnapshotService ─────────────────────────────────────────────────


class TestMetricSnapshotService:
    """Direct service tests — no HTTP layer, exercises DB queries directly."""

    async def test_get_trend_returns_single_snapshot(self, db: AsyncSession, sample_user: User):
        """Insert one snapshot and verify get_trend() returns it."""
        snap = _make_snapshot(value=80.0)
        db.add(snap)
        await db.flush()

        svc = MetricSnapshotService(db)
        results = await svc.get_trend("project", MM_ENTITY_ID, "signal_score")

        assert len(results) == 1
        assert results[0].value == 80.0
        assert results[0].entity_type == "project"
        assert results[0].metric_name == "signal_score"

    async def test_get_trend_returns_oldest_first(self, db: AsyncSession, sample_user: User):
        """Multiple snapshots should be returned in ascending recorded_at order."""
        now = datetime.now(UTC)
        snaps = [
            _make_snapshot(value=70.0, recorded_at=now - timedelta(days=2)),
            _make_snapshot(value=75.0, recorded_at=now - timedelta(days=1)),
            _make_snapshot(value=80.0, recorded_at=now),
        ]
        for s in snaps:
            db.add(s)
        await db.flush()

        svc = MetricSnapshotService(db)
        results = await svc.get_trend("project", MM_ENTITY_ID, "signal_score")

        assert len(results) == 3
        assert results[0].value == 70.0
        assert results[1].value == 75.0
        assert results[2].value == 80.0

    async def test_get_trend_filters_by_from_date(self, db: AsyncSession, sample_user: User):
        """from_date filter should exclude older snapshots."""
        now = datetime.now(UTC)
        old = _make_snapshot(value=50.0, recorded_at=now - timedelta(days=30))
        recent = _make_snapshot(value=85.0, recorded_at=now - timedelta(days=1))
        db.add(old)
        db.add(recent)
        await db.flush()

        svc = MetricSnapshotService(db)
        results = await svc.get_trend(
            "project",
            MM_ENTITY_ID,
            "signal_score",
            from_date=now - timedelta(days=7),
        )

        assert len(results) == 1
        assert results[0].value == 85.0

    async def test_get_trend_filters_by_to_date(self, db: AsyncSession, sample_user: User):
        """to_date filter should exclude newer snapshots."""
        now = datetime.now(UTC)
        old = _make_snapshot(value=60.0, recorded_at=now - timedelta(days=10))
        newer = _make_snapshot(value=90.0, recorded_at=now)
        db.add(old)
        db.add(newer)
        await db.flush()

        svc = MetricSnapshotService(db)
        results = await svc.get_trend(
            "project",
            MM_ENTITY_ID,
            "signal_score",
            to_date=now - timedelta(days=5),
        )

        assert len(results) == 1
        assert results[0].value == 60.0

    async def test_get_trend_returns_empty_list_when_no_snapshots(
        self, db: AsyncSession, sample_user: User
    ):
        """No snapshots for entity → empty list."""
        svc = MetricSnapshotService(db)
        results = await svc.get_trend("project", MM_ENTITY_ID, "signal_score")
        assert results == []

    async def test_get_change_explanation_returns_dict_with_delta(
        self, db: AsyncSession, sample_user: User
    ):
        """get_change_explanation returns list of dicts, each with a 'delta' key."""
        now = datetime.now(UTC)
        snap1 = _make_snapshot(
            value=60.0,
            previous_value=None,
            recorded_at=now - timedelta(days=2),
        )
        snap2 = _make_snapshot(
            value=75.0,
            previous_value=60.0,
            trigger_event="document_uploaded",
            recorded_at=now - timedelta(days=1),
        )
        db.add(snap1)
        db.add(snap2)
        await db.flush()

        svc = MetricSnapshotService(db)
        changes = await svc.get_change_explanation("project", MM_ENTITY_ID, "signal_score")

        # Only snap2 has a previous_value and value != previous_value
        assert len(changes) == 1
        c = changes[0]
        assert "delta" in c
        assert c["delta"] == pytest.approx(15.0)
        assert c["from"] == pytest.approx(60.0)
        assert c["to"] == pytest.approx(75.0)
        assert c["trigger"] == "document_uploaded"

    async def test_get_change_explanation_excludes_no_change(
        self, db: AsyncSession, sample_user: User
    ):
        """Snapshots where value == previous_value are excluded from change list."""
        now = datetime.now(UTC)
        snap = _make_snapshot(
            value=70.0,
            previous_value=70.0,  # no change
            recorded_at=now,
        )
        db.add(snap)
        await db.flush()

        svc = MetricSnapshotService(db)
        changes = await svc.get_change_explanation("project", MM_ENTITY_ID, "signal_score")
        assert changes == []

    async def test_get_percentile_rank_returns_none_when_no_data(
        self, db: AsyncSession, sample_user: User
    ):
        """Entity with no snapshots → percentile rank is None."""
        svc = MetricSnapshotService(db)
        rank = await svc.get_percentile_rank("project", MM_ENTITY_ID, "signal_score")
        assert rank is None

    async def test_get_percentile_rank_with_single_entity_is_zero(
        self, db: AsyncSession, sample_user: User
    ):
        """Single entity has no peers below it → rank 0.0."""
        snap = _make_snapshot(value=80.0)
        db.add(snap)
        await db.flush()

        svc = MetricSnapshotService(db)
        rank = await svc.get_percentile_rank("project", MM_ENTITY_ID, "signal_score")
        # 0 entities below it out of 1 total → 0.0%
        assert rank == pytest.approx(0.0)

    async def test_record_snapshot_captures_previous_value(
        self, db: AsyncSession, sample_user: User
    ):
        """record_snapshot() auto-populates previous_value from last snapshot."""
        svc = MetricSnapshotService(db)
        snap1 = await svc.record_snapshot(
            org_id=MM_ORG_ID,
            entity_type="project",
            entity_id=MM_ENTITY_ID,
            metric_name="irr",
            value=10.0,
        )
        assert snap1.previous_value is None

        snap2 = await svc.record_snapshot(
            org_id=MM_ORG_ID,
            entity_type="project",
            entity_id=MM_ENTITY_ID,
            metric_name="irr",
            value=12.0,
        )
        assert snap2.previous_value == pytest.approx(10.0)


# ── TestMetricTrendEndpoint ───────────────────────────────────────────────────


class TestMetricTrendEndpoint:
    """HTTP tests for GET /v1/metrics/trend/{entity_type}/{entity_id}/{metric_name}."""

    async def test_returns_empty_list_when_no_snapshots(
        self, metrics_client: AsyncClient, sample_user: User
    ):
        """Empty list returned when no metric snapshots exist for the entity."""
        resp = await metrics_client.get(f"/v1/metrics/trend/project/{MM_ENTITY_ID}/signal_score")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_trend_points_with_required_fields(
        self, metrics_client: AsyncClient, db: AsyncSession, sample_user: User
    ):
        """Snapshot data is serialised as TrendPoint with date, value, delta fields."""
        now = datetime.now(UTC)
        snap = MetricSnapshot(
            id=uuid.uuid4(),
            org_id=MM_ORG_ID,
            entity_type="project",
            entity_id=MM_ENTITY_ID,
            metric_name="signal_score",
            value=72.5,
            previous_value=65.0,
            metadata_={},
            trigger_event="ai_analysis",
            recorded_at=now,
        )
        db.add(snap)
        await db.flush()

        resp = await metrics_client.get(f"/v1/metrics/trend/project/{MM_ENTITY_ID}/signal_score")
        assert resp.status_code == 200
        points = resp.json()
        assert len(points) == 1

        pt = points[0]
        assert "date" in pt
        assert "value" in pt
        assert "previous_value" in pt
        assert "delta" in pt
        assert "trigger_event" in pt

        assert pt["value"] == pytest.approx(72.5)
        assert pt["previous_value"] == pytest.approx(65.0)
        assert pt["delta"] == pytest.approx(7.5)
        assert pt["trigger_event"] == "ai_analysis"

    async def test_trend_endpoint_ordering_oldest_first(
        self, metrics_client: AsyncClient, db: AsyncSession, sample_user: User
    ):
        """Trend points are ordered oldest-first (ascending recorded_at)."""
        now = datetime.now(UTC)
        for val, days_ago in [(60.0, 3), (70.0, 2), (80.0, 1)]:
            db.add(
                MetricSnapshot(
                    id=uuid.uuid4(),
                    org_id=MM_ORG_ID,
                    entity_type="project",
                    entity_id=MM_ENTITY_ID_2,
                    metric_name="esg_score",
                    value=val,
                    previous_value=None,
                    metadata_={},
                    recorded_at=now - timedelta(days=days_ago),
                )
            )
        await db.flush()

        resp = await metrics_client.get(f"/v1/metrics/trend/project/{MM_ENTITY_ID_2}/esg_score")
        assert resp.status_code == 200
        points = resp.json()
        values = [p["value"] for p in points]
        assert values == [60.0, 70.0, 80.0]


# ── TestMetricRankEndpoint ────────────────────────────────────────────────────


class TestMetricRankEndpoint:
    """HTTP tests for GET /v1/metrics/rank/{entity_type}/{entity_id}/{metric_name}."""

    async def test_returns_null_percentile_when_no_data(
        self, metrics_client: AsyncClient, sample_user: User
    ):
        """No snapshots → percentile null with message."""
        resp = await metrics_client.get(f"/v1/metrics/rank/project/{MM_ENTITY_ID}/signal_score")
        assert resp.status_code == 200
        data = resp.json()
        assert data["percentile"] is None
        assert "message" in data
        assert "Insufficient" in data["message"]

    async def test_returns_percentile_when_data_exists(
        self, metrics_client: AsyncClient, db: AsyncSession, sample_user: User
    ):
        """With snapshots, returns structured rank response."""
        # Seed two entities; the first with lower score, second with higher
        low_entity = uuid.UUID("00000000-0000-0000-00bb-000000000020")
        high_entity = uuid.UUID("00000000-0000-0000-00bb-000000000021")

        db.add(
            MetricSnapshot(
                id=uuid.uuid4(),
                org_id=MM_ORG_ID,
                entity_type="project",
                entity_id=low_entity,
                metric_name="irr",
                value=5.0,
                previous_value=None,
                metadata_={},
            )
        )
        db.add(
            MetricSnapshot(
                id=uuid.uuid4(),
                org_id=MM_ORG_ID,
                entity_type="project",
                entity_id=high_entity,
                metric_name="irr",
                value=15.0,
                previous_value=None,
                metadata_={},
            )
        )
        await db.flush()

        # high_entity is above low_entity → percentile > 0
        resp = await metrics_client.get(f"/v1/metrics/rank/project/{high_entity}/irr")
        assert resp.status_code == 200
        data = resp.json()
        assert data["percentile"] is not None
        assert data["percentile"] > 0


# ── TestBenchmarkListEndpoint ─────────────────────────────────────────────────


class TestBenchmarkListEndpoint:
    """HTTP tests for GET /v1/metrics/benchmark/list."""

    async def test_returns_empty_list_when_no_benchmarks(
        self, metrics_client: AsyncClient, sample_user: User
    ):
        """No benchmarks seeded → empty list."""
        resp = await metrics_client.get("/v1/metrics/benchmark/list")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_benchmarks_after_insertion(
        self, metrics_client: AsyncClient, db: AsyncSession, sample_user: User
    ):
        """After inserting a BenchmarkAggregate, the list endpoint returns it."""
        bench = BenchmarkAggregate(
            id=uuid.uuid4(),
            asset_class="solar",
            geography="EU",
            stage="operational",
            vintage_year=2023,
            metric_name="irr",
            count=10,
            mean=12.5,
            median=12.0,
            p25=9.0,
            p75=16.0,
            p10=7.0,
            p90=18.0,
            std_dev=3.0,
            min_val=6.0,
            max_val=20.0,
            period="2024-Q4",
        )
        db.add(bench)
        await db.flush()

        resp = await metrics_client.get("/v1/metrics/benchmark/list")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

        solar_bench = next((b for b in data if b["asset_class"] == "solar"), None)
        assert solar_bench is not None
        assert solar_bench["metric_name"] == "irr"
        assert solar_bench["geography"] == "EU"
        assert solar_bench["count"] == 10

    async def test_benchmark_response_has_required_fields(
        self, metrics_client: AsyncClient, db: AsyncSession, sample_user: User
    ):
        """BenchmarkAggregateResponse schema fields are all present."""
        bench = BenchmarkAggregate(
            id=uuid.uuid4(),
            asset_class="wind",
            geography=None,
            stage=None,
            vintage_year=None,
            metric_name="signal_score",
            count=5,
            mean=70.0,
            median=72.0,
            p25=65.0,
            p75=78.0,
            p10=60.0,
            p90=82.0,
            std_dev=6.0,
            min_val=58.0,
            max_val=85.0,
            period="2024-Q3",
        )
        db.add(bench)
        await db.flush()

        resp = await metrics_client.get("/v1/metrics/benchmark/list")
        assert resp.status_code == 200
        data = resp.json()
        wind_bench = next((b for b in data if b["asset_class"] == "wind"), None)
        assert wind_bench is not None

        required_fields = [
            "id",
            "asset_class",
            "metric_name",
            "count",
            "mean",
            "median",
            "p25",
            "p75",
            "period",
            "computed_at",
        ]
        for field in required_fields:
            assert field in wind_bench, f"Missing field: {field}"


# ── TestBenchmarkComputeEndpoint ──────────────────────────────────────────────


class TestBenchmarkComputeEndpoint:
    """Tests for the benchmark compute functionality.

    Note: POST /v1/metrics/benchmark/compute uses require_permission("edit", "report")
    which is not present in the RBAC matrix for any role (ADMIN only has "create" and
    "export" on report). Therefore HTTP tests for the compute endpoint would return 403.
    Instead, we test the service layer directly.
    """

    async def test_compute_benchmarks_service_returns_dict_with_rows_written(
        self, db: AsyncSession, sample_user: User
    ):
        """BenchmarkService.compute_benchmarks() returns a dict with rows_written key."""
        from app.modules.metrics.benchmark_service import BenchmarkService

        svc = BenchmarkService(db)
        result = await svc.compute_benchmarks()
        assert "rows_written" in result
        assert isinstance(result["rows_written"], int)

    async def test_compute_benchmarks_service_returns_period(
        self, db: AsyncSession, sample_user: User
    ):
        """compute_benchmarks() result includes the period (YYYY-MM format)."""
        import re

        from app.modules.metrics.benchmark_service import BenchmarkService

        svc = BenchmarkService(db)
        result = await svc.compute_benchmarks()
        assert "period" in result
        # Period format should be YYYY-MM
        assert re.match(
            r"\d{4}-\d{2}", result["period"]
        ), f"Expected YYYY-MM format, got: {result['period']}"

    async def test_compute_endpoint_requires_permission(
        self, metrics_client: AsyncClient, sample_user: User
    ):
        """POST /v1/metrics/benchmark/compute returns 403 because 'edit/report' is not
        in the RBAC matrix. This documents the current permission gap."""
        resp = await metrics_client.post("/v1/metrics/benchmark/compute")
        # ADMIN role does not have ("edit", "report") in the RBAC matrix
        assert resp.status_code == 403


# ── TestBenchmarkSavepoint ────────────────────────────────────────────────────


class TestBenchmarkSavepoint:
    """Verify the SAVEPOINT pattern for best-effort snapshot inserts.

    Documents the requirement from MEMORY.md: use 'async with db.begin_nested()'
    (SAVEPOINT) for snapshot inserts inside existing transactions so that a
    failure in the snapshot insert does not abort the outer transaction.
    """

    async def test_savepoint_insert_visible_in_same_transaction(
        self, db: AsyncSession, sample_user: User
    ):
        """Snapshot inserted inside a SAVEPOINT is visible within the same session."""
        snap_id = uuid.uuid4()

        async with db.begin_nested():
            snap = MetricSnapshot(
                id=snap_id,
                org_id=MM_ORG_ID,
                entity_type="project",
                entity_id=MM_ENTITY_ID,
                metric_name="nav",
                value=1_000_000.0,
                previous_value=None,
                metadata_={},
            )
            db.add(snap)

        # After savepoint is released, the snapshot is visible within this transaction
        svc = MetricSnapshotService(db)
        results = await svc.get_trend("project", MM_ENTITY_ID, "nav")
        assert len(results) == 1
        assert results[0].id == snap_id

    async def test_savepoint_rollback_does_not_abort_outer_transaction(
        self, db: AsyncSession, sample_user: User
    ):
        """A failing SAVEPOINT rolls back only itself, leaving the outer transaction intact.

        This is critical: without SAVEPOINT, a failed INSERT (e.g., duplicate PK)
        would abort the entire PostgreSQL transaction, making subsequent queries fail.
        """
        # Insert a known snapshot first (this is the "outer transaction" operation)
        outer_snap = MetricSnapshot(
            id=uuid.uuid4(),
            org_id=MM_ORG_ID,
            entity_type="portfolio",
            entity_id=MM_ENTITY_ID,
            metric_name="moic",
            value=2.5,
            previous_value=None,
            metadata_={},
        )
        db.add(outer_snap)
        await db.flush()

        # Now attempt a SAVEPOINT that will fail (duplicate PK)
        duplicate_id = outer_snap.id
        try:
            async with db.begin_nested():
                bad_snap = MetricSnapshot(
                    id=duplicate_id,  # duplicate PK — will fail on flush
                    org_id=MM_ORG_ID,
                    entity_type="portfolio",
                    entity_id=MM_ENTITY_ID,
                    metric_name="moic",
                    value=9.9,
                    previous_value=None,
                    metadata_={},
                )
                db.add(bad_snap)
                await db.flush()
        except Exception:
            pass  # savepoint rolled back — outer transaction should still be usable

        # The outer transaction is still usable: we can query without error
        svc = MetricSnapshotService(db)
        results = await svc.get_trend("portfolio", MM_ENTITY_ID, "moic")
        # The original outer_snap should still be present
        assert any(r.id == outer_snap.id for r in results)
