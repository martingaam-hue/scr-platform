from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.auth import verify_gateway_key
from app.services.llm_router import route_completion
from app.services.token_tracker import estimate_cost

logger = structlog.get_logger()

router = APIRouter()


class CompletionMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class CompletionRequest(BaseModel):
    messages: list[CompletionMessage]
    model: str | None = None
    task_type: str = Field(
        default="general",
        description="Task type for model routing: general, analysis, vision, embedding",
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    org_id: str
    user_id: str


class CompletionResponse(BaseModel):
    content: str
    model_used: str
    usage: dict[str, int]
    estimated_cost_usd: float


@router.post("/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    _api_key: str = Depends(verify_gateway_key),
) -> CompletionResponse:
    model = _resolve_model(request.task_type, request.model)

    logger.info(
        "completion_request",
        model=model,
        task_type=request.task_type,
        org_id=request.org_id,
        message_count=len(request.messages),
    )

    try:
        result = await route_completion(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as e:
        logger.error("completion_failed", model=model, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider error: {e}",
        ) from e

    usage: dict[str, Any] = result.get("usage", {})
    cost = estimate_cost(
        model=result.get("model_used", model),
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
    )

    return CompletionResponse(
        content=result["content"],
        model_used=result.get("model_used", model),
        usage=usage,
        estimated_cost_usd=cost,
    )


def _resolve_model(task_type: str, explicit_model: str | None) -> str:
    if explicit_model:
        return explicit_model

    model_map: dict[str, str] = {
        "general": settings.AI_DEFAULT_MODEL,
        "analysis": settings.AI_DEFAULT_MODEL,
        "vision": "gpt-4o",
        "embedding": settings.AI_EMBEDDING_MODEL,
    }
    return model_map.get(task_type, settings.AI_DEFAULT_MODEL)
