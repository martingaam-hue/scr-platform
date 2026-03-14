"""Tests for the redaction module: job lifecycle, PII detection, org scoping, HTTP endpoints."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.redaction import RedactionJob
from app.modules.redaction.schemas import ENTITY_TYPES, HIGH_SENSITIVITY
from app.modules.redaction.service import RedactionService
from tests.conftest import SAMPLE_ORG_ID, SAMPLE_USER_ID

pytestmark = pytest.mark.asyncio

OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000066")


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_job(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    status: str = "pending",
    document_id: uuid.UUID | None = None,
    detected_entities: list[dict] | None = None,
) -> RedactionJob:
    doc_id = document_id or uuid.uuid4()
    job = RedactionJob(
        org_id=org_id,
        created_by=SAMPLE_USER_ID,
        document_id=doc_id,
        status=status,
        detected_entities=detected_entities,
        entity_count=len(detected_entities) if detected_entities else 0,
        approved_count=0,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


# ── Entity type catalog tests ─────────────────────────────────────────────────


def test_entity_types_catalog_contains_expected_pii_categories():
    """ENTITY_TYPES includes core PII categories used by the AI detection prompt."""
    assert "person_name" in ENTITY_TYPES
    assert "email" in ENTITY_TYPES
    assert "phone_number" in ENTITY_TYPES
    assert "tax_id" in ENTITY_TYPES
    assert "bank_account" in ENTITY_TYPES
    assert "iban" in ENTITY_TYPES
    assert "passport_number" in ENTITY_TYPES
    assert "date_of_birth" in ENTITY_TYPES
    assert len(ENTITY_TYPES) >= 10


def test_high_sensitivity_is_subset_of_entity_types():
    """HIGH_SENSITIVITY must only reference types defined in ENTITY_TYPES."""
    for hs in HIGH_SENSITIVITY:
        assert hs in ENTITY_TYPES, f"{hs} is in HIGH_SENSITIVITY but not in ENTITY_TYPES"


def test_high_sensitivity_contains_financial_identifiers():
    """Financial identifiers are flagged as high sensitivity."""
    assert "tax_id" in HIGH_SENSITIVITY
    assert "bank_account" in HIGH_SENSITIVITY
    assert "iban" in HIGH_SENSITIVITY
    assert "credit_card" in HIGH_SENSITIVITY
    assert "passport_number" in HIGH_SENSITIVITY


# ── Service-level tests ───────────────────────────────────────────────────────


async def test_create_job_initialises_with_pending_status(
    db: AsyncSession, sample_org, sample_user
):
    """create_job creates a RedactionJob with status=pending."""
    svc = RedactionService(db)
    doc_id = uuid.uuid4()

    job = await svc.create_job(SAMPLE_ORG_ID, SAMPLE_USER_ID, doc_id)

    assert job.id is not None
    assert job.org_id == SAMPLE_ORG_ID
    assert job.document_id == doc_id
    assert job.created_by == SAMPLE_USER_ID
    assert job.status == "pending"
    assert job.entity_count == 0
    assert job.approved_count == 0
    assert job.detected_entities is None


async def test_analyze_document_transitions_to_review_on_success(
    db: AsyncSession, sample_org, sample_user
):
    """analyze_document transitions job to 'review' when AI gateway returns entities."""
    job = await _make_job(db, SAMPLE_ORG_ID)
    svc = RedactionService(db)

    entities = [
        {
            "entity_type": "email",
            "text": "alice@corp.com",
            "page": 1,
            "confidence": 0.97,
            "position": {"x": 10, "y": 20, "width": 15, "height": 2},
        },
        {
            "entity_type": "tax_id",
            "text": "DE123456789",
            "page": 1,
            "confidence": 0.92,
            "position": {"x": 5, "y": 50, "width": 10, "height": 2},
        },
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"content": json.dumps(entities)}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http

        result = await svc.analyze_document(job.id, "Test document with PII: alice@corp.com")

    assert result is not None
    assert result.status == "review"
    assert result.entity_count == 2
    assert result.detected_entities is not None
    # IDs should have been assigned by the service
    assert result.detected_entities[0]["id"] == 0
    assert result.detected_entities[1]["id"] == 1
    # High-sensitivity flag should be set for tax_id
    tax_entity = next(e for e in result.detected_entities if e["entity_type"] == "tax_id")
    assert tax_entity["is_high_sensitivity"] is True


async def test_analyze_document_transitions_to_failed_on_gateway_error(
    db: AsyncSession, sample_org, sample_user
):
    """analyze_document transitions job to 'failed' when AI gateway raises an exception."""
    job = await _make_job(db, SAMPLE_ORG_ID)
    svc = RedactionService(db)

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=None)
        mock_http.post = AsyncMock(side_effect=Exception("Connection refused"))
        mock_cls.return_value = mock_http

        result = await svc.analyze_document(job.id, "document text")

    assert result is not None
    assert result.status == "failed"
    assert result.error_message is not None
    assert "Connection refused" in result.error_message


async def test_approve_redactions_transitions_to_applying(
    db: AsyncSession, sample_org, sample_user
):
    """approve_redactions selects entities by id and transitions job to 'applying'."""
    entities = [
        {"id": 0, "entity_type": "email", "text": "test@corp.com", "page": 1,
         "confidence": 0.9, "position": {}, "is_high_sensitivity": False},
        {"id": 1, "entity_type": "tax_id", "text": "DE99988", "page": 2,
         "confidence": 0.95, "position": {}, "is_high_sensitivity": True},
        {"id": 2, "entity_type": "person_name", "text": "John Doe", "page": 1,
         "confidence": 0.88, "position": {}, "is_high_sensitivity": False},
    ]
    job = await _make_job(db, SAMPLE_ORG_ID, status="review", detected_entities=entities)
    svc = RedactionService(db)

    # Approve only entities 0 and 1
    result = await svc.approve_redactions(SAMPLE_ORG_ID, job.id, approved_ids=[0, 1])

    assert result is not None
    assert result.status == "applying"
    assert result.approved_count == 2
    assert result.approved_redactions is not None
    approved_ids = [e["id"] for e in result.approved_redactions]
    assert 0 in approved_ids
    assert 1 in approved_ids
    assert 2 not in approved_ids


async def test_approve_redactions_returns_none_for_wrong_org(
    db: AsyncSession, sample_org, sample_user
):
    """approve_redactions returns None when called with a different org_id."""
    entities = [{"id": 0, "entity_type": "email", "text": "x@y.com", "page": 1,
                 "confidence": 0.9, "position": {}, "is_high_sensitivity": False}]
    job = await _make_job(db, SAMPLE_ORG_ID, status="review", detected_entities=entities)
    svc = RedactionService(db)

    result = await svc.approve_redactions(OTHER_ORG_ID, job.id, approved_ids=[0])
    assert result is None


async def test_generate_redacted_document_transitions_to_done(
    db: AsyncSession, sample_org, sample_user
):
    """generate_redacted_document sets status=done and stores an S3 key."""
    job = await _make_job(db, SAMPLE_ORG_ID, status="applying")
    svc = RedactionService(db)

    result = await svc.generate_redacted_document(job.id)

    assert result is not None
    assert result.status == "done"
    assert result.redacted_s3_key is not None
    assert "redacted" in result.redacted_s3_key


async def test_list_jobs_returns_only_org_jobs(db: AsyncSession, sample_org, sample_user):
    """list_jobs returns only jobs belonging to the calling org."""
    own_job = await _make_job(db, SAMPLE_ORG_ID)
    other_job = await _make_job(db, OTHER_ORG_ID)

    svc = RedactionService(db)
    jobs = await svc.list_jobs(SAMPLE_ORG_ID)

    ids = [j.id for j in jobs]
    assert own_job.id in ids
    assert other_job.id not in ids


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_http_get_redaction_rules_returns_entity_types(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/redaction/rules returns entity types and high-sensitivity list."""
    resp = await authenticated_client.get("/v1/redaction/rules")

    assert resp.status_code == 200
    data = resp.json()
    assert "entity_types" in data
    assert "high_sensitivity_types" in data
    type_names = [e["entity_type"] for e in data["entity_types"]]
    assert "email" in type_names
    assert "tax_id" in type_names
    assert "tax_id" in data["high_sensitivity_types"]


async def test_http_list_jobs_returns_200(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/redaction/jobs returns 200 with a list."""
    await _make_job(db, SAMPLE_ORG_ID)

    resp = await authenticated_client.get("/v1/redaction/jobs")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


async def test_http_analyze_document_returns_202(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """POST /v1/redaction/analyze/{doc_id} returns 202 with job_id."""
    doc_id = uuid.uuid4()

    # Patch out the Celery task and the synchronous fallback
    with patch("app.modules.redaction.tasks.analyze_redaction_job_task") as mock_task:
        mock_task.delay = MagicMock(side_effect=Exception("no celery"))
        mock_task.return_value = None  # sync call fallback

        resp = await authenticated_client.post(
            f"/v1/redaction/analyze/{doc_id}",
            json={"document_text": "Short test document."},
        )

    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "pending"


async def test_http_get_job_returns_404_for_unknown(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/redaction/jobs/{unknown_id} returns 404."""
    resp = await authenticated_client.get(f"/v1/redaction/jobs/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_http_approve_redactions_returns_404_when_not_in_review(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """POST /v1/redaction/jobs/{id}/approve returns 404 when job is not in review status."""
    # Job is in 'pending', not 'review'
    job = await _make_job(db, SAMPLE_ORG_ID, status="pending")

    resp = await authenticated_client.post(
        f"/v1/redaction/jobs/{job.id}/approve",
        json={"approved_entity_ids": [0]},
    )

    assert resp.status_code == 404
