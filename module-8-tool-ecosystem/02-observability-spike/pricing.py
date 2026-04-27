"""
pricing.py — Model price table and cost calculator.

Same pattern as Module 7's pricing.py. Prices are per million tokens.
"""

from __future__ import annotations


# Prices per million tokens (USD) — April 2026 Anthropic pricing
MODEL_PRICES: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001": {
        "input": 1.00,
        "output": 5.00,
    },
    "claude-sonnet-4-20250514": {
        "input": 3.00,
        "output": 15.00,
    },
    "claude-opus-4-20250514": {
        "input": 15.00,
        "output": 75.00,
    },
}

# Short aliases for cleaner routing output
MODEL_ALIASES: dict[str, str] = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-20250514",
    "opus": "claude-opus-4-20250514",
}


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute cost in USD for a single API call."""
    prices = MODEL_PRICES.get(model)
    if not prices:
        return 0.0
    input_cost = (input_tokens / 1_000_000) * prices["input"]
    output_cost = (output_tokens / 1_000_000) * prices["output"]
    return input_cost + output_cost