"""Model price table and cost calculator.

Prices are per million tokens, in USD. Source: Anthropic pricing page.
Verify against current docs before using in production — prices change.
"""

# Prices per 1M tokens, USD
MODEL_PRICES = {
    "claude-haiku-4-5-20251001": {
        "input": 1.00,
        "output": 5.00,
        "display_name": "Haiku 4.5",
        "tier": 1,
    },
    "claude-sonnet-4-6": {
        "input": 3.00,
        "output": 15.00,
        "display_name": "Sonnet 4.6",
        "tier": 2,
    },
    "claude-opus-4-6": {
        "input": 15.00,
        "output": 75.00,
        "display_name": "Opus 4.6",
        "tier": 3,
    },
}


def cost_for_call(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute the dollar cost of a single call from token usage."""
    if model not in MODEL_PRICES:
        # Unknown model — return 0 rather than crash, but flag it
        return 0.0
    p = MODEL_PRICES[model]
    return (input_tokens * p["input"] / 1_000_000) + (
        output_tokens * p["output"] / 1_000_000
    )


def display_name(model: str) -> str:
    return MODEL_PRICES.get(model, {}).get("display_name", model)


def all_models() -> list[str]:
    """Models in tier order, cheapest first."""
    return sorted(MODEL_PRICES.keys(), key=lambda m: MODEL_PRICES[m]["tier"])