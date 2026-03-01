"""AI cost calculation utilities.

Pricing as of March 2026 — update when Anthropic / OpenAI change rates.
All values are USD per 1 million tokens.
"""
from decimal import Decimal

# (input_usd_per_1m, output_usd_per_1m)
MODEL_COSTS: dict[str, tuple[Decimal, Decimal]] = {
    # Claude 4 family
    "claude-opus-4-6":                   (Decimal("15.00"), Decimal("75.00")),
    "claude-sonnet-4-6":                 (Decimal("3.00"),  Decimal("15.00")),
    "claude-haiku-4-5-20251001":         (Decimal("0.80"),  Decimal("4.00")),
    # Legacy Claude 3 (still in use)
    "claude-3-5-sonnet-20241022":        (Decimal("3.00"),  Decimal("15.00")),
    "claude-3-5-haiku-20241022":         (Decimal("0.80"),  Decimal("4.00")),
    "claude-3-opus-20240229":            (Decimal("15.00"), Decimal("75.00")),
    # OpenAI
    "gpt-4o":                            (Decimal("2.50"),  Decimal("10.00")),
    "gpt-4o-mini":                       (Decimal("0.15"),  Decimal("0.60")),
    "gpt-4-turbo":                       (Decimal("10.00"), Decimal("30.00")),
}

# Fallback for unknown models — conservative estimate
_DEFAULT_COST: tuple[Decimal, Decimal] = (Decimal("3.00"), Decimal("15.00"))


def calculate_cost(
    model: str | None,
    tokens_input: int,
    tokens_output: int,
) -> Decimal:
    """Return USD cost for a single LLM call.

    Uses exact token counts when available.  Never raises — returns
    Decimal("0") if inputs are nonsensical.
    """
    if not model or tokens_input < 0 or tokens_output < 0:
        return Decimal("0")

    # Normalise model name for lookup (strip suffixes like ":latest")
    key = model.split(":")[0].lower()
    in_rate, out_rate = MODEL_COSTS.get(key, _DEFAULT_COST)

    cost = (in_rate * tokens_input + out_rate * tokens_output) / Decimal("1_000_000")
    return cost.quantize(Decimal("0.000001"))
