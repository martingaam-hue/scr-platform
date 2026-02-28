from collections.abc import AsyncGenerator
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
    messages: list[dict[str, Any]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Route a completion request to the appropriate LLM provider via litellm."""
    try:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "api_key": _get_api_key(model),
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        response = await litellm.acompletion(**kwargs)

        message = response.choices[0].message
        content = message.content or ""
        stop_reason = response.choices[0].finish_reason or "end_turn"

        # Extract tool calls if present
        tool_calls_raw = getattr(message, "tool_calls", None)
        tool_calls = None
        if tool_calls_raw:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls_raw
            ]

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
            stop_reason=stop_reason,
        )

        return {
            "content": content,
            "tool_calls": tool_calls,
            "stop_reason": stop_reason,
            "model_used": response.model or model,
            "usage": usage,
        }

    except Exception:
        logger.warning("primary_model_failed", model=model, fallback=settings.AI_FALLBACK_MODEL)
        # Fallback to secondary model (no tools on fallback)
        fallback_kwargs: dict[str, Any] = {
            "model": settings.AI_FALLBACK_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "api_key": settings.OPENAI_API_KEY,
        }
        response = await litellm.acompletion(**fallback_kwargs)

        content = response.choices[0].message.content or ""
        stop_reason = response.choices[0].finish_reason or "end_turn"
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        return {
            "content": content,
            "tool_calls": None,
            "stop_reason": stop_reason,
            "model_used": response.model or settings.AI_FALLBACK_MODEL,
            "usage": usage,
        }


async def route_completion_stream(
    model: str,
    messages: list[dict[str, Any]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncGenerator[str, None]:
    """Stream a completion token-by-token via litellm."""
    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=_get_api_key(model),
            stream=True,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
    except Exception:
        logger.warning("stream_primary_failed", model=model, fallback=settings.AI_FALLBACK_MODEL)
        response = await litellm.acompletion(
            model=settings.AI_FALLBACK_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.OPENAI_API_KEY,
            stream=True,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


def _get_api_key(model: str) -> str:
    """Resolve the API key for a given model."""
    if "claude" in model or "anthropic" in model:
        return settings.ANTHROPIC_API_KEY
    if "gpt" in model or "o1" in model:
        return settings.OPENAI_API_KEY
    # Default to OpenAI for unknown models
    return settings.OPENAI_API_KEY
