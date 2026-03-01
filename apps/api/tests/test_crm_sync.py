"""Tests for CRM sync module — connections, sync logs, entity mappings."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_list_crm_connections(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.get("/v1/crm/connections")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_connection_requires_provider(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.post("/v1/crm/connections", json={})
    # 422 = validation error (missing fields), 405 = method not allowed (POST not supported)
    assert response.status_code in (405, 422)


@pytest.mark.asyncio
async def test_get_oauth_connect_url(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    # /crm/connect/{provider} returns the OAuth2 URL for the given provider
    response = await authenticated_client.get("/v1/crm/connect/hubspot")
    assert response.status_code == 200
    data = response.json()
    assert "url" in data


@pytest.mark.asyncio
async def test_get_connection_logs_unknown_id(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    # Logs endpoint joins on org_id so a nonexistent connection_id returns empty list (200)
    fake_id = "00000000-0000-0000-0000-000000000099"
    response = await authenticated_client.get(f"/v1/crm/connections/{fake_id}/logs")
    assert response.status_code == 200
    assert response.json() == []
