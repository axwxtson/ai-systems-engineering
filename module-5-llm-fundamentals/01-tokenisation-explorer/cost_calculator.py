"""
Exercise 5.1: Cost Calculator

Compares the cost of processing text across different models,
using actual token counts from each tokeniser.

Prices as of March 2026 — check Anthropic and OpenAI pricing pages
for current rates. These change regularly.
"""


# ─── Pricing (per million tokens) ────────────────────────────────────
# Input pricing only — output pricing is higher but varies by model.
# Source: https://docs.anthropic.com/en/docs/about-claude/models
# Source: https://openai.com/pricing

MODEL_PRICING = {
    # Anthropic models (input price per 1M tokens)
    "claude-opus-4": {
        "provider": "Anthropic",
        "input_per_million": 15.00,
        "output_per_million": 75.00,
        "context_window": 200_000,
    },
    "claude-sonnet-4": {
        "provider": "Anthropic",
        "input_per_million": 3.00,
        "output_per_million": 15.00,
        "context_window": 200_000,
    },
    "claude-haiku-3.5": {
        "provider": "Anthropic",
        "input_per_million": 0.80,
        "output_per_million": 4.00,
        "context_window": 200_000,
    },
    # OpenAI models (input price per 1M tokens)
    "gpt-4o": {
        "provider": "OpenAI",
        "input_per_million": 2.50,
        "output_per_million": 10.00,
        "context_window": 128_000,
    },
    "gpt-4o-mini": {
        "provider": "OpenAI",
        "input_per_million": 0.15,
        "output_per_million": 0.60,
        "context_window": 128_000,
    },
    "gpt-4-turbo": {
        "provider": "OpenAI",
        "input_per_million": 10.00,
        "output_per_million": 30.00,
        "context_window": 128_000,
    },
}


def calculate_cost(token_count: int, model: str, direction: str = "input") -> float:
    """
    Calculate the cost for a given number of tokens.
    
    Args:
        token_count: Number of tokens
        model: Model name (key from MODEL_PRICING)
        direction: "input" or "output"
    
    Returns:
        Cost in USD
    """
    if model not in MODEL_PRICING:
        raise ValueError(f"Unknown model: {model}. Available: {list(MODEL_PRICING.keys())}")
    
    pricing = MODEL_PRICING[model]
    rate_key = f"{direction}_per_million"
    rate = pricing[rate_key]
    
    return (token_count / 1_000_000) * rate


def cost_comparison_table(claude_tokens: int, gpt4_tokens: int, gpt4o_tokens: int) -> list[dict]:
    """
    Generate a cost comparison across all models for given token counts.
    
    Uses the appropriate token count for each provider:
    - Anthropic models use claude_tokens
    - OpenAI cl100k models use gpt4_tokens
    - OpenAI o200k models use gpt4o_tokens
    """
    results = []
    
    for model, pricing in MODEL_PRICING.items():
        # Pick the right token count for the provider/tokeniser
        if pricing["provider"] == "Anthropic":
            tokens = claude_tokens
        elif model in ("gpt-4o", "gpt-4o-mini"):
            tokens = gpt4o_tokens  # These use o200k_base
        else:
            tokens = gpt4_tokens  # GPT-4-turbo uses cl100k_base
        
        input_cost = calculate_cost(tokens, model, "input")
        output_cost = calculate_cost(tokens, model, "output")
        
        results.append({
            "model": model,
            "provider": pricing["provider"],
            "tokens": tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "context_window": pricing["context_window"],
        })
    
    return results


def scale_to_target(token_count: int, target_tokens: int = 10_000) -> float:
    """
    Scale a sample token count to a target size.
    Returns the scaling factor.
    
    We measure token counts on sample texts, then extrapolate
    to a 10k token prompt to get meaningful cost comparisons.
    """
    if token_count == 0:
        return 0
    return target_tokens / token_count