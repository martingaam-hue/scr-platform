from typing import Any

import litellm
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = structlog.get_logger()

# Configure litellm
litellm.set_verbose = False


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
async def route_completion(
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Route a completion request to the appropriate LLM provider via litellm."""
    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=_get_api_key(model),
        )

        content = response.choices[0].message.content or ""
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        logger.info(
            "completion_success",
            model=model,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
        )

        return {
            "content": content,
            "model_used": response.model or model,
            "usage": usage,
        }

    except Exception:
        logger.warning("primary_model_failed", model=model, fallback=settings.AI_FALLBACK_MODEL)
        # Fallback to secondary model
        response = await litellm.acompletion(
            model=settings.AI_FALLBACK_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.OPENAI_API_KEY,
        )

        content = response.choices[0].message.content or ""
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        return {
            "content": content,
            "model_used": response.model or settings.AI_FALLBACK_MODEL,
            "usage": usage,
        }


def _get_api_key(model: str) -> str:
    """Resolve the API key for a given model."""
    if "claude" in model or "anthropic" in model:
        return settings.ANTHROPIC_API_KEY
    if "gpt" in model or "o1" in model:
        return settings.OPENAI_API_KEY
    # Default to OpenAI for unknown models
    return settings.OPENAI_API_KEY
