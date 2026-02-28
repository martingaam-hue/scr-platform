"""Embeddings endpoint."""
from typing import Any

import litellm
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.services.auth import verify_gateway_key
from app.services.token_tracker import estimate_cost

logger = structlog.get_logger()
router = APIRouter()


class EmbedRequest(BaseModel):
    input: str | list[str]
    model: str | None = None
    org_id: str = ""


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    model_used: str
    usage: dict[str, int]
    estimated_cost_usd: float


@router.post("/embed", response_model=EmbedResponse)
async def create_embedding(
    request: EmbedRequest,
    _api_key: str = Depends(verify_gateway_key),
) -> EmbedResponse:
    model = request.model or settings.AI_EMBEDDING_MODEL
    texts = [request.input] if isinstance(request.input, str) else request.input

    logger.info("embed_request", model=model, texts=len(texts), org_id=request.org_id)

    try:
        response = await litellm.aembedding(
            model=model,
            input=texts,
            api_key=settings.OPENAI_API_KEY,
        )
    except Exception as e:
        logger.error("embedding_failed", model=model, error=str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Embedding error: {e}") from e

    embeddings = [item["embedding"] for item in response.data]
    usage: dict[str, Any] = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": 0,
        "total_tokens": response.usage.total_tokens,
    }
    cost = estimate_cost(model=model, input_tokens=usage["prompt_tokens"], output_tokens=0)

    return EmbedResponse(embeddings=embeddings, model_used=model, usage=usage, estimated_cost_usd=cost)
