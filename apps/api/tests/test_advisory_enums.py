"""Advisory enum regression tests.

Validates that every _lc_enum() column in advisory models round-trips through
the DB with lowercase string values — not SQLAlchemy 2.0's uppercase NAME
binding that caused the original advisory enum bug.

Three layers of protection:
  1. Generic safety-net (no DB) — introspects every advisory model's SAEnum
     columns at import time and fails if any str enum is missing values_callable
     or yields uppercase values.
  2. ORM round-trip (DB, no HTTP) — inserts records directly via SQLAlchemy
     for models without direct creation API endpoints, then reads the raw DB
     value back to confirm it is lowercase.
  3. API round-trip (HTTP) — creates records via the HTTP endpoints and asserts
     the JSON response contains lowercase enum strings.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Enum as SAEnum
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advisory import (
    BoardAdvisorApplication,
    BoardAdvisorProfile,
    EquityScenario,
    InsurancePolicy,
    InsuranceQuote,
    InvestorPersona,
    MonitoringAlert,
)
from app.models.core import Organization, User
from app.models.enums import (
    AdvisorAvailabilityStatus,
    AdvisorCompensationPreference,
    AntiDilutionType,
    BoardAdvisorApplicationStatus,
    EquitySecurityType,
    InsurancePolicyStatus,
    InsurancePremiumFrequency,
    InsuranceSide,
    InvestorPersonaStrategy,
    MonitoringAlertDomain,
    MonitoringAlertSeverity,
    MonitoringAlertType,
    OrgType,
    ProjectStatus,
    ProjectType,
    UserRole,
)
from app.models.projects import Project

pytestmark = pytest.mark.anyio

# ── Unique UUIDs for this module (no collision with other test modules) ────────

AE_ORG_ID = uuid.UUID("00000000-0000-0000-00ae-000000000001")
AE_USER_ID = uuid.UUID("00000000-0000-0000-00ae-000000000002")
AE_PROJECT_ID = uuid.UUID("00000000-0000-0000-00ae-000000000003")
AE_INV_ORG_ID = uuid.UUID("00000000-0000-0000-00ae-000000000010")
AE_INV_USER_ID = uuid.UUID("00000000-0000-0000-00ae-000000000011")


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture
async def ae_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=AE_ORG_ID,
        name="AdvisoryEnum Org",
        slug="advisory-enum-org",
        type=OrgType.ALLY,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def ae_user(db: AsyncSession, ae_org: Organization) -> User:
    user = User(
        id=AE_USER_ID,
        org_id=AE_ORG_ID,
        email="advisory-enum@example.com",
        full_name="Advisory Enum User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_advisory_enum",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def ae_project(db: AsyncSession, ae_org: Organization) -> Project:
    proj = Project(
        id=AE_PROJECT_ID,
        org_id=AE_ORG_ID,
        name="Advisory Enum Solar Project",
        slug="advisory-enum-solar",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        geography_country="Kenya",
        total_investment_required=5_000_000,
        currency="USD",
        is_deleted=False,
    )
    db.add(proj)
    await db.flush()
    return proj


@pytest.fixture
async def ae_investor_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=AE_INV_ORG_ID,
        name="AdvisoryEnum Investor",
        slug="advisory-enum-investor",
        type=OrgType.INVESTOR,
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def ae_investor_user(db: AsyncSession, ae_investor_org: Organization) -> User:
    user = User(
        id=AE_INV_USER_ID,
        org_id=AE_INV_ORG_ID,
        email="advisory-enum-inv@example.com",
        full_name="Advisory Enum Investor",
        role=UserRole.ADMIN,
        external_auth_id="clerk_advisory_enum_inv",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def ae_client(db: AsyncSession, ae_user: User) -> AsyncClient:
    """Authenticated client for the ally org."""
    from app.auth.dependencies import get_current_user
    from app.core.database import get_db
    from app.main import app as _app
    from app.schemas.auth import CurrentUser

    cu = CurrentUser(
        user_id=AE_USER_ID,
        org_id=AE_ORG_ID,
        role=UserRole.ADMIN,
        email="advisory-enum@example.com",
        external_auth_id="clerk_advisory_enum",
    )
    _app.dependency_overrides[get_current_user] = lambda: cu
    _app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.pop(get_current_user, None)
    _app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def ae_investor_client(db: AsyncSession, ae_investor_user: User) -> AsyncClient:
    """Authenticated client for the investor org."""
    from app.auth.dependencies import get_current_user
    from app.core.database import get_db
    from app.main import app as _app
    from app.schemas.auth import CurrentUser

    cu = CurrentUser(
        user_id=AE_INV_USER_ID,
        org_id=AE_INV_ORG_ID,
        role=UserRole.ADMIN,
        email="advisory-enum-inv@example.com",
        external_auth_id="clerk_advisory_enum_inv",
    )
    _app.dependency_overrides[get_current_user] = lambda: cu
    _app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.pop(get_current_user, None)
    _app.dependency_overrides.pop(get_db, None)


# ── Layer 1: Generic safety net (no DB required) ───────────────────────────────

_ADVISORY_MODELS = [
    BoardAdvisorProfile,
    BoardAdvisorApplication,
    InvestorPersona,
    EquityScenario,
    MonitoringAlert,
    InsuranceQuote,
    InsurancePolicy,
]


def _str_enum_columns(model_cls):
    """Yield (attr_name, SAEnum_type) for every str-enum column on model_cls."""
    mapper = sa_inspect(model_cls)
    for col_prop in mapper.column_attrs:
        col = col_prop.columns[0]
        if not isinstance(col.type, SAEnum):
            continue
        enum_cls = col.type.enum_class
        if enum_cls is None or not issubclass(enum_cls, str):
            continue
        yield col_prop.key, col.type


@pytest.mark.parametrize("model_cls", _ADVISORY_MODELS, ids=lambda m: m.__name__)
def test_advisory_enum_columns_have_lowercase_enums(model_cls):
    """Every advisory str-enum SAEnum column must expose only lowercase values.

    Without _lc_enum(), SQLAlchemy 2.0 binds using the enum NAME (UPPERCASE),
    which mismatches the lowercase values stored in the DB by the migration.
    This test will fail if someone adds a new advisory enum column without
    applying the _lc_enum() helper.
    """
    for attr_name, enum_type in _str_enum_columns(model_cls):
        # enum_type.enums holds the strings that SQLAlchemy will bind to DB
        for raw_value in enum_type.enums:
            assert raw_value == raw_value.lower(), (
                f"{model_cls.__name__}.{attr_name}: SAEnum contains uppercase "
                f"value '{raw_value}'. Apply _lc_enum() to prevent the "
                f"SQLAlchemy 2.0 NAME-binding bug (expects lowercase in DB)."
            )


def test_lc_enum_helper_covers_all_advisory_str_enum_columns():
    """No advisory model may have a str-enum column that uses mixed-case enums.

    Catches regressions: if someone adds a new advisory model or column using
    plain mapped_column(SAEnum(SomeStrEnum)) instead of _lc_enum(), this test
    fails immediately — before any DB migration or runtime error occurs.
    """
    violations = []
    for model_cls in _ADVISORY_MODELS:
        for attr_name, enum_type in _str_enum_columns(model_cls):
            bad = [v for v in enum_type.enums if v != v.lower()]
            if bad:
                violations.append(f"{model_cls.__name__}.{attr_name}: uppercase values {bad}")
    assert not violations, "Advisory enum columns missing _lc_enum():\n" + "\n".join(violations)


# ── Layer 2: ORM round-trip (DB write + raw SQL read) ─────────────────────────


class TestBoardAdvisorProfileORM:
    """Direct ORM tests — availability_status and compensation_preference
    must survive a DB insert/read as their lowercase string form."""

    async def test_availability_status_stored_lowercase(
        self, db: AsyncSession, ae_user: User, ae_org: Organization
    ):
        """Insert a BoardAdvisorProfile for each AdvisorAvailabilityStatus value
        and confirm the raw DB column value is lowercase.

        Because user_id is UNIQUE in board_advisor_profiles, we create one User
        per enum value within this test, all linked to ae_org.
        """
        for i, status in enumerate(AdvisorAvailabilityStatus):
            user = User(
                id=uuid.UUID(f"00000000-0000-0000-a{i:03x}-000000000001"),
                org_id=AE_ORG_ID,
                email=f"avail-{i}@advisory-enum-test.example",
                full_name=f"Avail User {i}",
                role=UserRole.ANALYST,
                external_auth_id=f"clerk_avail_{i}",
                is_active=True,
            )
            db.add(user)
            await db.flush()

            profile = BoardAdvisorProfile(
                id=uuid.UUID(f"00000000-0000-0000-a{i:03x}-000000000002"),
                user_id=user.id,
                org_id=AE_ORG_ID,
                availability_status=status,
                compensation_preference=AdvisorCompensationPreference.NEGOTIABLE,
                bio=f"Test advisor {status.value}",
            )
            db.add(profile)

        await db.flush()

        rows = await db.execute(
            text(
                "SELECT availability_status::text FROM board_advisor_profiles "
                "WHERE org_id = :org_id"
            ),
            {"org_id": str(AE_ORG_ID)},
        )
        db_values = {r[0] for r in rows}
        expected = {s.value for s in AdvisorAvailabilityStatus}
        assert db_values == expected, (
            f"DB has {db_values!r}, expected all-lowercase {expected!r}. "
            "The _lc_enum() fix may have been removed."
        )

    async def test_compensation_preference_stored_lowercase(
        self, db: AsyncSession, ae_org: Organization
    ):
        for i, pref in enumerate(AdvisorCompensationPreference):
            user = User(
                id=uuid.UUID(f"00000000-0000-0000-b{i:03x}-000000000001"),
                org_id=AE_ORG_ID,
                email=f"comp-{i}@advisory-enum-test.example",
                full_name=f"Comp User {i}",
                role=UserRole.ANALYST,
                external_auth_id=f"clerk_comp_{i}",
                is_active=True,
            )
            db.add(user)
            await db.flush()

            profile = BoardAdvisorProfile(
                id=uuid.UUID(f"00000000-0000-0000-b{i:03x}-000000000002"),
                user_id=user.id,
                org_id=AE_ORG_ID,
                availability_status=AdvisorAvailabilityStatus.AVAILABLE,
                compensation_preference=pref,
                bio=f"Test pref {pref.value}",
            )
            db.add(profile)

        await db.flush()

        rows = await db.execute(
            text(
                "SELECT compensation_preference::text FROM board_advisor_profiles "
                "WHERE org_id = :org_id"
            ),
            {"org_id": str(AE_ORG_ID)},
        )
        db_values = {r[0] for r in rows}
        expected = {p.value for p in AdvisorCompensationPreference}
        assert db_values == expected


class TestMonitoringAlertORM:
    """MonitoringAlert has no direct POST endpoint — test via ORM."""

    async def test_alert_type_stored_lowercase(
        self, db: AsyncSession, ae_org: Organization, ae_project: Project
    ):
        for i, alert_type in enumerate(MonitoringAlertType):
            alert = MonitoringAlert(
                id=uuid.UUID(f"00000000-0000-0000-eee1-{i:012d}"),
                org_id=AE_ORG_ID,
                project_id=AE_PROJECT_ID,
                alert_type=alert_type,
                severity=MonitoringAlertSeverity.INFO,
                domain=MonitoringAlertDomain.MARKET,
                title=f"Test alert {alert_type.value}",
                description="ORM enum regression test",
            )
            db.add(alert)

        await db.flush()

        rows = await db.execute(
            text("SELECT alert_type::text FROM monitoring_alerts " "WHERE org_id = :org_id"),
            {"org_id": str(AE_ORG_ID)},
        )
        db_values = {r[0] for r in rows}
        expected = {t.value for t in MonitoringAlertType}
        assert db_values == expected

    async def test_severity_stored_lowercase(
        self, db: AsyncSession, ae_org: Organization, ae_project: Project
    ):
        for i, sev in enumerate(MonitoringAlertSeverity):
            alert = MonitoringAlert(
                id=uuid.UUID(f"00000000-0000-0000-eee2-{i:012d}"),
                org_id=AE_ORG_ID,
                alert_type=MonitoringAlertType.NEWS_ALERT,
                severity=sev,
                domain=MonitoringAlertDomain.CLIMATE,
                title=f"Severity test {sev.value}",
                description="severity enum test",
            )
            db.add(alert)

        await db.flush()

        rows = await db.execute(
            text("SELECT severity::text FROM monitoring_alerts WHERE org_id = :org_id"),
            {"org_id": str(AE_ORG_ID)},
        )
        db_values = {r[0] for r in rows}
        expected = {s.value for s in MonitoringAlertSeverity}
        assert db_values == expected

    async def test_domain_stored_lowercase(self, db: AsyncSession, ae_org: Organization):
        for i, domain in enumerate(MonitoringAlertDomain):
            alert = MonitoringAlert(
                id=uuid.UUID(f"00000000-0000-0000-eee3-{i:012d}"),
                org_id=AE_ORG_ID,
                alert_type=MonitoringAlertType.REGULATORY_CHANGE,
                severity=MonitoringAlertSeverity.WARNING,
                domain=domain,
                title=f"Domain test {domain.value}",
                description="domain enum test",
            )
            db.add(alert)

        await db.flush()

        rows = await db.execute(
            text("SELECT domain::text FROM monitoring_alerts WHERE org_id = :org_id"),
            {"org_id": str(AE_ORG_ID)},
        )
        db_values = {r[0] for r in rows}
        expected = {d.value for d in MonitoringAlertDomain}
        assert db_values == expected


# ── Layer 3: API round-trip (HTTP → response JSON must be lowercase) ───────────


class TestBoardAdvisorProfileAPI:
    """POST /v1/board-advisors/my-profile → enum fields in response are lowercase."""

    async def test_availability_status_returns_lowercase(
        self, ae_client: AsyncClient, ae_user: User
    ):
        resp = await ae_client.post(
            "/v1/board-advisors/my-profile",
            json={
                "availability_status": "available",
                "compensation_preference": "equity",
                "bio": "Enum regression test",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["availability_status"] == "available", (
            f"Expected 'available', got {data['availability_status']!r}. "
            "SQLAlchemy 2.0 may be returning enum NAME instead of VALUE."
        )
        assert data["compensation_preference"] == "equity"

    async def test_update_availability_to_limited_returns_lowercase(
        self, ae_client: AsyncClient, ae_user: User
    ):
        # Create profile first
        await ae_client.post(
            "/v1/board-advisors/my-profile",
            json={"availability_status": "available", "bio": "Initial"},
        )
        # Update
        resp = await ae_client.put(
            "/v1/board-advisors/my-profile",
            json={"availability_status": "limited"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["availability_status"] == "limited"

    async def test_update_availability_to_unavailable_returns_lowercase(
        self, ae_client: AsyncClient, ae_user: User
    ):
        await ae_client.post(
            "/v1/board-advisors/my-profile",
            json={"availability_status": "available", "bio": "Initial"},
        )
        resp = await ae_client.put(
            "/v1/board-advisors/my-profile",
            json={"availability_status": "unavailable"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["availability_status"] == "unavailable"

    async def test_all_compensation_preferences_via_update(
        self, ae_client: AsyncClient, ae_user: User
    ):
        """Round-trip all 4 compensation_preference values through the API."""
        await ae_client.post(
            "/v1/board-advisors/my-profile",
            json={"availability_status": "available", "bio": "Comp pref test"},
        )
        for pref in AdvisorCompensationPreference:
            resp = await ae_client.put(
                "/v1/board-advisors/my-profile",
                json={"compensation_preference": pref.value},
            )
            assert resp.status_code == 200, f"{pref.value}: {resp.text}"
            assert resp.json()["compensation_preference"] == pref.value, (
                f"compensation_preference '{pref.value}' came back as "
                f"{resp.json()['compensation_preference']!r} — uppercase regression"
            )


class TestBoardAdvisorApplicationAPI:
    """POST /v1/board-advisors/apply → status field in response is lowercase."""

    async def test_application_status_returns_pending_lowercase(
        self, ae_client: AsyncClient, ae_user: User, ae_project: Project
    ):
        # Need a profile first
        await ae_client.post(
            "/v1/board-advisors/my-profile",
            json={"availability_status": "available", "bio": "Applicant"},
        )
        resp = await ae_client.post(
            "/v1/board-advisors/apply",
            json={
                "project_id": str(AE_PROJECT_ID),
                "role_offered": "Lead Sustainability Advisor",
                "message": "Enum regression test application",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["status"] == "pending", (
            f"Expected 'pending', got {data['status']!r}. "
            "BoardAdvisorApplicationStatus enum may be returning uppercase NAME."
        )

    async def test_application_status_update_returns_lowercase(
        self, ae_client: AsyncClient, ae_user: User, ae_project: Project
    ):
        await ae_client.post(
            "/v1/board-advisors/my-profile",
            json={"availability_status": "available", "bio": "Applicant update"},
        )
        apply_resp = await ae_client.post(
            "/v1/board-advisors/apply",
            json={
                "project_id": str(AE_PROJECT_ID),
                "role_offered": "CFO Advisor",
            },
        )
        assert apply_resp.status_code == 201, apply_resp.text
        application_id = apply_resp.json()["id"]

        # Update status to accepted — verifies non-default enum value is lowercase
        resp = await ae_client.put(
            f"/v1/board-advisors/applications/{application_id}/status",
            json={"status": "accepted"},
        )
        assert resp.status_code == 200, resp.text
        assert (
            resp.json()["status"] == "accepted"
        ), f"Expected 'accepted', got {resp.json()['status']!r}"


class TestInvestorPersonaAPI:
    """POST /v1/investor-personas → strategy_type in response is lowercase."""

    async def test_default_strategy_type_is_lowercase(
        self, ae_investor_client: AsyncClient, ae_investor_user: User
    ):
        resp = await ae_investor_client.post(
            "/v1/investor-personas",
            json={"persona_name": "Conservative Fund", "strategy_type": "conservative"},
        )
        assert resp.status_code == 201, resp.text
        assert (
            resp.json()["strategy_type"] == "conservative"
        ), f"Expected 'conservative', got {resp.json()['strategy_type']!r}"

    async def test_all_strategy_types_round_trip_lowercase(
        self, ae_investor_client: AsyncClient, ae_investor_user: User
    ):
        """Every InvestorPersonaStrategy value must come back lowercase from the API."""
        for strategy in InvestorPersonaStrategy:
            resp = await ae_investor_client.post(
                "/v1/investor-personas",
                json={
                    "persona_name": f"Fund {strategy.value}",
                    "strategy_type": strategy.value,
                },
            )
            assert resp.status_code == 201, f"{strategy.value}: {resp.text}"
            returned = resp.json()["strategy_type"]
            assert returned == strategy.value, (
                f"strategy_type '{strategy.value}' round-tripped as {returned!r}. "
                "Possible SQLAlchemy 2.0 enum NAME binding regression."
            )


class TestEquityScenarioAPI:
    """POST /v1/equity-calculator/scenarios → security_type and
    anti_dilution_type are lowercase in the response."""

    async def test_common_equity_security_type_is_lowercase(
        self, ae_client: AsyncClient, ae_org: Organization
    ):
        resp = await ae_client.post(
            "/v1/equity-calculator/scenarios",
            json={
                "scenario_name": "Series A",
                "pre_money_valuation": 10_000_000,
                "investment_amount": 2_000_000,
                "security_type": "common_equity",
                "shares_outstanding_before": 1_000_000,
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert (
            data["security_type"] == "common_equity"
        ), f"Expected 'common_equity', got {data['security_type']!r}"

    async def test_all_security_types_round_trip_lowercase(
        self, ae_client: AsyncClient, ae_org: Organization
    ):
        for sec_type in EquitySecurityType:
            resp = await ae_client.post(
                "/v1/equity-calculator/scenarios",
                json={
                    "scenario_name": f"Test {sec_type.value}",
                    "pre_money_valuation": 5_000_000,
                    "investment_amount": 1_000_000,
                    "security_type": sec_type.value,
                    "shares_outstanding_before": 500_000,
                },
            )
            assert resp.status_code == 201, f"{sec_type.value}: {resp.text}"
            returned = resp.json()["security_type"]
            assert (
                returned == sec_type.value
            ), f"security_type '{sec_type.value}' came back as {returned!r}"

    async def test_anti_dilution_type_broad_based_is_lowercase(
        self, ae_client: AsyncClient, ae_org: Organization
    ):
        resp = await ae_client.post(
            "/v1/equity-calculator/scenarios",
            json={
                "scenario_name": "Preferred with broad-based anti-dilution",
                "pre_money_valuation": 20_000_000,
                "investment_amount": 5_000_000,
                "security_type": "preferred_equity",
                "anti_dilution_type": "broad_based",
                "shares_outstanding_before": 2_000_000,
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert (
            data["anti_dilution_type"] == "broad_based"
        ), f"Expected 'broad_based', got {data['anti_dilution_type']!r}"

    async def test_all_anti_dilution_types_round_trip_lowercase(
        self, ae_client: AsyncClient, ae_org: Organization
    ):
        for ad_type in AntiDilutionType:
            resp = await ae_client.post(
                "/v1/equity-calculator/scenarios",
                json={
                    "scenario_name": f"AntiDilution {ad_type.value}",
                    "pre_money_valuation": 8_000_000,
                    "investment_amount": 2_000_000,
                    "security_type": "convertible_note",
                    "anti_dilution_type": ad_type.value,
                    "shares_outstanding_before": 1_000_000,
                },
            )
            assert resp.status_code == 201, f"{ad_type.value}: {resp.text}"
            returned = resp.json()["anti_dilution_type"]
            assert (
                returned == ad_type.value
            ), f"anti_dilution_type '{ad_type.value}' came back as {returned!r}"


class TestInsuranceQuoteAPI:
    """POST /v1/insurance/quotes → side field is lowercase."""

    async def test_investor_side_is_lowercase(self, ae_client: AsyncClient, ae_org: Organization):
        resp = await ae_client.post(
            "/v1/insurance/quotes",
            json={
                "provider_name": "Lloyd's of London",
                "coverage_type": "construction_all_risk",
                "coverage_amount": 5_000_000,
                "quoted_premium": 22_500,
                "currency": "USD",
                "side": "investor",
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["side"] == "investor", (
            f"Expected 'investor', got {resp.json()['side']!r}. "
            "InsuranceSide enum may be returning uppercase NAME."
        )

    async def test_ally_side_is_lowercase(self, ae_client: AsyncClient, ae_org: Organization):
        resp = await ae_client.post(
            "/v1/insurance/quotes",
            json={
                "provider_name": "Zurich Insurance",
                "coverage_type": "liability",
                "coverage_amount": 2_000_000,
                "quoted_premium": 8_000,
                "currency": "USD",
                "side": "ally",
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["side"] == "ally", f"Expected 'ally', got {resp.json()['side']!r}"

    async def test_both_insurance_sides_round_trip(
        self, ae_client: AsyncClient, ae_org: Organization
    ):
        for side in InsuranceSide:
            resp = await ae_client.post(
                "/v1/insurance/quotes",
                json={
                    "provider_name": f"Insurer {side.value}",
                    "coverage_type": "general_liability",
                    "coverage_amount": 1_000_000,
                    "quoted_premium": 5_000,
                    "currency": "USD",
                    "side": side.value,
                },
            )
            assert resp.status_code == 201, f"{side.value}: {resp.text}"
            assert resp.json()["side"] == side.value


class TestInsurancePolicyAPI:
    """POST /v1/insurance/policies → premium_frequency, status, and side
    are all lowercase in the JSON response."""

    async def _create_quote(self, client: AsyncClient, side: str = "investor") -> str:
        resp = await client.post(
            "/v1/insurance/quotes",
            json={
                "provider_name": "Policy Test Insurer",
                "coverage_type": "operational_all_risk",
                "coverage_amount": 5_000_000,
                "quoted_premium": 30_000,
                "currency": "USD",
                "side": side,
            },
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_policy_status_defaults_to_active_lowercase(
        self, ae_client: AsyncClient, ae_org: Organization, ae_project: Project
    ):
        quote_id = await self._create_quote(ae_client)
        resp = await ae_client.post(
            "/v1/insurance/policies",
            json={
                "quote_id": quote_id,
                "project_id": str(AE_PROJECT_ID),
                "policy_number": "POL-ENUM-001",
                "provider_name": "Policy Test Insurer",
                "coverage_type": "operational_all_risk",
                "coverage_amount": 5_000_000,
                "premium_amount": 30_000,
                "premium_frequency": "annual",
                "start_date": "2026-01-01",
                "end_date": "2027-01-01",
                "side": "investor",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["status"] == "active", (
            f"Expected 'active', got {data['status']!r}. "
            "InsurancePolicyStatus may be returning uppercase NAME."
        )
        assert (
            data["premium_frequency"] == "annual"
        ), f"Expected 'annual', got {data['premium_frequency']!r}"
        assert data["side"] == "investor"

    async def test_all_premium_frequencies_round_trip_lowercase(
        self, ae_client: AsyncClient, ae_org: Organization, ae_project: Project
    ):
        for i, freq in enumerate(InsurancePremiumFrequency):
            quote_id = await self._create_quote(ae_client)
            resp = await ae_client.post(
                "/v1/insurance/policies",
                json={
                    "quote_id": quote_id,
                    "project_id": str(AE_PROJECT_ID),
                    "policy_number": f"POL-FREQ-{i:03d}",
                    "provider_name": "Freq Test Insurer",
                    "coverage_type": "freight_insurance",
                    "coverage_amount": 1_000_000,
                    "premium_amount": 10_000,
                    "premium_frequency": freq.value,
                    "start_date": "2026-01-01",
                    "end_date": "2027-01-01",
                },
            )
            assert resp.status_code == 201, f"{freq.value}: {resp.text}"
            returned = resp.json()["premium_frequency"]
            assert (
                returned == freq.value
            ), f"premium_frequency '{freq.value}' came back as {returned!r}"

    async def test_policy_side_ally_is_lowercase(
        self, ae_client: AsyncClient, ae_org: Organization, ae_project: Project
    ):
        quote_id = await self._create_quote(ae_client, side="ally")
        resp = await ae_client.post(
            "/v1/insurance/policies",
            json={
                "quote_id": quote_id,
                "project_id": str(AE_PROJECT_ID),
                "policy_number": "POL-ALLY-001",
                "provider_name": "Ally Insurer",
                "coverage_type": "professional_indemnity",
                "coverage_amount": 2_000_000,
                "premium_amount": 15_000,
                "premium_frequency": "quarterly",
                "start_date": "2026-01-01",
                "end_date": "2027-01-01",
                "side": "ally",
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["side"] == "ally"
