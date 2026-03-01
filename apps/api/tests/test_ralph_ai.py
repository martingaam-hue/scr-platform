"""Tests for Ralph AI module — conversation management, tool definitions, context trimming."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import SAMPLE_ORG_ID, SAMPLE_USER_ID


# ── Conversation CRUD ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_conversation(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.post(
        "/v1/ralph/conversations",
        json={"context_type": "general"},
    )
    assert response.status_code in (200, 201), response.text
    data = response.json()
    assert "id" in data


@pytest.mark.asyncio
async def test_list_conversations(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    response = await authenticated_client.get("/v1/ralph/conversations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_conversation_not_found(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    fake_id = "00000000-0000-0000-0000-000000000099"
    response = await authenticated_client.get(f"/v1/ralph/conversations/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation_not_found(
    authenticated_client: AsyncClient, sample_user, db: AsyncSession
) -> None:
    fake_id = "00000000-0000-0000-0000-000000000099"
    response = await authenticated_client.delete(f"/v1/ralph/conversations/{fake_id}")
    assert response.status_code == 404


# ── Tool definitions ────────────────────────────────────────────────────────


def test_tool_definitions_structure() -> None:
    from app.modules.ralph_ai.tools import RALPH_TOOL_DEFINITIONS

    assert isinstance(RALPH_TOOL_DEFINITIONS, list)
    assert len(RALPH_TOOL_DEFINITIONS) > 0
    for tool in RALPH_TOOL_DEFINITIONS:
        # Each tool should have at minimum a name field (Anthropic format)
        assert isinstance(tool, dict)
        assert "name" in tool


# ── Context manager ─────────────────────────────────────────────────────────


def test_context_manager_exists() -> None:
    from app.modules.ralph_ai.context_manager import ContextWindowManager

    manager = ContextWindowManager(max_tokens=4096)
    assert manager.max_tokens == 4096


def test_context_trimming_keeps_last_message() -> None:
    from app.modules.ralph_ai.context_manager import ContextWindowManager

    manager = ContextWindowManager(max_tokens=50)
    messages = [
        {"role": "user", "content": "x" * 200},
        {"role": "assistant", "content": "y" * 200},
        {"role": "user", "content": "latest question"},
    ]
    trimmed = manager.trim_messages(messages)
    assert len(trimmed) > 0
    assert trimmed[-1]["content"] == "latest question"
