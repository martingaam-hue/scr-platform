"""AI Completions router — full MODEL_ROUTING for all task types."""
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.auth import verify_gateway_key
from app.services.llm_router import route_completion
from app.services.rate_limiter import RateLimiter
from app.services.token_tracker import estimate_cost

logger = structlog.get_logger()
router = APIRouter()

# ── Model routing ─────────────────────────────────────────────────────────────

MODEL_ROUTING: dict[str, str] = {
    # Document intelligence
    "extract_kpis": "claude-sonnet-4-20250514",
    "extract_clauses": "claude-sonnet-4-20250514",
    "classify_document": "claude-haiku-4-5-20251001",
    "ocr_extract": "gpt-4o",
    "summarize_document": "claude-haiku-4-5-20251001",
    # Scoring
    "score_quality": "claude-sonnet-4-20250514",
    "score_deal_readiness": "claude-sonnet-4-20250514",
    "assess_risk": "claude-sonnet-4-20250514",
    "investor_signal_score": "claude-sonnet-4-20250514",
    "investor_score_improvement": "claude-sonnet-4-20250514",
    "live_score_enrichment": "claude-haiku-4-5-20251001",
    # Financial
    "suggest_assumptions": "claude-sonnet-4-20250514",
    "generate_valuation_narrative": "claude-sonnet-4-20250514",
    "find_comparables": "claude-sonnet-4-20250514",
    "capital_efficiency_report": "claude-sonnet-4-20250514",
    "market_opportunity_analysis": "claude-sonnet-4-20250514",
    # Matching
    "explain_match": "claude-haiku-4-5-20251001",
    "board_advisor_matching": "claude-haiku-4-5-20251001",
    # Reports & memos
    "generate_memo": "claude-sonnet-4-20250514",
    "generate_section": "claude-sonnet-4-20250514",
    "generate_narrative": "claude-sonnet-4-20250514",
    "business_plan_section": "claude-sonnet-4-20250514",
    # Conversational
    "chat": "claude-sonnet-4-20250514",
    "chat_with_tools": "claude-sonnet-4-20250514",
    # Compliance & ESG
    "classify_sfdr": "claude-sonnet-4-20250514",
    "check_taxonomy": "claude-sonnet-4-20250514",
    "extract_esg": "claude-haiku-4-5-20251001",
    # Legal
    "review_legal_doc": "claude-sonnet-4-20250514",
    "suggest_terms": "claude-sonnet-4-20250514",
    "legal_document_generation": "claude-sonnet-4-20250514",
    "legal_document_review": "claude-sonnet-4-20250514",
    # Advisory
    "persona_extraction": "claude-sonnet-4-20250514",
    "risk_mitigation_generation": "claude-sonnet-4-20250514",
    "risk_monitoring_analysis": "claude-haiku-4-5-20251001",
    "insurance_risk_impact": "claude-haiku-4-5-20251001",
    # Analysis
    "analysis": "claude-sonnet-4-20250514",
    "general": "claude-sonnet-4-20250514",
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
    "chat_with_tools": 4096,
    "general": 4096,
    "analysis": 4096,
}

# ── Schemas ──────────────────────────────────────────────────────────────────

class CompletionMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


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


# ── Endpoint ─────────────────────────────────────────────────────────────────

_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


@router.post("/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    _api_key: str = Depends(verify_gateway_key),
) -> CompletionResponse:
    model = _resolve_model(request.task_type, request.model)
    max_tokens = request.max_tokens or TOKEN_LIMITS.get(request.task_type, 4096)

    # Build messages list
    if request.messages:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
    else:
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        if request.prompt:
            messages.append({"role": "user", "content": request.prompt})
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
    )

    try:
        result = await route_completion(
            model=model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=max_tokens,
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
    return MODEL_ROUTING.get(task_type, settings.AI_DEFAULT_MODEL)
