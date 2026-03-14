"""Tests for the Connectors module — catalog, org config, enable/disable, and usage."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db, get_readonly_db, get_readonly_session
from app.main import app
from app.models.connectors import DataConnector, OrgConnectorConfig
from app.models.enums import OrgType, UserRole
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio


# ── RBAC bypass ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def bypass_rbac():
    """Bypass RBAC permission checks in all connectors tests."""
    with patch("app.auth.dependencies.check_permission", return_value=True):
        yield


# ── Unique IDs ────────────────────────────────────────────────────────────────

CN_ORG_ID = uuid.UUID("00000000-0000-00C4-0000-000000000001")
CN_USER_ID = uuid.UUID("00000000-0000-00C4-0000-000000000002")

# Second org for isolation tests
CN_ORG2_ID = uuid.UUID("00000000-0000-00C4-0000-000000000010")

CURRENT_USER = CurrentUser(
    user_id=CN_USER_ID,
    org_id=CN_ORG_ID,
    role=UserRole.ADMIN,
    email="connector_test@example.com",
    external_auth_id="clerk_connector_test",
)

CURRENT_USER2 = CurrentUser(
    user_id=uuid.UUID("00000000-0000-00C4-0000-000000000011"),
    org_id=CN_ORG2_ID,
    role=UserRole.ADMIN,
    email="connector_test2@example.com",
    external_auth_id="clerk_connector_test2",
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def cn_org(db: AsyncSession):
    from app.models.core import Organization

    org = Organization(
        id=CN_ORG_ID,
        name="Connector Test Org",
        slug="connector-test-org",
        type=OrgType.INVESTOR,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def cn_org2(db: AsyncSession):
    from app.models.core import Organization

    org = Organization(
        id=CN_ORG2_ID,
        name="Connector Test Org 2",
        slug="connector-test-org-2",
        type=OrgType.INVESTOR,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def cn_user(db: AsyncSession, cn_org):
    from app.models.core import User

    user = User(
        id=CN_USER_ID,
        org_id=CN_ORG_ID,
        email="connector_test@example.com",
        full_name="Connector Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_connector_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def sample_connector(db: AsyncSession):
    """Insert a single DataConnector catalog entry."""
    connector = DataConnector(
        name="test_weather_api",
        display_name="Test Weather API",
        category="weather",
        description="A weather connector for tests.",
        base_url="https://api.test-weather.example.com",
        auth_type="api_key",
        is_available=True,
        pricing_tier="free",
        rate_limit_per_minute=60,
    )
    db.add(connector)
    await db.flush()
    return connector


@pytest.fixture
async def enabled_connector_config(db: AsyncSession, cn_org, sample_connector):
    """OrgConnectorConfig that marks the test connector as enabled for cn_org."""
    with patch("app.services.encryption.encrypt_field", return_value="encrypted_key_abc"):
        cfg = OrgConnectorConfig(
            org_id=CN_ORG_ID,
            connector_id=sample_connector.id,
            is_enabled=True,
            api_key_encrypted="encrypted_key_abc",
            config={},
        )
        db.add(cfg)
        await db.flush()
    return cfg


def _override(db: AsyncSession, current_user: CurrentUser = CURRENT_USER):
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db


def _clear():
    app.dependency_overrides.clear()


# ── Service-level tests ───────────────────────────────────────────────────────


async def test_list_connectors_returns_available(db: AsyncSession, cn_org, sample_connector):
    """list_connectors returns only available, non-deleted connectors."""
    from app.modules.connectors.service import list_connectors

    connectors = await list_connectors(db)

    names = [c.name for c in connectors]
    assert "test_weather_api" in names


async def test_list_connectors_excludes_unavailable(db: AsyncSession, cn_org):
    """list_connectors excludes connectors marked is_available=False."""
    from app.modules.connectors.service import list_connectors

    unavailable = DataConnector(
        name="unavailable_connector",
        display_name="Unavailable",
        category="energy",
        auth_type="api_key",
        is_available=False,
        pricing_tier="free",
        rate_limit_per_minute=30,
    )
    db.add(unavailable)
    await db.flush()

    connectors = await list_connectors(db)

    names = [c.name for c in connectors]
    assert "unavailable_connector" not in names


async def test_enable_connector_creates_config(db: AsyncSession, cn_org, sample_connector):
    """enable_connector creates an OrgConnectorConfig row for the org."""
    from app.modules.connectors.service import enable_connector, get_org_config

    with patch("app.services.encryption.encrypt_field", return_value="enc_key"):
        cfg = await enable_connector(
            db,
            org_id=CN_ORG_ID,
            connector_id=sample_connector.id,
            api_key="my-secret-api-key",
            config={"region": "eu-west-1"},
        )

    assert cfg.org_id == CN_ORG_ID
    assert cfg.connector_id == sample_connector.id
    assert cfg.is_enabled is True


async def test_enable_connector_updates_existing_config(
    db: AsyncSession, cn_org, sample_connector, enabled_connector_config
):
    """enable_connector updates an existing config rather than creating a duplicate."""
    from app.modules.connectors.service import enable_connector, list_org_configs

    with patch("app.services.encryption.encrypt_field", return_value="new_enc_key"):
        updated = await enable_connector(
            db,
            org_id=CN_ORG_ID,
            connector_id=sample_connector.id,
            api_key="updated-key",
            config={"region": "us-east-1"},
        )

    assert updated.id == enabled_connector_config.id  # same row, not a new one
    assert updated.is_enabled is True

    configs = await list_org_configs(db, CN_ORG_ID)
    # Only one config for this org/connector combination
    matching = [c for c in configs if c.connector_id == sample_connector.id]
    assert len(matching) == 1


async def test_disable_connector(
    db: AsyncSession, cn_org, sample_connector, enabled_connector_config
):
    """disable_connector sets is_enabled=False on the org config."""
    from app.modules.connectors.service import disable_connector, get_org_config

    await disable_connector(db, CN_ORG_ID, sample_connector.id)

    cfg = await get_org_config(db, CN_ORG_ID, sample_connector.id)
    assert cfg is not None
    assert cfg.is_enabled is False


async def test_get_org_config_returns_none_for_other_org(
    db: AsyncSession, cn_org, cn_org2, sample_connector, enabled_connector_config
):
    """get_org_config is scoped to org_id — another org cannot see this config."""
    from app.modules.connectors.service import get_org_config

    cfg = await get_org_config(db, CN_ORG2_ID, sample_connector.id)

    assert cfg is None


async def test_list_org_configs_org_scoped(
    db: AsyncSession, cn_org, cn_org2, sample_connector, enabled_connector_config
):
    """list_org_configs returns only configs belonging to the specified org."""
    from app.modules.connectors.service import list_org_configs

    org1_configs = await list_org_configs(db, CN_ORG_ID)
    org2_configs = await list_org_configs(db, CN_ORG2_ID)

    assert len(org1_configs) >= 1
    assert all(c.org_id == CN_ORG_ID for c in org1_configs)
    assert len(org2_configs) == 0


async def test_test_connector_logs_success(
    db: AsyncSession, cn_org, sample_connector, enabled_connector_config
):
    """test_connector logs a DataFetchLog with status 200 on success."""
    from sqlalchemy import select

    from app.models.connectors import DataFetchLog
    from app.modules.connectors.service import test_connector

    mock_instance = AsyncMock()
    mock_instance.test = AsyncMock(return_value={"status": "ok"})

    with (
        patch("app.services.encryption.decrypt_field", return_value="decrypted_key"),
        patch(
            "app.modules.connectors.service._get_connector_instance",
            return_value=mock_instance,
        ),
    ):
        result = await test_connector(db, CN_ORG_ID, sample_connector.id)

    assert result == {"status": "ok"}

    # Verify the DataFetchLog was created
    logs = await db.execute(
        select(DataFetchLog).where(
            DataFetchLog.org_id == CN_ORG_ID,
            DataFetchLog.connector_id == sample_connector.id,
        )
    )
    rows = logs.scalars().all()
    assert len(rows) >= 1
    assert rows[-1].status_code == 200


async def test_test_connector_logs_failure_and_reraises(
    db: AsyncSession, cn_org, sample_connector, enabled_connector_config
):
    """test_connector logs a 500 DataFetchLog and re-raises on connector error."""
    from sqlalchemy import select

    from app.models.connectors import DataFetchLog
    from app.modules.connectors.service import test_connector

    mock_instance = AsyncMock()
    mock_instance.test = AsyncMock(side_effect=RuntimeError("API key invalid"))

    with (
        patch("app.services.encryption.decrypt_field", return_value="bad_key"),
        patch(
            "app.modules.connectors.service._get_connector_instance",
            return_value=mock_instance,
        ),
        pytest.raises(RuntimeError, match="API key invalid"),
    ):
        await test_connector(db, CN_ORG_ID, sample_connector.id)

    logs = await db.execute(
        select(DataFetchLog).where(
            DataFetchLog.org_id == CN_ORG_ID,
            DataFetchLog.connector_id == sample_connector.id,
        )
    )
    rows = logs.scalars().all()
    assert any(r.status_code == 500 for r in rows)


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


async def test_api_list_connectors(db: AsyncSession, cn_org, cn_user, sample_connector):
    """GET /v1/connectors/ returns the connector catalog with org-level status."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/connectors/")

    _clear()

    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    names = [c["name"] for c in items]
    assert "test_weather_api" in names


async def test_api_enable_connector(db: AsyncSession, cn_org, cn_user, sample_connector):
    """POST /v1/connectors/{id}/enable returns status=enabled."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    with patch("app.services.encryption.encrypt_field", return_value="enc"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/v1/connectors/{sample_connector.id}/enable",
                json={"api_key": "my-api-key"},
            )

    _clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "enabled"


async def test_api_disable_connector(
    db: AsyncSession, cn_org, cn_user, sample_connector, enabled_connector_config
):
    """POST /v1/connectors/{id}/disable returns status=disabled."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/v1/connectors/{sample_connector.id}/disable")

    _clear()

    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"


async def test_api_test_connector_not_found(db: AsyncSession, cn_org, cn_user):
    """POST /v1/connectors/{id}/test returns 404 for unknown connector ID."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    unknown_id = uuid.uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/v1/connectors/{unknown_id}/test")

    _clear()

    assert resp.status_code == 404


async def test_api_usage_stats(db: AsyncSession, cn_org, cn_user):
    """GET /v1/connectors/usage returns an empty list when no calls have been made."""
    _override(db)

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/connectors/usage")

    _clear()

    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
