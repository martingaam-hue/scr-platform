from collections.abc import AsyncGenerator
from typing import Any

import litellm
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.validation import AIOutputValidator, ConfidenceLevel

logger = structlog.get_logger()

litellm.set_verbose = False

_validator = AIOutputValidator()


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
    task_type: str | None = None,
    fallback_model: str | None = None,
) -> dict[str, Any]:
    """Route a completion request to the appropriate LLM provider via litellm.

    When task_type is provided, the response is validated and repaired.
    On a clean JSON parse failure, a single retry is attempted with corrective
    instructions before the result is returned to the caller.
    The fallback_model overrides settings.AI_FALLBACK_MODEL on primary failure.
    """
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

        # ── Validation + optional retry ───────────────────────────────────────
        validation = None
        if task_type:
            validation = _validator.validate(task_type, content)

            # Auto-retry once if JSON parse completely failed (and no tools involved)
            if (
                validation.confidence_level == ConfidenceLevel.FAILED
                and validation.error
                and "parse JSON" in validation.error
                and not tools
            ):
                retry_messages = messages + [
                    {"role": "assistant", "content": content},
                    {
                        "role": "user",
                        "content": (
                            "Your response could not be parsed as JSON. "
                            "Please respond with ONLY a valid JSON object, "
                            "no markdown fences, no explanation."
                        ),
                    },
                ]
                retry_response = await litellm.acompletion(
                    model=model,
                    messages=retry_messages,
                    temperature=0.1,
                    max_tokens=max_tokens,
                    api_key=_get_api_key(model),
                )
                content = retry_response.choices[0].message.content or ""
                validation = _validator.validate(task_type, content)
                # Accumulate token counts
                usage["prompt_tokens"] += retry_response.usage.prompt_tokens
                usage["completion_tokens"] += retry_response.usage.completion_tokens
                usage["total_tokens"] += retry_response.usage.total_tokens

        logger.info(
            "completion_success",
            model=model,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            stop_reason=stop_reason,
            confidence=validation.confidence if validation else None,
        )

        return {
            "content": content,
            "tool_calls": tool_calls,
            "stop_reason": stop_reason,
            "model_used": response.model or model,
            "usage": usage,
            # Validation fields (None when task_type not provided)
            "validated_data": validation.data if validation else None,
            "confidence": validation.confidence if validation else None,
            "confidence_level": validation.confidence_level.value if validation else None,
            "validation_repairs": validation.repairs_applied if validation else [],
            "validation_warnings": validation.warnings if validation else [],
        }

    except Exception:
        _fallback = fallback_model or settings.AI_FALLBACK_MODEL
        logger.warning("primary_model_failed", model=model, fallback=_fallback)
        fallback_kwargs: dict[str, Any] = {
            "model": _fallback,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "api_key": _get_api_key(_fallback),
        }
        response = await litellm.acompletion(**fallback_kwargs)

        content = response.choices[0].message.content or ""
        stop_reason = response.choices[0].finish_reason or "end_turn"
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        validation = None
        if task_type:
            validation = _validator.validate(task_type, content)

        return {
            "content": content,
            "tool_calls": None,
            "stop_reason": stop_reason,
            "model_used": response.model or settings.AI_FALLBACK_MODEL,
            "usage": usage,
            "validated_data": validation.data if validation else None,
            "confidence": validation.confidence if validation else None,
            "confidence_level": validation.confidence_level.value if validation else None,
            "validation_repairs": validation.repairs_applied if validation else [],
            "validation_warnings": validation.warnings if validation else [],
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
            api_key=_get_api_key(settings.AI_FALLBACK_MODEL),
            stream=True,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


def _get_api_key(model: str) -> str:
    """Return the API key for the given model/provider string."""
    m = model.lower()
    if "claude" in m or "anthropic" in m:
        return settings.ANTHROPIC_API_KEY
    if "gemini" in m or "google" in m:
        return settings.GOOGLE_API_KEY
    if "grok" in m or "xai" in m:
        return settings.XAI_API_KEY
    if "deepseek" in m:
        return settings.DEEPSEEK_API_KEY
    # OpenAI (gpt, o1, whisper, text-embedding, etc.)
    return settings.OPENAI_API_KEY
