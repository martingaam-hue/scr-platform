"""Integration tests for the Compliance module.

Covers:
  TestDeadlineCRUD         — create, read, list, update, soft-delete lifecycle
  TestDeadlineFilters      — filter by status and category, org scoping
  TestCompleteDeadline     — mark complete, verify completed_at is set
  TestRecurringDeadline    — completing a recurring deadline spawns next occurrence
  TestAutoGenerate         — EU_solar → 6, EU_wind → 4 deadlines
  TestNextOccurrence       — unit tests for _next_occurrence() (no DB required)
  TestOrgScoping           — org A cannot see org B's deadlines

Note: "compliance" is not a standard RBAC resource type, and "manage" is not
a standard action in the permission matrix. Both client fixtures patch
check_permission (same pattern as test_module_batch3/batch4) to allow them.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.auth.dependencies as deps_module
from app.auth.dependencies import get_current_user
from app.auth.rbac import check_permission as original_check
from app.core.database import get_db, get_readonly_session
from app.main import app
from app.models.compliance import ComplianceDeadline
from app.models.core import Organization, User
from app.models.enums import OrgType, ProjectStatus, ProjectType, UserRole
from app.models.projects import Project
from app.modules.compliance.service import _next_occurrence
from app.schemas.auth import CurrentUser

pytestmark = pytest.mark.anyio

# ── Module-unique UUIDs (no collision with other test files) ──────────────────

CL_ORG_ID = uuid.UUID("00000000-0000-00C1-0000-000000000001")
CL_USER_ID = uuid.UUID("00000000-0000-00C1-0000-000000000002")
CL_PROJECT_ID = uuid.UUID("00000000-0000-00C1-0000-000000000003")

CL_ORG2_ID = uuid.UUID("00000000-0000-00C1-0000-000000000020")
CL_USER2_ID = uuid.UUID("00000000-0000-00C1-0000-000000000021")

# Non-standard (action, resource_type) pairs used by the compliance router.
_CL_ALWAYS_ALLOW = {
    ("view", "compliance"),
    ("manage", "compliance"),
}

CL_CURRENT_USER = CurrentUser(
    user_id=CL_USER_ID,
    org_id=CL_ORG_ID,
    role=UserRole.ADMIN,
    email="cl_test@example.com",
    external_auth_id="clerk_cl_test",
)

CL_CURRENT_USER2 = CurrentUser(
    user_id=CL_USER2_ID,
    org_id=CL_ORG2_ID,
    role=UserRole.ADMIN,
    email="cl_test2@example.com",
    external_auth_id="clerk_cl_test2",
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def cl_org(db: AsyncSession) -> Organization:
    org = Organization(id=CL_ORG_ID, name="CL Test Org", slug="cl-test-org", type=OrgType.ALLY)
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def cl_user(db: AsyncSession, cl_org: Organization) -> User:
    user = User(
        id=CL_USER_ID,
        org_id=CL_ORG_ID,
        email="cl_test@example.com",
        full_name="CL Test User",
        role=UserRole.ADMIN,
        external_auth_id="clerk_cl_test",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def cl_project(db: AsyncSession, cl_org: Organization) -> Project:
    proj = Project(
        id=CL_PROJECT_ID,
        org_id=CL_ORG_ID,
        name="CL Solar Project",
        slug="cl-solar-project",
        project_type=ProjectType.SOLAR,
        status=ProjectStatus.ACTIVE,
        geography_country="Germany",
        total_investment_required=Decimal("5000000"),
        currency="EUR",
        is_deleted=False,
    )
    db.add(proj)
    await db.flush()
    return proj


@pytest.fixture
async def cl_org2(db: AsyncSession) -> Organization:
    org = Organization(
        id=CL_ORG2_ID, name="CL Test Org 2", slug="cl-test-org-2", type=OrgType.INVESTOR
    )
    db.add(org)
    await db.flush()
    return org


@pytest.fixture
async def cl_user2(db: AsyncSession, cl_org2: Organization) -> User:
    user = User(
        id=CL_USER2_ID,
        org_id=CL_ORG2_ID,
        email="cl_test2@example.com",
        full_name="CL Test User 2",
        role=UserRole.ADMIN,
        external_auth_id="clerk_cl_test2",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


def _patched_check_cl(role, action, resource_type, resource_id=None):
    """Allow non-standard compliance (action, resource_type) pairs in tests."""
    if (action, resource_type) in _CL_ALWAYS_ALLOW:
        return True
    return original_check(role, action, resource_type, resource_id)


@pytest.fixture
async def cl_client(db: AsyncSession, cl_user: User) -> AsyncClient:
    """Authenticated client scoped to CL_ORG_ID with compliance permissions patched."""
    app.dependency_overrides[get_current_user] = lambda: CL_CURRENT_USER
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db
    with patch.object(deps_module, "check_permission", side_effect=_patched_check_cl):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_readonly_session, None)


@pytest.fixture
async def cl_client2(db: AsyncSession, cl_user2: User) -> AsyncClient:
    """Authenticated client scoped to CL_ORG2_ID with compliance permissions patched."""
    app.dependency_overrides[get_current_user] = lambda: CL_CURRENT_USER2
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_readonly_session] = lambda: db
    with patch.object(deps_module, "check_permission", side_effect=_patched_check_cl):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_readonly_session, None)


def _deadline_payload(**overrides) -> dict:
    """Base valid DeadlineCreate payload."""
    base = {
        "category": "regulatory_filing",
        "title": "Test Compliance Deadline",
        "due_date": str(date.today() + timedelta(days=60)),
        "priority": "high",
    }
    base.update(overrides)
    return base


# ── TestDeadlineCRUD ──────────────────────────────────────────────────────────


class TestDeadlineCRUD:
    async def test_create_deadline_returns_201(self, cl_client: AsyncClient) -> None:
        payload = _deadline_payload(title="Annual EIA Report")
        resp = await cl_client.post("/v1/compliance/deadlines", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Annual EIA Report"
        assert data["category"] == "regulatory_filing"
        assert data["status"] == "upcoming"
        assert data["priority"] == "high"
        assert data["org_id"] == str(CL_ORG_ID)

    async def test_create_deadline_with_optional_fields(self, cl_client: AsyncClient) -> None:
        payload = _deadline_payload(
            title="Permit Renewal",
            category="permit",
            jurisdiction="EU",
            regulatory_body="National Authority",
            description="Annual permit renewal submission",
            priority="critical",
        )
        resp = await cl_client.post("/v1/compliance/deadlines", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["jurisdiction"] == "EU"
        assert data["regulatory_body"] == "National Authority"
        assert data["priority"] == "critical"

    async def test_get_deadline_by_id(self, cl_client: AsyncClient) -> None:
        create_resp = await cl_client.post(
            "/v1/compliance/deadlines", json=_deadline_payload(title="Get Me")
        )
        assert create_resp.status_code == 201
        deadline_id = create_resp.json()["id"]

        get_resp = await cl_client.get(f"/v1/compliance/deadlines/{deadline_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == deadline_id
        assert get_resp.json()["title"] == "Get Me"

    async def test_get_deadline_not_found(self, cl_client: AsyncClient) -> None:
        resp = await cl_client.get(f"/v1/compliance/deadlines/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_list_deadlines_returns_created(self, cl_client: AsyncClient) -> None:
        await cl_client.post("/v1/compliance/deadlines", json=_deadline_payload(title="List Me"))
        resp = await cl_client.get("/v1/compliance/deadlines")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        titles = [item["title"] for item in data["items"]]
        assert "List Me" in titles

    async def test_update_deadline(self, cl_client: AsyncClient) -> None:
        create_resp = await cl_client.post(
            "/v1/compliance/deadlines", json=_deadline_payload(title="Before Update")
        )
        deadline_id = create_resp.json()["id"]

        update_resp = await cl_client.patch(
            f"/v1/compliance/deadlines/{deadline_id}",
            json={"title": "After Update", "status": "in_progress"},
        )
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["title"] == "After Update"
        assert data["status"] == "in_progress"

    async def test_delete_deadline_returns_204(self, cl_client: AsyncClient) -> None:
        create_resp = await cl_client.post(
            "/v1/compliance/deadlines", json=_deadline_payload(title="Delete Me")
        )
        deadline_id = create_resp.json()["id"]

        del_resp = await cl_client.delete(f"/v1/compliance/deadlines/{deadline_id}")
        assert del_resp.status_code == 204

    async def test_soft_delete_hides_from_list(self, cl_client: AsyncClient) -> None:
        """After soft-delete, the deadline should not appear in list results."""
        create_resp = await cl_client.post(
            "/v1/compliance/deadlines", json=_deadline_payload(title="Soft Delete Me")
        )
        deadline_id = create_resp.json()["id"]

        await cl_client.delete(f"/v1/compliance/deadlines/{deadline_id}")

        # Should not appear in list
        list_resp = await cl_client.get("/v1/compliance/deadlines")
        ids = [item["id"] for item in list_resp.json()["items"]]
        assert deadline_id not in ids

    async def test_soft_delete_hides_from_get(self, cl_client: AsyncClient) -> None:
        """After soft-delete, the deadline should return 404 on direct GET."""
        create_resp = await cl_client.post(
            "/v1/compliance/deadlines", json=_deadline_payload(title="Gone After Delete")
        )
        deadline_id = create_resp.json()["id"]

        await cl_client.delete(f"/v1/compliance/deadlines/{deadline_id}")
        get_resp = await cl_client.get(f"/v1/compliance/deadlines/{deadline_id}")
        assert get_resp.status_code == 404


# ── TestDeadlineFilters ───────────────────────────────────────────────────────


class TestDeadlineFilters:
    async def test_filter_by_status(self, cl_client: AsyncClient) -> None:
        # Create one 'upcoming' and one 'in_progress'
        await cl_client.post(
            "/v1/compliance/deadlines", json=_deadline_payload(title="Upcoming One")
        )
        create_resp = await cl_client.post(
            "/v1/compliance/deadlines", json=_deadline_payload(title="In Progress One")
        )
        dl_id = create_resp.json()["id"]
        await cl_client.patch(f"/v1/compliance/deadlines/{dl_id}", json={"status": "in_progress"})

        resp = await cl_client.get("/v1/compliance/deadlines?status=in_progress")
        assert resp.status_code == 200
        statuses = [item["status"] for item in resp.json()["items"]]
        assert all(s == "in_progress" for s in statuses)

    async def test_filter_by_category(self, cl_client: AsyncClient) -> None:
        await cl_client.post(
            "/v1/compliance/deadlines",
            json=_deadline_payload(title="Tax Filing", category="tax"),
        )
        await cl_client.post(
            "/v1/compliance/deadlines",
            json=_deadline_payload(title="EIA Report", category="environmental"),
        )

        resp = await cl_client.get("/v1/compliance/deadlines?category=tax")
        assert resp.status_code == 200
        categories = [item["category"] for item in resp.json()["items"]]
        assert all(c == "tax" for c in categories)

    async def test_filter_by_project_id(self, cl_client: AsyncClient, cl_project: Project) -> None:
        await cl_client.post(
            "/v1/compliance/deadlines",
            json=_deadline_payload(title="Project Deadline", project_id=str(CL_PROJECT_ID)),
        )
        await cl_client.post(
            "/v1/compliance/deadlines",
            json=_deadline_payload(title="No Project Deadline"),
        )

        resp = await cl_client.get(f"/v1/compliance/deadlines?project_id={CL_PROJECT_ID}")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        assert all(item["project_id"] == str(CL_PROJECT_ID) for item in items)

    async def test_list_response_includes_summary_counts(self, cl_client: AsyncClient) -> None:
        resp = await cl_client.get("/v1/compliance/deadlines")
        assert resp.status_code == 200
        data = resp.json()
        for field in ("items", "total", "overdue_count", "due_this_week", "due_this_month"):
            assert field in data


# ── TestCompleteDeadline ──────────────────────────────────────────────────────


class TestCompleteDeadline:
    async def test_complete_sets_status_completed(self, cl_client: AsyncClient) -> None:
        create_resp = await cl_client.post(
            "/v1/compliance/deadlines",
            json=_deadline_payload(title="Complete Me", recurrence="one_time"),
        )
        deadline_id = create_resp.json()["id"]

        complete_resp = await cl_client.post(f"/v1/compliance/deadlines/{deadline_id}/complete")
        assert complete_resp.status_code == 200
        data = complete_resp.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

    async def test_complete_nonexistent_returns_404(self, cl_client: AsyncClient) -> None:
        resp = await cl_client.post(f"/v1/compliance/deadlines/{uuid.uuid4()}/complete")
        assert resp.status_code == 404

    async def test_complete_one_time_does_not_spawn_next(
        self, cl_client: AsyncClient, db: AsyncSession
    ) -> None:
        from sqlalchemy import select

        create_resp = await cl_client.post(
            "/v1/compliance/deadlines",
            json=_deadline_payload(title="One Time Only", recurrence="one_time"),
        )
        deadline_id = uuid.UUID(create_resp.json()["id"])

        await cl_client.post(f"/v1/compliance/deadlines/{deadline_id}/complete")

        # Count total deadlines for this org with same title
        result = await db.execute(
            select(ComplianceDeadline).where(
                ComplianceDeadline.org_id == CL_ORG_ID,
                ComplianceDeadline.title == "One Time Only",
            )
        )
        all_deadlines = result.scalars().all()
        # Only the original — no next occurrence
        assert len(all_deadlines) == 1


# ── TestRecurringDeadline ─────────────────────────────────────────────────────


class TestRecurringDeadline:
    async def test_completing_annual_spawns_next_occurrence(
        self, cl_client: AsyncClient, db: AsyncSession
    ) -> None:
        from sqlalchemy import select

        # Due date well in the past so _next_occurrence will compute a future date
        past_due = str(date.today() - timedelta(days=400))
        create_resp = await cl_client.post(
            "/v1/compliance/deadlines",
            json=_deadline_payload(
                title="Annual Recurring",
                recurrence="annually",
                due_date=past_due,
            ),
        )
        assert create_resp.status_code == 201
        deadline_id = uuid.UUID(create_resp.json()["id"])

        complete_resp = await cl_client.post(f"/v1/compliance/deadlines/{deadline_id}/complete")
        assert complete_resp.status_code == 200
        assert complete_resp.json()["status"] == "completed"

        # A new upcoming deadline should have been spawned
        result = await db.execute(
            select(ComplianceDeadline).where(
                ComplianceDeadline.org_id == CL_ORG_ID,
                ComplianceDeadline.title == "Annual Recurring",
                ComplianceDeadline.status == "upcoming",
            )
        )
        next_deadlines = result.scalars().all()
        assert len(next_deadlines) == 1
        assert next_deadlines[0].due_date > date.today()

    async def test_completing_quarterly_spawns_upcoming_occurrence(
        self, cl_client: AsyncClient, db: AsyncSession
    ) -> None:
        from sqlalchemy import select

        past_due = str(date.today() - timedelta(days=100))
        create_resp = await cl_client.post(
            "/v1/compliance/deadlines",
            json=_deadline_payload(
                title="Quarterly SFDR",
                recurrence="quarterly",
                due_date=past_due,
            ),
        )
        deadline_id = uuid.UUID(create_resp.json()["id"])

        await cl_client.post(f"/v1/compliance/deadlines/{deadline_id}/complete")

        result = await db.execute(
            select(ComplianceDeadline).where(
                ComplianceDeadline.org_id == CL_ORG_ID,
                ComplianceDeadline.title == "Quarterly SFDR",
                ComplianceDeadline.status == "upcoming",
            )
        )
        next_deadlines = result.scalars().all()
        assert len(next_deadlines) == 1
        assert next_deadlines[0].recurrence == "quarterly"

    async def test_next_occurrence_inherits_category(
        self, cl_client: AsyncClient, db: AsyncSession
    ) -> None:
        from sqlalchemy import select

        past_due = str(date.today() - timedelta(days=380))
        create_resp = await cl_client.post(
            "/v1/compliance/deadlines",
            json=_deadline_payload(
                title="Annually Tax",
                category="tax",
                recurrence="annually",
                due_date=past_due,
                priority="critical",
            ),
        )
        deadline_id = uuid.UUID(create_resp.json()["id"])
        await cl_client.post(f"/v1/compliance/deadlines/{deadline_id}/complete")

        result = await db.execute(
            select(ComplianceDeadline).where(
                ComplianceDeadline.org_id == CL_ORG_ID,
                ComplianceDeadline.title == "Annually Tax",
                ComplianceDeadline.status == "upcoming",
            )
        )
        next_dl = result.scalars().first()
        assert next_dl is not None
        assert next_dl.category == "tax"
        assert next_dl.priority == "critical"


# ── TestAutoGenerate ──────────────────────────────────────────────────────────


class TestAutoGenerate:
    async def test_eu_solar_generates_six_deadlines(
        self, cl_client: AsyncClient, cl_project: Project
    ) -> None:
        resp = await cl_client.post(
            "/v1/compliance/deadlines/auto-generate",
            json={
                "project_id": str(CL_PROJECT_ID),
                "jurisdiction": "EU",
                "project_type": "solar",
            },
        )
        assert resp.status_code == 200
        deadlines = resp.json()
        assert len(deadlines) == 6

    async def test_eu_solar_deadline_categories(
        self, cl_client: AsyncClient, cl_project: Project
    ) -> None:
        resp = await cl_client.post(
            "/v1/compliance/deadlines/auto-generate",
            json={
                "project_id": str(CL_PROJECT_ID),
                "jurisdiction": "EU",
                "project_type": "solar",
            },
        )
        assert resp.status_code == 200
        categories = {d["category"] for d in resp.json()}
        # EU_solar templates include environmental, permit, sfdr, reporting, insurance, tax
        assert "environmental" in categories
        assert "sfdr" in categories
        assert "tax" in categories

    async def test_eu_wind_generates_four_deadlines(
        self, cl_client: AsyncClient, cl_project: Project
    ) -> None:
        resp = await cl_client.post(
            "/v1/compliance/deadlines/auto-generate",
            json={
                "project_id": str(CL_PROJECT_ID),
                "jurisdiction": "EU",
                "project_type": "wind",
            },
        )
        assert resp.status_code == 200
        deadlines = resp.json()
        assert len(deadlines) == 4

    async def test_eu_wind_has_environmental_category(
        self, cl_client: AsyncClient, cl_project: Project
    ) -> None:
        resp = await cl_client.post(
            "/v1/compliance/deadlines/auto-generate",
            json={
                "project_id": str(CL_PROJECT_ID),
                "jurisdiction": "EU",
                "project_type": "wind",
            },
        )
        assert resp.status_code == 200
        categories = {d["category"] for d in resp.json()}
        assert "environmental" in categories

    async def test_auto_generate_deadlines_are_upcoming(
        self, cl_client: AsyncClient, cl_project: Project
    ) -> None:
        resp = await cl_client.post(
            "/v1/compliance/deadlines/auto-generate",
            json={
                "project_id": str(CL_PROJECT_ID),
                "jurisdiction": "EU",
                "project_type": "solar",
            },
        )
        assert resp.status_code == 200
        statuses = {d["status"] for d in resp.json()}
        assert statuses == {"upcoming"}

    async def test_auto_generate_due_dates_are_future(
        self, cl_client: AsyncClient, cl_project: Project
    ) -> None:
        resp = await cl_client.post(
            "/v1/compliance/deadlines/auto-generate",
            json={
                "project_id": str(CL_PROJECT_ID),
                "jurisdiction": "EU",
                "project_type": "solar",
            },
        )
        assert resp.status_code == 200
        today = date.today()
        for dl in resp.json():
            due = date.fromisoformat(dl["due_date"])
            assert due > today, f"Expected future due_date, got {due}"


# ── TestNextOccurrence ────────────────────────────────────────────────────────


class TestNextOccurrence:
    def test_annually_advances_one_year(self) -> None:
        past = date.today() - timedelta(days=400)
        result = _next_occurrence(past, "annually")
        assert result is not None
        assert result > date.today()

    def test_quarterly_advances_three_months(self) -> None:
        past = date.today() - timedelta(days=100)
        result = _next_occurrence(past, "quarterly")
        assert result is not None
        assert result > date.today()

    def test_monthly_advances_one_month(self) -> None:
        past = date.today() - timedelta(days=35)
        result = _next_occurrence(past, "monthly")
        assert result is not None
        assert result > date.today()

    def test_one_time_returns_none(self) -> None:
        any_date = date.today() - timedelta(days=10)
        result = _next_occurrence(any_date, "one_time")
        assert result is None

    def test_none_recurrence_returns_none(self) -> None:
        result = _next_occurrence(date.today() - timedelta(days=10), None)
        assert result is None

    def test_future_base_date_still_advances_past_today(self) -> None:
        # If due_date is already in the future, the next occurrence is the
        # year after that (for annually) — i.e. still > today
        future = date.today() + timedelta(days=30)
        result = _next_occurrence(future, "annually")
        assert result is not None
        assert result > date.today()

    def test_unknown_recurrence_returns_none(self) -> None:
        result = _next_occurrence(date.today() - timedelta(days=10), "decennially")
        assert result is None


# ── TestOrgScoping ────────────────────────────────────────────────────────────


class TestOrgScoping:
    async def test_org_cannot_see_other_org_deadlines(
        self, cl_client: AsyncClient, db: AsyncSession, cl_org2: Organization
    ) -> None:
        """Org1's list endpoint must not return org2's deadlines (seeded via DB)."""
        from datetime import date

        # Seed a deadline directly for org2 (bypassing HTTP client to avoid override conflict)
        org2_dl = ComplianceDeadline(
            org_id=CL_ORG2_ID,
            category="tax",
            title="Org2 Secret Deadline",
            due_date=date.today() + timedelta(days=90),
            status="upcoming",
        )
        db.add(org2_dl)
        await db.flush()

        # Org1 lists — should NOT see org2's deadline
        list_resp = await cl_client.get("/v1/compliance/deadlines")
        assert list_resp.status_code == 200
        ids = [item["id"] for item in list_resp.json()["items"]]
        assert str(org2_dl.id) not in ids

    async def test_org_cannot_get_other_org_deadline_by_id(
        self, cl_client: AsyncClient, db: AsyncSession, cl_org2: Organization
    ) -> None:
        """Direct GET for org2's deadline must return 404 when authenticated as org1."""
        from datetime import date

        # Seed org2's deadline directly
        org2_dl = ComplianceDeadline(
            org_id=CL_ORG2_ID,
            category="environmental",
            title="Org2 Restricted",
            due_date=date.today() + timedelta(days=60),
            status="upcoming",
        )
        db.add(org2_dl)
        await db.flush()

        # Org1 client tries to GET org2's deadline — service filters by org_id, returns 404
        get_resp = await cl_client.get(f"/v1/compliance/deadlines/{org2_dl.id}")
        assert get_resp.status_code == 404
