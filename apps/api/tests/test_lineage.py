"""Tests for the data lineage module — provenance tracking and derivation chains."""

import uuid
from datetime import UTC, datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lineage import DataLineage
from app.modules.lineage.service import LineageService
from tests.conftest import SAMPLE_ORG_ID

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _record(
    svc: LineageService,
    entity_type: str = "project",
    entity_id: uuid.UUID | None = None,
    field_name: str = "valuation",
    field_value: str = "5000000",
    source_type: str = "document_extraction",
    source_id: uuid.UUID | None = None,
    source_detail: str | None = "DCF model v2",
    computation_chain: list | None = None,
) -> DataLineage:
    return await svc.record_lineage(
        entity_type=entity_type,
        entity_id=entity_id or uuid.uuid4(),
        field_name=field_name,
        field_value=field_value,
        source_type=source_type,
        source_id=source_id,
        source_detail=source_detail,
        computation_chain=computation_chain,
    )


# ── Service-level unit tests ───────────────────────────────────────────────────


async def test_record_lineage_creates_row(db: AsyncSession, sample_org):
    """record_lineage persists a DataLineage record with the expected fields."""
    svc = LineageService(db, sample_org.id)
    entity_id = uuid.uuid4()

    row = await svc.record_lineage(
        entity_type="project",
        entity_id=entity_id,
        field_name="enterprise_value",
        field_value="12000000",
        source_type="document_extraction",
        source_detail="Financial model Q4 2024",
        computation_chain=[
            {"step": "extract_revenue", "source": "income_statement.pdf"},
            {"step": "apply_dcf", "discount_rate": 0.12},
        ],
    )

    assert row.id is not None
    assert row.entity_type == "project"
    assert row.entity_id == entity_id
    assert row.field_name == "enterprise_value"
    assert row.field_value == "12000000"
    assert row.source_detail == "Financial model Q4 2024"
    assert row.org_id == sample_org.id
    assert len(row.computation_chain) == 2


async def test_get_lineage_returns_all_records_for_entity(db: AsyncSession, sample_org):
    """get_lineage returns all lineage records for an entity, newest first."""
    svc = LineageService(db, sample_org.id)
    entity_id = uuid.uuid4()

    # Record three separate lineage entries for the same entity
    await svc.record_lineage("project", entity_id, "irr", "0.15", "computed")
    await svc.record_lineage("project", entity_id, "nav", "3000000", "api_connector")
    await svc.record_lineage("project", entity_id, "irr", "0.16", "computed")
    await db.flush()

    records = await svc.get_lineage("project", entity_id)

    assert len(records) == 3
    # All belong to the requested entity
    for r in records:
        assert r.entity_id == entity_id
        assert r.org_id == sample_org.id


async def test_get_lineage_filtered_by_field_name(db: AsyncSession, sample_org):
    """get_lineage with field_name returns only records for that specific field."""
    svc = LineageService(db, sample_org.id)
    entity_id = uuid.uuid4()

    await svc.record_lineage("project", entity_id, "irr", "0.15", "computed")
    await svc.record_lineage("project", entity_id, "nav", "3000000", "computed")
    await svc.record_lineage("project", entity_id, "irr", "0.16", "computed")
    await db.flush()

    irr_records = await svc.get_lineage("project", entity_id, field_name="irr")
    nav_records = await svc.get_lineage("project", entity_id, field_name="nav")

    assert len(irr_records) == 2
    assert all(r.field_name == "irr" for r in irr_records)
    assert len(nav_records) == 1
    assert nav_records[0].field_name == "nav"


async def test_org_isolation_lineage(db: AsyncSession, sample_org):
    """get_lineage does not return records belonging to a different org."""
    svc_mine = LineageService(db, sample_org.id)
    other_org_id = uuid.uuid4()
    svc_other = LineageService(db, other_org_id)
    entity_id = uuid.uuid4()

    await svc_mine.record_lineage("project", entity_id, "irr", "0.12", "computed")
    await svc_other.record_lineage("project", entity_id, "irr", "0.99", "computed")
    await db.flush()

    my_records = await svc_mine.get_lineage("project", entity_id, field_name="irr")
    assert len(my_records) == 1
    assert my_records[0].field_value == "0.12"
    assert my_records[0].org_id == sample_org.id


async def test_get_full_trace_returns_latest_record(db: AsyncSession, sample_org):
    """get_full_trace returns the most recent lineage entry for a field."""
    svc = LineageService(db, sample_org.id)
    entity_id = uuid.uuid4()

    rec1 = await svc.record_lineage("project", entity_id, "moic", "1.8", "computed")
    # Explicitly push the first record into the past so ordering is deterministic
    rec1.recorded_at = datetime(2024, 1, 1, tzinfo=UTC)
    await db.flush()
    await svc.record_lineage("project", entity_id, "moic", "2.1", "computed", source_detail="v2")
    await db.flush()

    trace = await svc.get_full_trace("project", entity_id, "moic")

    assert trace is not None
    assert trace["value"] == "2.1"
    assert trace["source_detail"] == "v2"
    assert "last_updated" in trace
    assert "chain" in trace


async def test_get_full_trace_returns_none_when_no_lineage(db: AsyncSession, sample_org):
    """get_full_trace returns None when no lineage record exists for the field."""
    svc = LineageService(db, sample_org.id)

    trace = await svc.get_full_trace("project", uuid.uuid4(), "nonexistent_field")

    assert trace is None


async def test_field_value_truncated_at_500_chars(db: AsyncSession, sample_org):
    """record_lineage truncates field_value to 500 characters maximum."""
    svc = LineageService(db, sample_org.id)
    long_value = "x" * 1000  # 1000-char string

    row = await svc.record_lineage("project", uuid.uuid4(), "notes", long_value, "manual_entry")

    assert row.field_value is not None
    assert len(row.field_value) == 500


async def test_computation_chain_stored_and_retrieved(db: AsyncSession, sample_org):
    """Computation chain JSONB roundtrips correctly through the database."""
    svc = LineageService(db, sample_org.id)
    entity_id = uuid.uuid4()
    chain = [
        {"step": 1, "operation": "normalise_revenue", "model": "dcf_v3"},
        {"step": 2, "operation": "apply_growth_rate", "rate": 0.08},
        {"step": 3, "operation": "discount_cashflows", "wacc": 0.12},
    ]

    await svc.record_lineage(
        "project", entity_id, "enterprise_value", "8500000",
        "computed", computation_chain=chain,
    )
    await db.flush()

    records = await svc.get_lineage("project", entity_id, field_name="enterprise_value")
    assert records[0].computation_chain == chain


# ── HTTP endpoint tests ────────────────────────────────────────────────────────


async def test_api_get_entity_lineage_empty(authenticated_client):
    """GET /v1/lineage/{type}/{id} returns empty list for entity with no records."""
    resp = await authenticated_client.get(f"/v1/lineage/project/{uuid.uuid4()}")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_api_get_entity_lineage_returns_records(
    authenticated_client, db: AsyncSession, sample_org
):
    """GET /v1/lineage/{type}/{id} returns lineage records for the entity."""
    svc = LineageService(db, sample_org.id)
    entity_id = uuid.uuid4()
    await svc.record_lineage("project", entity_id, "irr", "0.18", "computed")
    await db.flush()

    resp = await authenticated_client.get(f"/v1/lineage/project/{entity_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["field_name"] == "irr"
    assert data[0]["field_value"] == "0.18"
    assert data[0]["entity_type"] == "project"


async def test_api_get_field_lineage(authenticated_client, db: AsyncSession, sample_org):
    """GET /v1/lineage/{type}/{id}/{field} returns only records for that field."""
    svc = LineageService(db, sample_org.id)
    entity_id = uuid.uuid4()
    await svc.record_lineage("project", entity_id, "irr", "0.14", "computed")
    await svc.record_lineage("project", entity_id, "nav", "2000000", "api_connector")
    await db.flush()

    resp = await authenticated_client.get(f"/v1/lineage/project/{entity_id}/irr")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["field_name"] == "irr"


async def test_api_get_full_trace_404_when_missing(authenticated_client):
    """GET /v1/lineage/trace/{type}/{id}/{field} returns 404 when no lineage exists."""
    resp = await authenticated_client.get(
        f"/v1/lineage/trace/project/{uuid.uuid4()}/phantom_field"
    )
    assert resp.status_code == 404


async def test_api_get_full_trace_returns_provenance(
    authenticated_client, db: AsyncSession, sample_org
):
    """GET /v1/lineage/trace/... returns the full trace with chain and source details."""
    svc = LineageService(db, sample_org.id)
    entity_id = uuid.uuid4()
    await svc.record_lineage(
        "portfolio", entity_id, "total_irr", "0.22",
        "computed",
        source_detail="IRR model v4",
        computation_chain=[{"step": "aggregate_cashflows"}, {"step": "xirr"}],
    )
    await db.flush()

    resp = await authenticated_client.get(f"/v1/lineage/trace/portfolio/{entity_id}/total_irr")

    assert resp.status_code == 200
    body = resp.json()
    assert body["value"] == "0.22"
    assert body["source_detail"] == "IRR model v4"
    assert len(body["chain"]) == 2
    assert "last_updated" in body
