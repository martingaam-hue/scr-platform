"""Token counting and cost estimation for LLM usage tracking."""

# Approximate pricing per 1M tokens (USD) — update as providers change pricing.
# These are estimates; actual billing comes from the provider.
MODEL_PRICING: dict[str, dict[str, float]] = {
    # Anthropic Claude
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
}

# Fallback pricing for unknown models
DEFAULT_PRICING = {"input": 3.00, "output": 15.00}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate the cost in USD for a given completion."""
    pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)
