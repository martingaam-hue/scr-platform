"""Tests for the custom_domain module: registration, DNS verification, status transitions."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_domain import CustomDomain
from app.modules.custom_domain.service import CNAME_TARGET, CustomDomainService
from tests.conftest import SAMPLE_ORG_ID

pytestmark = pytest.mark.asyncio

OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000055")


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_domain(
    db: AsyncSession,
    org_id: uuid.UUID,
    domain: str = "app.example.com",
    *,
    status: str = "pending",
    verification_token: str = "testtoken123",
) -> CustomDomain:
    record = CustomDomain(
        org_id=org_id,
        domain=domain,
        status=status,
        cname_target=CNAME_TARGET,
        verification_token=verification_token,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


# ── Service-level tests ───────────────────────────────────────────────────────


async def test_set_domain_creates_new_pending_record(db: AsyncSession, sample_org, sample_user):
    """set_domain creates a new CustomDomain with status=pending when none exists."""
    svc = CustomDomainService(db, SAMPLE_ORG_ID)

    record = await svc.set_domain("portal.mycompany.com")

    assert record.id is not None
    assert record.domain == "portal.mycompany.com"
    assert record.org_id == SAMPLE_ORG_ID
    assert record.status == "pending"
    assert record.cname_target == CNAME_TARGET
    assert record.verification_token is not None
    assert len(record.verification_token) > 10
    assert record.verified_at is None


async def test_set_domain_resets_existing_record(db: AsyncSession, sample_org, sample_user):
    """set_domain updates an existing domain record and resets verification status."""
    await _make_domain(db, SAMPLE_ORG_ID, "old.example.com", status="verified")

    svc = CustomDomainService(db, SAMPLE_ORG_ID)
    record = await svc.set_domain("new.example.com")

    assert record.domain == "new.example.com"
    assert record.status == "pending"
    assert record.verified_at is None
    assert record.ssl_provisioned_at is None
    assert record.error_message is None


async def test_get_domain_returns_none_when_not_configured(
    db: AsyncSession, sample_org, sample_user
):
    """get_domain returns None when no domain has been configured for the org."""
    svc = CustomDomainService(db, SAMPLE_ORG_ID)
    result = await svc.get_domain()
    assert result is None


async def test_get_domain_returns_record_for_correct_org(
    db: AsyncSession, sample_org, sample_user
):
    """get_domain returns the correct domain record for the org."""
    record = await _make_domain(db, SAMPLE_ORG_ID, "myapp.io")

    svc = CustomDomainService(db, SAMPLE_ORG_ID)
    result = await svc.get_domain()

    assert result is not None
    assert result.id == record.id
    assert result.domain == "myapp.io"


async def test_get_domain_is_org_scoped(db: AsyncSession, sample_org, sample_user):
    """get_domain does not return a record belonging to a different org."""
    await _make_domain(db, OTHER_ORG_ID, "other.example.com")

    svc = CustomDomainService(db, SAMPLE_ORG_ID)
    result = await svc.get_domain()

    assert result is None


async def test_verify_domain_marks_failed_when_dns_not_found(
    db: AsyncSession, sample_org, sample_user
):
    """verify_domain marks status=failed when CNAME and TXT records are missing."""
    await _make_domain(db, SAMPLE_ORG_ID, "unverified.example.com")
    svc = CustomDomainService(db, SAMPLE_ORG_ID)

    # Mock httpx to return empty DNS answers (no CNAME, no TXT)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"Answer": []}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        success, message = await svc.verify_domain()

    assert success is False
    record = await svc.get_domain()
    assert record is not None
    assert record.status == "failed"
    assert record.error_message is not None


async def test_verify_domain_marks_verified_when_cname_and_txt_match(
    db: AsyncSession, sample_org, sample_user
):
    """verify_domain marks status=verified when both CNAME and TXT records are correct."""
    token = "abc123verifytoken"
    await _make_domain(
        db, SAMPLE_ORG_ID, "verified.example.com", verification_token=token
    )
    svc = CustomDomainService(db, SAMPLE_ORG_ID)

    def make_dns_response(answers: list[dict]) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"Answer": answers}
        return resp

    cname_resp = make_dns_response(
        [{"type": 5, "data": CNAME_TARGET + "."}]  # CNAME answer
    )
    txt_resp = make_dns_response(
        [{"type": 16, "data": f'"{token}"'}]  # TXT answer contains token
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        # First call returns CNAME response, second returns TXT response
        mock_client.get = AsyncMock(side_effect=[cname_resp, txt_resp])
        mock_client_cls.return_value = mock_client

        success, message = await svc.verify_domain()

    assert success is True
    assert "verified" in message.lower()
    record = await svc.get_domain()
    assert record is not None
    assert record.status == "verified"
    assert record.verified_at is not None
    assert record.ssl_provisioned_at is not None


async def test_verify_domain_returns_error_when_no_domain_configured(
    db: AsyncSession, sample_org, sample_user
):
    """verify_domain returns (False, 'No domain configured') when no record exists."""
    svc = CustomDomainService(db, SAMPLE_ORG_ID)
    success, message = await svc.verify_domain()

    assert success is False
    assert "no domain" in message.lower()


async def test_delete_domain_removes_record(db: AsyncSession, sample_org, sample_user):
    """delete_domain removes the domain record and returns True."""
    await _make_domain(db, SAMPLE_ORG_ID, "todelete.example.com")
    svc = CustomDomainService(db, SAMPLE_ORG_ID)

    result = await svc.delete_domain()

    assert result is True
    assert await svc.get_domain() is None


async def test_delete_domain_returns_false_when_none_configured(
    db: AsyncSession, sample_org, sample_user
):
    """delete_domain returns False when no domain is configured."""
    svc = CustomDomainService(db, SAMPLE_ORG_ID)
    result = await svc.delete_domain()
    assert result is False


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_http_get_domain_returns_null_when_not_configured(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """GET /v1/custom-domain returns null body (200) when no domain is configured."""
    resp = await authenticated_client.get("/v1/custom-domain")
    assert resp.status_code == 200
    assert resp.json() is None


async def test_http_set_domain_creates_record(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """PUT /v1/custom-domain creates a domain record with status=pending."""
    resp = await authenticated_client.put(
        "/v1/custom-domain",
        json={"domain": "portal.testcompany.com"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "portal.testcompany.com"
    assert data["status"] == "pending"
    assert "verification_token" in data
    assert "dns_instructions" in data


async def test_http_set_domain_rejects_scr_io_subdomain(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """PUT /v1/custom-domain returns 422 for scr.io subdomains."""
    resp = await authenticated_client.put(
        "/v1/custom-domain",
        json={"domain": "myapp.scr.io"},
    )
    assert resp.status_code == 422


async def test_http_delete_domain_returns_204(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """DELETE /v1/custom-domain returns 204 after removing the domain."""
    await _make_domain(db, SAMPLE_ORG_ID, "deletehttp.example.com")

    resp = await authenticated_client.delete("/v1/custom-domain")
    assert resp.status_code == 204


async def test_http_delete_domain_returns_404_when_not_configured(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """DELETE /v1/custom-domain returns 404 when no domain is configured."""
    resp = await authenticated_client.delete("/v1/custom-domain")
    assert resp.status_code == 404


async def test_http_verify_domain_returns_failed_status(
    authenticated_client: AsyncClient, db: AsyncSession, sample_org, sample_user
):
    """POST /v1/custom-domain/verify returns 200 with success=false when DNS not configured."""
    await _make_domain(db, SAMPLE_ORG_ID, "verifyme.example.com")

    # Mock DNS calls to return empty answers
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"Answer": []}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        resp = await authenticated_client.post("/v1/custom-domain/verify")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["status"] == "failed"
