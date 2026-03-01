"""Tests for gamification — badges, quests, leaderboard."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_my_badges(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    # User's own badges: GET /gamification/badges/my
    response = await authenticated_client.get("/v1/gamification/badges/my")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_project_badges(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    # Project badges require a project_id; nonexistent project returns empty list
    fake_id = "00000000-0000-0000-0000-000000000099"
    response = await authenticated_client.get(f"/v1/gamification/badges/project/{fake_id}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_leaderboard(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.get("/v1/gamification/leaderboard")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_progress_for_project(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    # Progress endpoint is read-only; returns zero data for a nonexistent project
    fake_id = "00000000-0000-0000-0000-000000000099"
    response = await authenticated_client.get(f"/v1/gamification/progress/{fake_id}")
    assert response.status_code == 200
