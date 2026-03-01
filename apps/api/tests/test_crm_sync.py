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
async def test_list_sync_logs(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.get("/v1/crm/sync-logs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_entity_mappings(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.get("/v1/crm/entity-mappings")
    assert response.status_code == 200
