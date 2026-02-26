from app.services.token_tracker import estimate_cost


def test_estimate_cost_known_model() -> None:
    cost = estimate_cost("gpt-4o", input_tokens=1000, output_tokens=500)
    expected = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
    assert cost == round(expected, 6)


def test_estimate_cost_unknown_model_uses_default() -> None:
    cost = estimate_cost("some-future-model", input_tokens=1000, output_tokens=1000)
    expected = (1000 / 1_000_000) * 3.00 + (1000 / 1_000_000) * 15.00
    assert cost == round(expected, 6)


def test_estimate_cost_zero_tokens() -> None:
    cost = estimate_cost("gpt-4o", input_tokens=0, output_tokens=0)
    assert cost == 0.0
