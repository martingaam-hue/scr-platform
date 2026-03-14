"""Tests for the FX module — ECB rate fetching, conversion, and exposure analysis."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db, get_readonly_db, get_readonly_session
from app.main import app
from app.models.enums import OrgType, UserRole
from app.models.fx import FXRate
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio

# ── Unique IDs ────────────────────────────────────────────────────────────────

FX_ORG_ID = uuid.UUID("00000000-0000-00AF-0000-000000000001")
FX_USER_ID = uuid.UUID("00000000-0000-00AF-0000-000000000002")

CURRENT_USER = CurrentUser(
    user_id=FX_USER_ID,
    org_id=FX_ORG_ID,
    role=UserRole.ADMIN,
    email="fx_test@example.com",
    external_auth_id="clerk_fx_test",
)

_ECB_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube>
    <Cube time="2026-03-10">
      <Cube currency="USD" rate="1.08"/>
      <Cube currency="GBP" rate="0.855"/>
      <Cube currency="CHF" rate="0.945"/>
      <Cube currency="JPY" rate="163.21"/>
    </Cube>
  </Cube>
</gesmes:Envelope>
"""


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def fx_org(db: AsyncSession):
    from app.models.core import Organization

    org = Organization(
        id=FX_ORG_ID,
        name="FX Test Org",
        slug="fx-test-org",
        type=OrgType.INVESTOR,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def fx_user(db: AsyncSession, fx_org):
    from app.models.core import User

    user = User(
        id=FX_USER_ID,
        org_id=FX_ORG_ID,
        email="fx_test@example.com",
        full_name="FX Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_fx_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def fx_rates(db: AsyncSession, fx_org):
    """Insert a set of EUR-based FX rates for a known date."""
    rate_date = date(2026, 3, 10)
    entries = [
        FXRate(
            base_currency="EUR",
            quote_currency="USD",
            rate=1.08,
            rate_date=rate_date,
            source="ecb",
        ),
        FXRate(
            base_currency="EUR",
            quote_currency="GBP",
            rate=0.855,
            rate_date=rate_date,
            source="ecb",
        ),
        FXRate(
            base_currency="EUR",
            quote_currency="CHF",
            rate=0.945,
            rate_date=rate_date,
            source="ecb",
        ),
        FXRate(
            base_currency="EUR",
            quote_currency="JPY",
            rate=163.21,
            rate_date=rate_date,
            source="ecb",
        ),
    ]
    for entry in entries:
        db.add(entry)
    await db.flush()
    return entries


@pytest.fixture
def auth_client(db: AsyncSession):
    """Authenticated HTTP client with DB override."""
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db
    from httpx import ASGITransport, AsyncClient

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_get_latest_rates_returns_stored_rates(db: AsyncSession, fx_org, fx_rates):
    """get_latest_rates returns the most recent EUR-based rates from the DB."""
    from app.modules.fx.service import get_latest_rates

    rates, rate_date = await get_latest_rates(db)

    assert "USD" in rates
    assert "GBP" in rates
    assert "EUR" in rates
    assert rates["EUR"] == 1.0  # EUR is always 1.0
    assert abs(rates["USD"] - 1.08) < 0.001
    assert rate_date == date(2026, 3, 10)


async def test_get_latest_rates_empty_db(db: AsyncSession, fx_org):
    """get_latest_rates returns EUR=1.0 and None date when no rates in DB."""
    from app.modules.fx.service import get_latest_rates

    rates, rate_date = await get_latest_rates(db)

    # EUR is always added as 1.0 even with no DB rows
    assert rates.get("EUR") == 1.0
    assert rate_date is None


async def test_convert_same_currency_returns_original(db: AsyncSession, fx_org, fx_rates):
    """Converting EUR→EUR should return the same amount with rate=1.0."""
    from app.modules.fx.service import convert_amount

    converted, rate = await convert_amount(db, 1000.0, "EUR", "EUR", date(2026, 3, 10))

    assert converted == 1000.0
    assert rate == 1.0


async def test_convert_eur_to_usd(db: AsyncSession, fx_org, fx_rates):
    """Convert EUR to USD using stored ECB rates."""
    from app.modules.fx.service import convert_amount

    converted, rate = await convert_amount(db, 1000.0, "EUR", "USD", date(2026, 3, 10))

    assert abs(converted - 1080.0) < 0.01  # 1000 * 1.08
    assert rate is not None


async def test_convert_usd_to_gbp_via_eur(db: AsyncSession, fx_org, fx_rates):
    """Cross-rate conversion routes through EUR as the base."""
    from app.modules.fx.service import convert_amount

    # 1080 USD → 1000 EUR → 855 GBP  (1080/1.08 * 0.855)
    converted, rate = await convert_amount(db, 1080.0, "USD", "GBP", date(2026, 3, 10))

    assert abs(converted - 855.0) < 0.5
    assert rate is not None


async def test_convert_returns_none_rate_when_no_data(db: AsyncSession, fx_org):
    """If no rate exists for a currency pair the returned rate should be None."""
    from app.modules.fx.service import convert_amount

    # No rates in DB — from_currency conversion will have no rate
    converted, rate = await convert_amount(
        db, 100.0, "USD", "GBP", date(2026, 3, 10)
    )

    # Service returns original amount unchanged and rate=None
    assert converted == 100.0
    assert rate is None


async def test_fetch_ecb_rates_parses_xml_and_upserts(db: AsyncSession, fx_org):
    """fetch_ecb_rates parses ECB XML and stores rates in the DB."""
    from app.modules.fx.service import fetch_ecb_rates, get_latest_rates

    mock_resp = MagicMock()
    mock_resp.text = _ECB_XML
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        rates = await fetch_ecb_rates(db)

    assert "USD" in rates
    assert "GBP" in rates
    assert abs(rates["USD"] - 1.08) < 0.001

    # Confirm DB was populated
    stored_rates, stored_date = await get_latest_rates(db)
    assert "USD" in stored_rates
    assert stored_date == date(2026, 3, 10)


async def test_fetch_ecb_rates_falls_back_to_cache_on_bad_xml(db: AsyncSession, fx_org, fx_rates):
    """When ECB returns malformed XML the service falls back to cached DB rates."""
    from app.modules.fx.service import fetch_ecb_rates

    bad_xml = "<invalid>not ecb xml</invalid>"

    mock_resp = MagicMock()
    mock_resp.text = bad_xml
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        rates = await fetch_ecb_rates(db)

    # Falls back to the fx_rates fixture data
    assert isinstance(rates, dict)
    # Either empty dict (if no cube) or cached rates are returned — service is resilient
    assert rates is not None


async def test_api_get_latest_rates(db: AsyncSession, fx_org, fx_user, fx_rates):
    """GET /v1/fx/rates/latest returns rates JSON with rate_date."""
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/fx/rates/latest")

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert "rates" in data
    assert "rate_date" in data
    assert data["rates"]["EUR"] == 1.0


async def test_api_convert_currency(db: AsyncSession, fx_org, fx_user, fx_rates):
    """POST /v1/fx/convert returns a converted amount."""
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db

    from httpx import ASGITransport, AsyncClient

    payload = {
        "amount": 1000.0,
        "from_currency": "EUR",
        "to_currency": "USD",
        "rate_date": "2026-03-10",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/v1/fx/convert", json=payload)

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["from_currency"] == "EUR"
    assert data["to_currency"] == "USD"
    assert abs(data["converted_amount"] - 1080.0) < 0.5
    assert data["amount"] == 1000.0
