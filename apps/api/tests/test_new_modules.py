"""Tests for newly implemented modules: insurance, matching deal-room auto-creation,
field encryption, digest trigger, and connector ingest."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.core import Organization, User
from app.models.enums import (
    MatchInitiator,
    MatchStatus,
    OrgType,
    ProjectStage,
    ProjectStatus,
    ProjectType,
    UserRole,
)
from app.models.matching import MatchResult
from app.models.projects import Project
from app.schemas.auth import CurrentUser
from app.services.encryption import decrypt_field, encrypt_field

# ── Constants ─────────────────────────────────────────────────────────────────

ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
INVESTOR_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000020")
INVESTOR_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000021")

ADMIN_USER = CurrentUser(
    user_id=USER_ID,
    org_id=ORG_ID,
    role=UserRole.ADMIN,
    email="admin@example.com",
    external_auth_id="user_test_admin",
)

INVESTOR_USER = CurrentUser(
    user_id=INVESTOR_USER_ID,
    org_id=INVESTOR_ORG_ID,
    role=UserRole.ADMIN,
    email="investor@example.com",
    external_auth_id="user_test_investor",
)


# ── Session-scoped DB prep ────────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
async def ensure_meeting_scheduled_enum():
    """Add meeting_scheduled to the matchstatus DB enum if it is missing.

    ALTER TYPE … ADD VALUE cannot run inside a transaction, so we use an
    autocommit engine for this one-off DDL statement.
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        isolation_level="AUTOCOMMIT",
    )
    async with engine.connect() as conn:
        await conn.execute(
            text("ALTER TYPE matchstatus ADD VALUE IF NOT EXISTS 'meeting_scheduled'")
        )
    await engine.dispose()


# ── Auth helper ───────────────────────────────────────────────────────────────


def _override_auth(user: CurrentUser):
    async def _override():
        return user
    return _override


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def seed_org_and_project(db: AsyncSession):
    """Seed org, user, and a solar project in Kenya (high-risk geo)."""
    org = Organization(id=ORG_ID, name="Test Org", slug="test-org", type=OrgType.ALLY)
    db.add(org)
    user = User(
        id=USER_ID, org_id=ORG_ID, email="admin@example.com",
        full_name="Admin User", role=UserRole.ADMIN,
        external_auth_id="user_test_admin", is_active=True,
    )
    db.add(user)
    project = Project(
        id=PROJECT_ID,
        org_id=ORG_ID,
        name="Kenya Solar Alpha",
        slug="kenya-solar-alpha",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        stage=ProjectStage.DEVELOPMENT,
        geography_country="Kenya",
        total_investment_required=Decimal("10000000"),
        currency="USD",
    )
    db.add(project)
    await db.flush()
    return project


@pytest.fixture
async def seed_match(db: AsyncSession, seed_org_and_project):
    """Seed two orgs and a MatchResult between them."""
    investor_org = Organization(
        id=INVESTOR_ORG_ID, name="Inv Fund", slug="inv-fund", type=OrgType.INVESTOR
    )
    db.add(investor_org)
    investor_user = User(
        id=INVESTOR_USER_ID, org_id=INVESTOR_ORG_ID, email="investor@example.com",
        full_name="Investor", role=UserRole.ADMIN,
        external_auth_id="user_test_investor", is_active=True,
    )
    db.add(investor_user)

    match = MatchResult(
        investor_org_id=INVESTOR_ORG_ID,
        ally_org_id=ORG_ID,
        project_id=PROJECT_ID,
        status=MatchStatus.INTRO_REQUESTED,
        initiated_by=MatchInitiator.INVESTOR,
        overall_score=75,
    )
    db.add(match)
    await db.flush()
    return match


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Field Encryption
# ═══════════════════════════════════════════════════════════════════════════════


class TestFieldEncryption:
    def test_encrypt_produces_sentinel_prefix(self):
        token = encrypt_field("my-secret-api-key")
        assert token is not None
        assert token.startswith("enc:")

    def test_decrypt_round_trip(self):
        plaintext = "sk-live-abc123"
        encrypted = encrypt_field(plaintext)
        assert encrypted != plaintext
        decrypted = decrypt_field(encrypted)
        assert decrypted == plaintext

    def test_encrypt_none_returns_none(self):
        assert encrypt_field(None) is None

    def test_decrypt_none_returns_none(self):
        assert decrypt_field(None) is None

    def test_decrypt_legacy_plaintext_passthrough(self):
        """Values without sentinel prefix are returned as-is (backward compat)."""
        legacy = "plain-api-key-no-prefix"
        result = decrypt_field(legacy)
        assert result == legacy

    def test_different_plaintexts_produce_different_ciphertexts(self):
        a = encrypt_field("key-one")
        b = encrypt_field("key-two")
        assert a != b

    def test_same_plaintext_produces_different_ciphertexts(self):
        """Fernet includes a random IV — each encryption is unique."""
        a = encrypt_field("same-key")
        b = encrypt_field("same-key")
        assert a != b  # different random IVs

    def test_empty_string_round_trip(self):
        encrypted = encrypt_field("")
        assert decrypt_field(encrypted) == ""


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Insurance Service — deterministic logic
# ═══════════════════════════════════════════════════════════════════════════════


class TestInsuranceFallbackRecommendations:
    """Pure function tests — no DB required."""

    def _recs(self, project_type="solar", stage="development", geography="Germany"):
        from app.modules.insurance.service import _build_fallback_recommendations
        return _build_fallback_recommendations(project_type, stage, geography)

    def test_construction_stage_includes_car(self):
        recs = self._recs(stage="development")
        types = [r.policy_type for r in recs]
        assert "construction_all_risk" in types

    def test_construction_stage_includes_tpl(self):
        recs = self._recs(stage="construction")
        types = [r.policy_type for r in recs]
        assert "third_party_liability" in types

    def test_operational_stage_includes_oar(self):
        recs = self._recs(stage="operational")
        types = [r.policy_type for r in recs]
        assert "operational_all_risk" in types

    def test_operational_stage_includes_bi(self):
        recs = self._recs(stage="operational")
        types = [r.policy_type for r in recs]
        assert "business_interruption" in types

    def test_high_risk_geo_adds_political_risk(self):
        recs = self._recs(geography="Kenya")
        types = [r.policy_type for r in recs]
        assert "political_risk" in types

    def test_low_risk_geo_no_political_risk(self):
        recs = self._recs(geography="Germany")
        types = [r.policy_type for r in recs]
        assert "political_risk" not in types

    def test_wind_project_adds_weather_parametric(self):
        recs = self._recs(project_type="wind", stage="operational")
        types = [r.policy_type for r in recs]
        assert "weather_parametric" in types

    def test_solar_project_no_weather_parametric(self):
        recs = self._recs(project_type="solar")
        types = [r.policy_type for r in recs]
        assert "weather_parametric" not in types

    def test_always_includes_environmental_and_do(self):
        recs = self._recs()
        types = [r.policy_type for r in recs]
        assert "environmental_liability" in types
        assert "directors_officers" in types

    def test_construction_car_is_mandatory_and_critical(self):
        recs = self._recs(stage="construction")
        car = next(r for r in recs if r.policy_type == "construction_all_risk")
        assert car.is_mandatory is True
        assert car.priority == "critical"

    def test_do_is_not_mandatory(self):
        recs = self._recs()
        do_rec = next(r for r in recs if r.policy_type == "directors_officers")
        assert do_rec.is_mandatory is False
        assert do_rec.priority == "low"


class TestInsuranceFinancialImpact:
    """Tests for `_compute_financial_impact` — pure arithmetic."""

    def _compute(self, total_investment, annual_premium_pct, **kw):
        from app.modules.insurance.service import _compute_financial_impact
        return _compute_financial_impact(total_investment, annual_premium_pct, **kw)

    def test_irr_impact_is_negative(self):
        irr_bps, _ = self._compute(10_000_000, 0.45)
        assert irr_bps < 0

    def test_higher_premium_larger_irr_impact(self):
        irr_low, _ = self._compute(10_000_000, 0.45)
        irr_high, _ = self._compute(10_000_000, 0.80)
        assert irr_high < irr_low  # more negative

    def test_npv_is_positive(self):
        _, npv = self._compute(10_000_000, 0.45)
        assert npv > 0

    def test_npv_with_zero_discount_rate_equals_sum(self):
        """At 0% discount rate, NPV should be annual_premium * project_life_years."""
        total = 10_000_000
        pct = 0.50
        annual = total * (pct / 100)
        life = 20
        _, npv = self._compute(total, pct, discount_rate=0.0, project_life_years=life)
        assert abs(npv - annual * life) < 1.0

    def test_zero_investment_no_crash(self):
        irr_bps, npv = self._compute(0, 0.45)
        assert irr_bps == 0
        assert npv == 0.0

    def test_geo_premium_multiplier_kenya(self):
        from app.modules.insurance.service import _geo_premium_multiplier
        assert _geo_premium_multiplier("Kenya") == 1.40

    def test_geo_premium_multiplier_germany(self):
        from app.modules.insurance.service import _geo_premium_multiplier
        assert _geo_premium_multiplier("Germany") == 1.0


class TestInsuranceAPI:
    """API-level tests for insurance endpoints."""

    @pytest.mark.anyio
    async def test_get_impact_200(
        self, client: AsyncClient, db: AsyncSession, seed_org_and_project
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        try:
            with (
                patch(
                    "app.modules.insurance.service._generate_ai_narrative",
                    new_callable=AsyncMock,
                    return_value="Mocked insurance narrative.",
                ),
                # Mock signal score query to avoid hitting unmigrated columns
                patch(
                    "app.modules.insurance.service._get_latest_signal_score",
                    new_callable=AsyncMock,
                    return_value=None,
                ),
            ):
                resp = await client.get(f"/v1/insurance/projects/{PROJECT_ID}/impact")
            assert resp.status_code == 200
            data = resp.json()
            assert data["project_id"] == str(PROJECT_ID)
            assert "recommendations" in data
            assert len(data["recommendations"]) > 0
            assert data["estimated_annual_premium_pct"] > 0
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_impact_404_unknown_project(
        self, client: AsyncClient, db: AsyncSession, seed_org_and_project
    ):
        fake = uuid.UUID("00000000-0000-0000-0000-999999999999")
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = await client.get(f"/v1/insurance/projects/{fake}/impact")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_get_summary_200(
        self, client: AsyncClient, db: AsyncSession, seed_org_and_project
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db
        try:
            with patch(
                "app.modules.insurance.service._get_latest_signal_score",
                new_callable=AsyncMock,
                return_value=None,
            ):
                resp = await client.get(f"/v1/insurance/projects/{PROJECT_ID}/summary")
            assert resp.status_code == 200
            data = resp.json()
            assert "coverage_adequacy" in data
            assert "risk_reduction_score" in data
            assert "estimated_annual_premium" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_high_risk_geo_premium_higher(
        self, client: AsyncClient, db: AsyncSession, seed_org_and_project
    ):
        """Kenya (high-risk geo) should have a higher premium than a low-risk geography."""
        from app.modules.insurance.service import _BASE_PREMIUM_PCT, _geo_premium_multiplier
        base = _BASE_PREMIUM_PCT.get("solar", 0.50)
        kenya_pct = base * _geo_premium_multiplier("Kenya")
        germany_pct = base * _geo_premium_multiplier("Germany")
        assert kenya_pct > germany_pct


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Matching — deal room auto-creation on meeting_scheduled
# ═══════════════════════════════════════════════════════════════════════════════


class TestMatchingDealRoomAutoCreate:
    """Tests for update_match_status deal-room auto-creation logic.

    All DB calls are mocked so tests are isolated from schema drift and async
    lazy-load issues (SQLAlchemy expires server-generated `updated_at` after
    flush, which fails as a sync call inside async code).
    """

    _mock_room_id = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
    _match_id = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000001")

    def _make_mock_match(self, status: "MatchStatus") -> "MagicMock":
        from datetime import datetime, timezone
        from unittest.mock import MagicMock

        m = MagicMock()
        m.id = self._match_id
        m.status = status
        m.investor_org_id = INVESTOR_ORG_ID
        m.ally_org_id = ORG_ID
        m.investor_notes = ""
        m.ally_notes = ""
        m.is_deleted = False
        m.updated_at = datetime.now(timezone.utc)
        return m

    def _make_mock_db(self, match_mock: "MagicMock") -> "AsyncMock":
        from unittest.mock import MagicMock

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = match_mock

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=execute_result)
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        return mock_db

    @pytest.mark.anyio
    async def test_update_to_meeting_scheduled_creates_deal_room(self):
        """Advancing to meeting_scheduled must call _auto_create_deal_room."""
        from app.models.enums import MatchStatus
        from app.modules.matching import service as matching_service

        mock_match = self._make_mock_match(MatchStatus.INTRO_REQUESTED)
        mock_db = self._make_mock_db(mock_match)

        with patch.object(
            matching_service,
            "_auto_create_deal_room",
            new_callable=AsyncMock,
            return_value=self._mock_room_id,
        ) as mock_create:
            response = await matching_service.update_match_status(
                mock_db,
                match_id=self._match_id,
                org_id=INVESTOR_ORG_ID,
                user_id=INVESTOR_USER_ID,
                status="meeting_scheduled",
                notes=None,
            )

        assert response.status == "meeting_scheduled"
        assert response.deal_room_id == self._mock_room_id
        mock_create.assert_called_once()

    @pytest.mark.anyio
    async def test_update_to_other_status_no_deal_room(self):
        """Advancing to a non-meeting_scheduled status must NOT call _auto_create_deal_room."""
        from app.models.enums import MatchStatus
        from app.modules.matching import service as matching_service

        mock_match = self._make_mock_match(MatchStatus.INTRO_REQUESTED)
        mock_db = self._make_mock_db(mock_match)

        with patch.object(
            matching_service,
            "_auto_create_deal_room",
            new_callable=AsyncMock,
        ) as mock_create:
            response = await matching_service.update_match_status(
                mock_db,
                match_id=self._match_id,
                org_id=INVESTOR_ORG_ID,
                user_id=INVESTOR_USER_ID,
                status="engaged",
                notes=None,
            )

        assert response.status == "engaged"
        assert response.deal_room_id is None
        mock_create.assert_not_called()

    @pytest.mark.anyio
    async def test_update_invalid_status_raises(self):
        from app.models.enums import MatchStatus
        from app.modules.matching import service as matching_service

        mock_match = self._make_mock_match(MatchStatus.INTRO_REQUESTED)
        mock_db = self._make_mock_db(mock_match)

        with pytest.raises(ValueError, match="Invalid status"):
            await matching_service.update_match_status(
                mock_db,
                match_id=self._match_id,
                org_id=INVESTOR_ORG_ID,
                user_id=INVESTOR_USER_ID,
                status="does_not_exist",
                notes=None,
            )

    @pytest.mark.anyio
    async def test_update_match_not_found_raises(self):
        from app.modules.matching import service as matching_service
        from unittest.mock import MagicMock

        # scalar_one_or_none returns None → match not found
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=execute_result)

        with pytest.raises(LookupError):
            await matching_service.update_match_status(
                mock_db,
                match_id=uuid.UUID("00000000-0000-0000-0000-999999999999"),
                org_id=INVESTOR_ORG_ID,
                user_id=INVESTOR_USER_ID,
                status="engaged",
                notes=None,
            )

    @pytest.mark.anyio
    async def test_duplicate_meeting_scheduled_no_second_deal_room(self):
        """Re-sending meeting_scheduled (same old_status) must not call _auto_create_deal_room again."""
        from app.models.enums import MatchStatus
        from app.modules.matching import service as matching_service

        # Set match already at meeting_scheduled
        mock_match = self._make_mock_match(MatchStatus.MEETING_SCHEDULED)
        mock_db = self._make_mock_db(mock_match)

        with patch.object(
            matching_service,
            "_auto_create_deal_room",
            new_callable=AsyncMock,
            return_value=self._mock_room_id,
        ) as mock_create:
            response = await matching_service.update_match_status(
                mock_db,
                match_id=self._match_id,
                org_id=INVESTOR_ORG_ID,
                user_id=INVESTOR_USER_ID,
                status="meeting_scheduled",
                notes=None,
            )

        # old_status == new_status, so deal room should NOT be created
        assert response.deal_room_id is None
        mock_create.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Digest endpoints
# ═══════════════════════════════════════════════════════════════════════════════


class TestDigestEndpoints:
    @pytest.mark.anyio
    async def test_preview_returns_200(
        self, client: AsyncClient, db: AsyncSession
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db

        with patch(
            "app.modules.digest.service.gather_digest_data",
            new_callable=AsyncMock,
            return_value={
                "new_projects": [],
                "portfolio_activity": [],
                "ai_tasks": [],
                "match_updates": [],
            },
        ):
            try:
                resp = await client.get("/v1/digest/preview?days=7")
                assert resp.status_code == 200
                data = resp.json()
                # Router wraps data in {"days": ..., "summary": ...}
                assert "summary" in data
                assert "days" in data
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_trigger_returns_summary(
        self, client: AsyncClient, db: AsyncSession
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db

        mock_data = {
            "new_projects": [{"id": str(PROJECT_ID), "name": "Solar Farm"}],
            "portfolio_activity": [],
            "ai_tasks": [{"type": "scoring", "count": 3}],
            "match_updates": [],
        }
        with (
            patch(
                "app.modules.digest.service.gather_digest_data",
                new_callable=AsyncMock,
                return_value=mock_data,
            ),
            patch(
                "app.modules.digest.service.generate_digest_summary",
                new_callable=AsyncMock,
                return_value="Summary: 1 new project, 3 AI tasks.",
            ),
        ):
            try:
                resp = await client.post("/v1/digest/trigger?days=7")
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "generated"
                assert "narrative" in data
                assert data["narrative"] == "Summary: 1 new project, 3 AI tasks."
            finally:
                app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Connector ingest endpoint
# ═══════════════════════════════════════════════════════════════════════════════


class TestConnectorIngest:
    @pytest.mark.anyio
    async def test_ingest_calls_service_and_returns_document_id(
        self, client: AsyncClient, db: AsyncSession
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db

        connector_id = uuid.uuid4()
        expected_response = {
            "document_id": str(uuid.uuid4()),
            "document_name": "ecb_fx_20250101_120000.json",
            "file_size_bytes": 1024,
            "s3_key": "connector-data/org/ecb/ecb_fx_20250101_120000.json",
        }

        with patch(
            "app.modules.connectors.service.ingest_to_dataroom",
            new_callable=AsyncMock,
            return_value=expected_response,
        ):
            try:
                resp = await client.post(
                    f"/v1/connectors/{connector_id}/ingest",
                    json={
                        "project_id": str(PROJECT_ID),
                        "endpoint": "fx/rates",
                        "params": {"currency": "EUR"},
                    },
                )
                assert resp.status_code == 201
                data = resp.json()
                assert "document_id" in data
                assert data["document_id"] == expected_response["document_id"]
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_ingest_connector_not_found_returns_404(
        self, client: AsyncClient, db: AsyncSession
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db

        connector_id = uuid.uuid4()

        with patch(
            "app.modules.connectors.service.ingest_to_dataroom",
            new_callable=AsyncMock,
            side_effect=ValueError("Connector not found"),
        ):
            try:
                resp = await client.post(
                    f"/v1/connectors/{connector_id}/ingest",
                    json={"project_id": str(PROJECT_ID), "endpoint": "fx/rates"},
                )
                assert resp.status_code == 404
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_ingest_connector_disabled_returns_404(
        self, client: AsyncClient, db: AsyncSession
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db

        connector_id = uuid.uuid4()

        with patch(
            "app.modules.connectors.service.ingest_to_dataroom",
            new_callable=AsyncMock,
            side_effect=ValueError("Connector is not enabled for this organisation"),
        ):
            try:
                resp = await client.post(
                    f"/v1/connectors/{connector_id}/ingest",
                    json={"project_id": str(PROJECT_ID), "endpoint": "fx/rates"},
                )
                assert resp.status_code == 404
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.anyio
    async def test_ingest_fetch_failure_returns_502(
        self, client: AsyncClient, db: AsyncSession
    ):
        app.dependency_overrides[get_current_user] = _override_auth(ADMIN_USER)
        app.dependency_overrides[get_db] = lambda: db

        connector_id = uuid.uuid4()

        with patch(
            "app.modules.connectors.service.ingest_to_dataroom",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Connector fetch failed: timeout"),
        ):
            try:
                resp = await client.post(
                    f"/v1/connectors/{connector_id}/ingest",
                    json={"project_id": str(PROJECT_ID), "endpoint": "fx/rates"},
                )
                assert resp.status_code == 502
            finally:
                app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Connector encryption integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestConnectorEncryptionIntegration:
    """Verify that enable_connector encrypts keys before storing.

    Uses a mock DB session to avoid depending on data_connectors table migrations.
    The assertions focus on what is passed to the ORM object, not the DB itself.
    """

    def _make_connector_mock_db(self, captured: dict):
        """Build a mock AsyncSession for enable_connector tests.

        db.add is a SYNC method — must be a MagicMock, not AsyncMock, so that
        side_effect fires on the call rather than only when the coroutine is awaited.
        """
        from app.models.connectors import OrgConnectorConfig

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None  # No existing config

        def _capture_add(obj):
            if isinstance(obj, OrgConnectorConfig):
                captured["cfg"] = obj

        mock_db = MagicMock()  # sync base so .add works correctly
        mock_db.execute = AsyncMock(return_value=execute_result)
        mock_db.add = MagicMock(side_effect=_capture_add)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        return mock_db

    @pytest.mark.anyio
    async def test_enable_stores_encrypted_key(self):
        """enable_connector should set api_key_encrypted to an enc:-prefixed ciphertext."""
        from app.modules.connectors import service as conn_service

        captured: dict = {}
        mock_db = self._make_connector_mock_db(captured)

        await conn_service.enable_connector(
            mock_db, ORG_ID, uuid.uuid4(), api_key="sk-secret-key", config={}
        )

        assert "cfg" in captured, "OrgConnectorConfig was never passed to db.add()"
        cfg = captured["cfg"]
        assert cfg.api_key_encrypted is not None
        assert cfg.api_key_encrypted.startswith("enc:")
        assert cfg.api_key_encrypted != "sk-secret-key"
        # Round-trip decrypt should recover the original key
        assert decrypt_field(cfg.api_key_encrypted) == "sk-secret-key"

    @pytest.mark.anyio
    async def test_enable_with_no_api_key_stores_none(self):
        """enable_connector with api_key=None should store None (no encryption)."""
        from app.modules.connectors import service as conn_service

        captured: dict = {}
        mock_db = self._make_connector_mock_db(captured)

        await conn_service.enable_connector(
            mock_db, ORG_ID, uuid.uuid4(), api_key=None, config={}
        )

        assert "cfg" in captured, "OrgConnectorConfig was never passed to db.add()"
        assert captured["cfg"].api_key_encrypted is None
