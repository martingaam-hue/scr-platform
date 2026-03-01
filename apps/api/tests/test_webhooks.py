"""Tests for webhook subscription, delivery, and validation."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ── Subscriptions ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_webhook_subscription(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.post(
        "/v1/webhooks/subscriptions",
        json={
            "url": "https://example.com/webhook",
            "events": ["signal_score.computed", "document.uploaded"],
            "secret": "test-secret-key-123",
        },
    )
    assert response.status_code in (200, 201), response.text
    data = response.json()
    assert "id" in data
    assert data["url"] == "https://example.com/webhook"


@pytest.mark.asyncio
async def test_list_webhook_subscriptions(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.get("/v1/webhooks/subscriptions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_subscription_invalid_url(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.post(
        "/v1/webhooks/subscriptions",
        json={"url": "not-a-valid-url", "events": ["test"]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_subscription_missing_events(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.post(
        "/v1/webhooks/subscriptions",
        json={"url": "https://example.com/webhook"},
    )
    # Either 201 (defaults applied) or 422 (events required)
    assert response.status_code in (200, 201, 422)


# ── Deliveries ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_webhook_deliveries(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.get("/v1/webhooks/deliveries")
    assert response.status_code == 200
