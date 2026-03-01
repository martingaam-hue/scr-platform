"""Tests for auth router endpoints."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.auth.dependencies import get_current_user
from app.main import app
from app.models.enums import UserRole
from app.schemas.auth import CurrentUser
from tests.conftest import SAMPLE_CLERK_ID, SAMPLE_ORG_ID, SAMPLE_USER_ID


@pytest.mark.anyio
class TestWebhookEndpoint:
    async def test_webhook_without_signature_returns_error(self, client: AsyncClient):
        """Webhook without valid svix headers should fail (400 or 500)."""
        response = await client.post(
            "/v1/auth/webhook",
            json={"type": "user.created", "data": {}},
        )
        # 400 if secret is set (bad signature), 500 if secret is empty
        assert response.status_code >= 400

    async def test_webhook_with_unknown_event_returns_200(self, client: AsyncClient):
        """Unknown events should be accepted but ignored."""
        with patch(
            "app.auth.router.verify_webhook_signature",
            new_callable=AsyncMock,
            return_value={"type": "unknown.event", "data": {}},
        ):
            response = await client.post(
                "/v1/auth/webhook",
                json={},
                headers={
                    "svix-id": "test",
                    "svix-timestamp": "12345",
                    "svix-signature": "v1,test",
                },
            )
            assert response.status_code == 200
            assert response.json()["status"] == "ok"


@pytest.mark.anyio
class TestMeEndpoint:
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.get("/v1/auth/me")
        assert response.status_code in (401, 403)


@pytest.mark.anyio
class TestPermissionsEndpoint:
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        response = await client.get("/v1/auth/permissions")
        assert response.status_code in (401, 403)
