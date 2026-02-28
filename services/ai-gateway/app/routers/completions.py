"""AI Completions router — full MODEL_ROUTING for all task types."""
import json
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.auth import verify_gateway_key
from app.services.llm_router import route_completion, route_completion_stream
from app.services.rate_limiter import RateLimiter
from app.services.token_tracker import estimate_cost

logger = structlog.get_logger()
router = APIRouter()

# ── Model routing ─────────────────────────────────────────────────────────────
# 5-provider routing: Anthropic, Google, xAI, DeepSeek, OpenAI
# Selected per task type based on Feb 2026 benchmark data, pricing, and strengths.
#
# TIER 1 — Claude Opus 4.6: highest quality, financial/legal stakes, client-facing
# TIER 2 — Gemini 3.1 Pro / Claude Sonnet 4.5: strong reasoning, professional writing
# TIER 3 — Grok 4.1 Fast / DeepSeek V3.2 / Gemini Flash: high-volume extraction
#
# ⚠️ GDPR: DeepSeek (deepseek/deepseek-chat) must NOT receive PII or document content.
#    Only route internal, template-driven, non-sensitive tasks to DeepSeek.
#    For EU-only processing, swap xai/grok-4.1-fast to eu-west-1 endpoint.

MODEL_ROUTING: dict[str, dict[str, str] | str] = {
    # ── TIER 1 — Claude Opus 4.6 (financial decisions, legal, client-facing) ──
    "score_quality": {
        "model": "anthropic/claude-opus-4-6",
        "fallback": "anthropic/claude-sonnet-4-5-20250929",
    },
    "assess_risk": {
        "model": "anthropic/claude-opus-4-6",
        "fallback": "anthropic/claude-sonnet-4-5-20250929",
    },
    "generate_memo": {
        "model": "anthropic/claude-opus-4-6",
        "fallback": "anthropic/claude-sonnet-4-5-20250929",
    },
    "chat_with_tools": {
        "model": "anthropic/claude-opus-4-6",
        "fallback": "anthropic/claude-sonnet-4-5-20250929",
    },
    "investor_signal_score": {
        "model": "anthropic/claude-opus-4-6",
        "fallback": "anthropic/claude-sonnet-4-5-20250929",
    },

    # ── TIER 2 — Gemini 3.1 Pro (legal/financial deep analysis, 1M context) ──
    "review_legal_doc": {
        "model": "google/gemini-3.1-pro",
        "fallback": "anthropic/claude-sonnet-4-5-20250929",
    },
    "review_contract": {
        "model": "google/gemini-3.1-pro",
        "fallback": "anthropic/claude-sonnet-4-5-20250929",
    },
    "analyze_transaction": {
        "model": "google/gemini-3.1-pro",
        "fallback": "openai/gpt-4o",
    },
    "find_comparables": {
        "model": "google/gemini-3.1-pro",
        "fallback": "openai/gpt-4o",
    },
    "legal_document_review": {
        "model": "google/gemini-3.1-pro",
        "fallback": "anthropic/claude-sonnet-4-5-20250929",
    },

    # ── TIER 2 — Claude Sonnet 4.5 (professional writing, LP reports) ──
    "generate_lp_narrative": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "generate_narrative": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "generate_section": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "business_plan_section": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "suggest_terms": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "legal_document_generation": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "score_deal_readiness": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "suggest_assumptions": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "generate_valuation_narrative": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "capital_efficiency_report": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "market_opportunity_analysis": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "generate_compliance_narrative": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "investor_score_improvement": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "risk_mitigation_generation": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "chat": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },

    # ── TIER 3 — Grok 4.1 Fast (high-volume extraction, 2M context, $/quality) ──
    "classify_document": {
        "model": "xai/grok-4.1-fast",
        "fallback": "google/gemini-2.5-flash-lite",
    },
    "extract_kpis": {
        "model": "xai/grok-4.1-fast",
        "fallback": "google/gemini-2.0-flash",
    },
    "extract_clauses": {
        "model": "xai/grok-4.1-fast",
        "fallback": "google/gemini-2.0-flash",
    },
    "parse_screener_query": {
        "model": "xai/grok-4.1-fast",
        "fallback": "openai/gpt-4o-mini",
    },
    "parse_nl_query": {
        "model": "xai/grok-4.1-fast",
        "fallback": "openai/gpt-4o-mini",
    },
    "auto_fill_checklist": {
        "model": "xai/grok-4.1-fast",
        "fallback": "deepseek/deepseek-chat",
    },
    "detect_redactable": {
        "model": "xai/grok-4.1-fast",
        "fallback": "openai/gpt-4o-mini",
    },
    "summarize_doc_changes": {
        "model": "xai/grok-4.1-fast",
        "fallback": "deepseek/deepseek-chat",
    },
    "board_advisor_matching": {
        "model": "xai/grok-4.1-fast",
        "fallback": "google/gemini-2.0-flash",
    },
    "explain_match": {
        "model": "xai/grok-4.1-fast",
        "fallback": "deepseek/deepseek-chat",
    },
    "insurance_risk_impact": {
        "model": "xai/grok-4.1-fast",
        "fallback": "deepseek/deepseek-chat",
    },
    "risk_monitoring_analysis": {
        "model": "xai/grok-4.1-fast",
        "fallback": "deepseek/deepseek-chat",
    },
    "live_score_enrichment": {
        "model": "xai/grok-4.1-fast",
        "fallback": "google/gemini-2.0-flash",
    },

    # ── TIER 3 — Gemini Flash (long-doc comparison, ESG, 1M context) ──
    "generate_esg_narrative": {
        "model": "google/gemini-2.0-flash",
        "fallback": "deepseek/deepseek-chat",
    },
    "extract_esg": {
        "model": "google/gemini-2.0-flash",
        "fallback": "xai/grok-4.1-fast",
    },
    "compare_documents": {
        "model": "google/gemini-2.0-flash",
        "fallback": "xai/grok-4.1-fast",
    },
    "summarize_document": {
        "model": "google/gemini-2.0-flash",
        "fallback": "xai/grok-4.1-fast",
    },
    "classify_sfdr": {
        "model": "google/gemini-2.0-flash",
        "fallback": "anthropic/claude-sonnet-4-5-20250929",
    },
    "check_taxonomy": {
        "model": "google/gemini-2.0-flash",
        "fallback": "anthropic/claude-sonnet-4-5-20250929",
    },

    # ── TIER 3 — DeepSeek V3.2 (non-sensitive internal tasks only) ──
    # ⚠️ DO NOT route tasks with PII or document content to DeepSeek.
    "generate_briefing": {
        "model": "deepseek/deepseek-chat",
        "fallback": "xai/grok-4.1-fast",
    },
    "generate_digest": {
        "model": "deepseek/deepseek-chat",
        "fallback": "xai/grok-4.1-fast",
    },
    "generate_digest_summary": {
        "model": "deepseek/deepseek-chat",
        "fallback": "xai/grok-4.1-fast",
    },
    "enrich_expert_note": {
        "model": "deepseek/deepseek-chat",
        "fallback": "xai/grok-4.1-fast",
    },
    "persona_extraction": {
        "model": "deepseek/deepseek-chat",
        "fallback": "xai/grok-4.1-fast",
    },
    "generate_persona_summary": {
        "model": "deepseek/deepseek-chat",
        "fallback": "xai/grok-4.1-fast",
    },

    # ── Special purpose ───────────────────────────────────────────────────────
    "ocr_extract": {
        "model": "openai/gpt-4o",
        "fallback": "anthropic/claude-sonnet-4-5-20250929",
    },

    # ── Legacy / catch-all ────────────────────────────────────────────────────
    "analysis": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
    "general": {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "fallback": "google/gemini-3.1-pro",
    },
}

# Max tokens per task type
TOKEN_LIMITS: dict[str, int] = {
    "extract_kpis": 2048,
    "extract_clauses": 4096,
    "classify_document": 512,
    "summarize_document": 1024,
    "score_quality": 2048,
    "score_deal_readiness": 2048,
    "assess_risk": 3000,
    "generate_memo": 8192,
    "generate_section": 4096,
    "business_plan_section": 6000,
    "legal_document_generation": 8000,
    "legal_document_review": 6000,
    "risk_mitigation_generation": 3000,
    "capital_efficiency_report": 3000,
    "market_opportunity_analysis": 4000,
    "chat": 4096,
    "chat_with_tools": 8192,
    "general": 4096,
    "analysis": 4096,
}

# ── Schemas ──────────────────────────────────────────────────────────────────

class CompletionMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant|tool)$")
    content: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    name: str | None = None


class CompletionRequest(BaseModel):
    # Legacy fields (keep backward compat)
    messages: list[CompletionMessage] | None = None
    # New-style fields
    prompt: str | None = None
    system: str | None = None
    # Routing
    model: str | None = None
    task_type: str = Field(default="general")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = None
    # Tool use
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    # Tenant
    org_id: str = ""
    user_id: str = ""
    # Priority for future queuing
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")
    org_tier: str = Field(default="professional", pattern="^(foundation|professional|enterprise)$")


class CompletionResponse(BaseModel):
    content: str
    model_used: str
    usage: dict[str, int]
    estimated_cost_usd: float
    tool_calls: list[dict[str, Any]] | None = None
    stop_reason: str = "end_turn"
    # Validation metadata (populated when task_type has a validation schema)
    validated_data: dict | None = None
    confidence: float | None = None
    confidence_level: str | None = None  # "high" | "medium" | "low" | "failed"
    validation_repairs: list[str] = []
    validation_warnings: list[str] = []


class StreamCompletionRequest(BaseModel):
    messages: list[CompletionMessage]
    task_type: str = Field(default="chat")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = None
    org_id: str = ""
    org_tier: str = Field(default="professional", pattern="^(foundation|professional|enterprise)$")


# ── Endpoint ─────────────────────────────────────────────────────────────────

_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def _build_messages(request: CompletionRequest | StreamCompletionRequest) -> list[dict[str, Any]]:
    """Build the messages list from request, handling both legacy and new-style fields."""
    if request.messages:
        result = []
        for m in request.messages:
            msg: dict[str, Any] = {"role": m.role}
            if m.content is not None:
                msg["content"] = m.content
            if m.tool_call_id is not None:
                msg["tool_call_id"] = m.tool_call_id
            if m.tool_calls is not None:
                msg["tool_calls"] = m.tool_calls
            if m.name is not None:
                msg["name"] = m.name
            result.append(msg)
        return result

    # Legacy prompt/system style
    messages: list[dict[str, Any]] = []
    if hasattr(request, "system") and request.system:  # type: ignore[union-attr]
        messages.append({"role": "system", "content": request.system})
    if hasattr(request, "prompt") and request.prompt:  # type: ignore[union-attr]
        messages.append({"role": "user", "content": request.prompt})
    return messages


@router.post("/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    _api_key: str = Depends(verify_gateway_key),
) -> CompletionResponse:
    model = _resolve_model(request.task_type, request.model)
    max_tokens = request.max_tokens or TOKEN_LIMITS.get(request.task_type, 4096)

    messages = _build_messages(request)
    if not messages:
        raise HTTPException(status_code=400, detail="Either messages or prompt is required")

    # Rate limit check (non-blocking on Redis errors)
    if request.org_id:
        limiter = get_rate_limiter()
        try:
            await limiter.check_and_increment(request.org_id, request.org_tier)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)) from e
        except Exception:
            pass  # Don't block on rate limiter errors

    logger.info(
        "completion_request",
        model=model,
        task_type=request.task_type,
        org_id=request.org_id,
        message_count=len(messages),
        has_tools=bool(request.tools),
    )

    try:
        result = await route_completion(
            model=model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=max_tokens,
            tools=request.tools,
            tool_choice=request.tool_choice,
            task_type=request.task_type,
            fallback_model=_get_fallback_model(request.task_type),
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

    logger.info(
        "completion_success",
        model=result.get("model_used"),
        task_type=request.task_type,
        org_id=request.org_id,
        cost_usd=cost,
        stop_reason=result.get("stop_reason"),
    )

    return CompletionResponse(
        content=result["content"],
        model_used=result.get("model_used", model),
        usage=usage,
        estimated_cost_usd=cost,
        tool_calls=result.get("tool_calls"),
        stop_reason=result.get("stop_reason", "end_turn"),
        validated_data=result.get("validated_data"),
        confidence=result.get("confidence"),
        confidence_level=result.get("confidence_level"),
        validation_repairs=result.get("validation_repairs", []),
        validation_warnings=result.get("validation_warnings", []),
    )


@router.post("/completions/stream")
async def stream_completion(
    request: StreamCompletionRequest,
    _api_key: str = Depends(verify_gateway_key),
) -> StreamingResponse:
    """Stream completion tokens via SSE. Returns data: {"token": "..."} events."""
    model = _resolve_model(request.task_type, None)
    max_tokens = request.max_tokens or TOKEN_LIMITS.get(request.task_type, 4096)

    messages = _build_messages(request)
    if not messages:
        raise HTTPException(status_code=400, detail="messages is required")

    if request.org_id:
        limiter = get_rate_limiter()
        try:
            await limiter.check_and_increment(request.org_id, request.org_tier)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)) from e
        except Exception:
            pass

    logger.info(
        "stream_request",
        model=model,
        task_type=request.task_type,
        org_id=request.org_id,
        message_count=len(messages),
    )

    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for token in route_completion_stream(
                model=model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=max_tokens,
            ):
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.error("stream_failed", error=str(e))
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _resolve_model(task_type: str, explicit_model: str | None) -> str:
    if explicit_model:
        return explicit_model
    routing = MODEL_ROUTING.get(task_type, settings.AI_DEFAULT_MODEL)
    if isinstance(routing, dict):
        return routing["model"]
    return routing  # type: ignore[return-value]


def _get_fallback_model(task_type: str) -> str:
    """Return the task-specific fallback model, or the global fallback."""
    routing = MODEL_ROUTING.get(task_type)
    if isinstance(routing, dict):
        return routing.get("fallback", settings.AI_FALLBACK_MODEL)
    return settings.AI_FALLBACK_MODEL


# ── Batch completions ─────────────────────────────────────────────────────────


class BatchCompletionRequest(BaseModel):
    task_type: str = Field(default="classify_document")
    contexts: list[dict[str, Any]]  # one context dict per item
    max_batch_size: int | None = None
    org_id: str = ""
    org_tier: str = Field(default="professional", pattern="^(foundation|professional|enterprise)$")


class BatchCompletionResponse(BaseModel):
    results: list[dict[str, Any]]
    task_type: str
    total: int
    batched: bool


class _LLMClientAdapter:
    """Adapts route_completion to the TaskBatcher.llm.complete() interface."""

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        task_type: str | None = None,
    ) -> "_CompletionResult":
        result = await route_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            task_type=task_type,
        )
        return _CompletionResult(
            content=result["content"],
            validated_data=result.get("validated_data"),
        )


class _CompletionResult:
    def __init__(self, content: str, validated_data: dict[str, Any] | None = None) -> None:
        self.content = content
        self.validated_data = validated_data


@router.post("/completions/batch", response_model=BatchCompletionResponse)
async def batch_completions(
    request: BatchCompletionRequest,
    _api_key: str = Depends(verify_gateway_key),
) -> BatchCompletionResponse:
    """Batch multiple same-type tasks into efficient grouped LLM calls.

    Batchable task types: classify_document, extract_kpis, summarize_document,
    explain_match, insurance_risk_impact, risk_monitoring_analysis.
    Non-batchable tasks are processed individually.
    """
    from app.task_batcher import BATCHABLE_TASKS, TaskBatcher

    if not request.contexts:
        return BatchCompletionResponse(
            results=[], task_type=request.task_type, total=0, batched=False
        )

    if request.org_id:
        limiter = get_rate_limiter()
        try:
            await limiter.check_and_increment(request.org_id, request.org_tier)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)) from e
        except Exception:
            pass

    llm_adapter = _LLMClientAdapter()
    batcher = TaskBatcher(llm_client=llm_adapter)

    is_batched = request.task_type in BATCHABLE_TASKS and len(request.contexts) > 1

    logger.info(
        "batch_completion_request",
        task_type=request.task_type,
        count=len(request.contexts),
        batched=is_batched,
        org_id=request.org_id,
    )

    try:
        results = await batcher.batch_complete(
            task_type=request.task_type,
            contexts=request.contexts,
            max_batch_size=request.max_batch_size,
        )
    except Exception as e:
        logger.error("batch_completion_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Batch processing error: {e}",
        ) from e

    return BatchCompletionResponse(
        results=results,
        task_type=request.task_type,
        total=len(results),
        batched=is_batched,
    )
