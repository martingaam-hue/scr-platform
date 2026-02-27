"""Tests for Clerk webhook handlers."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk_webhook import (
    handle_organization_created,
    handle_user_created,
    handle_user_deleted,
    handle_user_updated,
)
from app.models.core import Organization, User
from app.models.enums import OrgType, UserRole


def _uid() -> str:
    """Generate a short unique suffix for test data to avoid collisions."""
    return uuid.uuid4().hex[:8]


@pytest.mark.anyio
class TestHandleUserCreated:
    async def test_creates_user_and_default_org(self, db: AsyncSession):
        data = {
            "id": "user_test_new_123",
            "email_addresses": [{"email_address": "newuser@example.com"}],
            "first_name": "New",
            "last_name": "User",
            "image_url": "https://example.com/avatar.png",
            "organization_memberships": [],
        }
        await handle_user_created(data, db)

        result = await db.execute(
            select(User).where(User.external_auth_id == "user_test_new_123")
        )
        user = result.scalar_one()
        assert user.email == "newuser@example.com"
        assert user.full_name == "New User"
        assert user.avatar_url == "https://example.com/avatar.png"
        assert user.role == UserRole.ADMIN  # first user in org
        assert user.is_active is True

    async def test_creates_user_with_existing_org(self, db: AsyncSession):
        suffix = _uid()
        slug = f"existing-org-{suffix}"
        org = Organization(name="Existing Org", slug=slug, type=OrgType.ALLY)
        db.add(org)
        await db.flush()

        clerk_id = f"user_test_org_member_{suffix}"
        data = {
            "id": clerk_id,
            "email_addresses": [{"email_address": f"member-{suffix}@example.com"}],
            "first_name": "Org",
            "last_name": "Member",
            "organization_memberships": [
                {
                    "organization": {
                        "id": f"clerk_org_{suffix}",
                        "name": "Existing Org",
                        "slug": slug,
                    }
                }
            ],
        }
        await handle_user_created(data, db)

        result = await db.execute(
            select(User).where(User.external_auth_id == clerk_id)
        )
        user = result.scalar_one()
        assert user.org_id == org.id

    async def test_idempotent_duplicate_event(self, db: AsyncSession):
        data = {
            "id": "user_test_idempotent",
            "email_addresses": [{"email_address": "idem@example.com"}],
            "first_name": "Idem",
            "last_name": "Potent",
            "organization_memberships": [],
        }
        await handle_user_created(data, db)
        await handle_user_created(data, db)  # second call should be no-op

        result = await db.execute(
            select(User).where(User.external_auth_id == "user_test_idempotent")
        )
        users = result.scalars().all()
        assert len(users) == 1


@pytest.mark.anyio
class TestHandleUserUpdated:
    async def test_updates_user_fields(self, db: AsyncSession):
        suffix = _uid()
        org = Organization(name="Update Org", slug=f"update-org-{suffix}", type=OrgType.ALLY)
        db.add(org)
        await db.flush()

        clerk_id = f"user_test_update_{suffix}"
        user = User(
            org_id=org.id,
            email=f"old-{suffix}@example.com",
            full_name="Old Name",
            role=UserRole.VIEWER,
            external_auth_id=clerk_id,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        data = {
            "id": clerk_id,
            "email_addresses": [{"email_address": f"new-{suffix}@example.com"}],
            "first_name": "New",
            "last_name": "Name",
            "image_url": "https://example.com/new-avatar.png",
        }
        await handle_user_updated(data, db)

        await db.refresh(user)
        assert user.email == f"new-{suffix}@example.com"
        assert user.full_name == "New Name"
        assert user.avatar_url == "https://example.com/new-avatar.png"

    async def test_ignores_unknown_user(self, db: AsyncSession):
        data = {
            "id": "user_nonexistent",
            "email_addresses": [{"email_address": "ghost@example.com"}],
            "first_name": "Ghost",
            "last_name": "User",
        }
        # Should not raise
        await handle_user_updated(data, db)


@pytest.mark.anyio
class TestHandleUserDeleted:
    async def test_soft_deletes_user(self, db: AsyncSession):
        suffix = _uid()
        org = Organization(name="Del Org", slug=f"del-org-{suffix}", type=OrgType.ALLY)
        db.add(org)
        await db.flush()

        clerk_id = f"user_test_delete_{suffix}"
        user = User(
            org_id=org.id,
            email=f"delete-{suffix}@example.com",
            full_name="Delete Me",
            role=UserRole.VIEWER,
            external_auth_id=clerk_id,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        await handle_user_deleted({"id": clerk_id}, db)

        await db.refresh(user)
        assert user.is_active is False
        assert user.is_deleted is True

    async def test_ignores_unknown_user(self, db: AsyncSession):
        await handle_user_deleted({"id": "user_nonexistent"}, db)


@pytest.mark.anyio
class TestHandleOrganizationCreated:
    async def test_creates_org(self, db: AsyncSession):
        suffix = _uid()
        slug = f"new-org-{suffix}"
        data = {
            "id": f"clerk_org_new_{suffix}",
            "name": "New Org",
            "slug": slug,
        }
        await handle_organization_created(data, db)

        result = await db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        org = result.scalar_one()
        assert org.name == "New Org"
        assert org.type == OrgType.ALLY

    async def test_idempotent_duplicate_org(self, db: AsyncSession):
        suffix = _uid()
        slug = f"dup-org-{suffix}"
        data = {
            "id": f"clerk_org_dup_{suffix}",
            "name": "Dup Org",
            "slug": slug,
        }
        await handle_organization_created(data, db)
        await handle_organization_created(data, db)

        result = await db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        orgs = result.scalars().all()
        assert len(orgs) == 1
