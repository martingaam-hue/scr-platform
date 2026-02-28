"""Ralph AI — Pydantic schemas for conversations and messages."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", max_length=500)
    context_type: str = Field(default="general")
    context_entity_id: uuid.UUID | None = None


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=32000)


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    tool_calls: dict[str, Any] | None = None
    tool_results: dict[str, Any] | None = None
    model_used: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str
    context_type: str
    context_entity_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = []


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
