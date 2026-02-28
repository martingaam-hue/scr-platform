"""Ralph AI — FastAPI router (6 endpoints: 5 REST + 1 SSE stream)."""

import json
import uuid
from collections.abc import AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.schemas.auth import CurrentUser
from app.modules.ralph_ai import service
from app.modules.ralph_ai.agent import RalphAgent
from app.modules.ralph_ai.schemas import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    SendMessageResponse,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/ralph", tags=["ralph-ai"])

_agent = RalphAgent()


# ── Conversation CRUD ─────────────────────────────────────────────────────────

@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Create a new Ralph AI conversation."""
    conversation = await service.create_conversation(
        db, current_user.org_id, current_user.user_id, body
    )
    return ConversationResponse.model_validate(conversation)


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationResponse]:
    """List all conversations for the current user."""
    conversations = await service.list_conversations(
        db, current_user.org_id, current_user.user_id
    )
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetailResponse:
    """Get a conversation with its full message history."""
    conversation = await service.get_conversation(db, conversation_id, current_user.org_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    messages = sorted(conversation.messages, key=lambda m: m.created_at)
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        context_type=conversation.context_type.value,
        context_entity_id=conversation.context_entity_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a conversation."""
    deleted = await service.delete_conversation(db, conversation_id, current_user.org_id, current_user.user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


# ── Messaging ─────────────────────────────────────────────────────────────────

@router.post("/conversations/{conversation_id}/message", response_model=SendMessageResponse)
async def send_message(
    conversation_id: uuid.UUID,
    body: MessageCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SendMessageResponse:
    """Send a message and receive the full agent response (sync)."""
    conversation = await service.get_conversation(db, conversation_id, current_user.org_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    try:
        user_msg, assistant_msg = await _agent.process_message(
            db=db,
            conversation_id=conversation_id,
            user_content=body.content,
            org_id=current_user.org_id,
            user_id=current_user.user_id,
        )
    except Exception as e:
        logger.error("ralph_send_message_error", error=str(e), conversation_id=str(conversation_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message",
        ) from e

    return SendMessageResponse(
        user_message=MessageResponse.model_validate(user_msg),
        assistant_message=MessageResponse.model_validate(assistant_msg),
    )


@router.post("/conversations/{conversation_id}/stream")
async def stream_message(
    conversation_id: uuid.UUID,
    body: MessageCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Send a message and stream the response via SSE."""
    conversation = await service.get_conversation(db, conversation_id, current_user.org_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for event in _agent.process_message_stream(
                db=db,
                conversation_id=conversation_id,
                user_content=body.content,
                org_id=current_user.org_id,
                user_id=current_user.user_id,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error("ralph_stream_error", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
