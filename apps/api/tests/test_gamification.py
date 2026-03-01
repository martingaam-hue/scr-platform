"""Tests for gamification — badges, quests, leaderboard."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_list_badges(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.get("/v1/gamification/badges")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_user_badges(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.get("/v1/gamification/user-badges")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_leaderboard(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.get("/v1/gamification/leaderboard")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_quests(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.get("/v1/gamification/quests")
    assert response.status_code == 200
