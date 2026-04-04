"""
Exercise 5.1: Tokenisation Explorer — Core Logic

Compares tokenisation between Claude (Anthropic API) and GPT-4 (tiktoken).
Shows token boundaries, counts, and patterns across different text types.
"""

import anthropic
import tiktoken


def get_claude_token_count(client: anthropic.Anthropic, text: str, model: str = "claude-sonnet-4-20250514") -> int:
    """
    Get token count from the Anthropic API.
    
    This uses Claude's actual tokeniser — the ground truth for cost calculations.
    The API only returns a count, not the individual tokens or boundaries.
    """
    response = client.messages.count_tokens(
        model=model,
        messages=[{"role": "user", "content": text}]
    )
    return response.input_tokens


def get_tiktoken_tokens(text: str, encoding_name: str = "cl100k_base") -> list[str]:
    """
    Tokenise text using tiktoken (OpenAI's tokeniser).
    
    cl100k_base is used by GPT-4 and GPT-3.5-turbo.
    o200k_base is used by GPT-4o and newer models.
    
    Unlike the Anthropic API, tiktoken runs locally and gives us
    the actual token boundaries — we can see exactly how text is split.
    """
    enc = tiktoken.get_encoding(encoding_name)
    token_ids = enc.encode(text)
    # Decode each token individually to see the boundaries
    tokens = [enc.decode([tid]) for tid in token_ids]
    return tokens


def get_tiktoken_token_count(text: str, encoding_name: str = "cl100k_base") -> int:
    """Get just the token count from tiktoken."""
    enc = tiktoken.get_encoding(encoding_name)
    return len(enc.encode(text))


def compare_tokenisation(client: anthropic.Anthropic, text: str, label: str) -> dict:
    """
    Compare tokenisation between Claude and GPT-4 for a given text.
    
    Returns a dict with counts and tiktoken's token boundaries.
    We can't get Claude's token boundaries (API only returns count),
    but comparing counts tells us about efficiency differences.
    """
    claude_count = get_claude_token_count(client, text)
    
    # GPT-4 (cl100k_base) and GPT-4o (o200k_base)
    gpt4_tokens = get_tiktoken_tokens(text, "cl100k_base")
    gpt4o_tokens = get_tiktoken_tokens(text, "o200k_base")
    
    return {
        "label": label,
        "text": text,
        "char_count": len(text),
        "word_count": len(text.split()),
        "claude_tokens": claude_count,
        "gpt4_tokens": len(gpt4_tokens),
        "gpt4_token_list": gpt4_tokens,
        "gpt4o_tokens": len(gpt4o_tokens),
        "gpt4o_token_list": gpt4o_tokens,
        # Efficiency: chars per token (higher = more efficient)
        "claude_chars_per_token": len(text) / claude_count if claude_count > 0 else 0,
        "gpt4_chars_per_token": len(text) / len(gpt4_tokens) if gpt4_tokens else 0,
        "gpt4o_chars_per_token": len(text) / len(gpt4o_tokens) if gpt4o_tokens else 0,
    }


# ─── Test Texts ─────────────────────────────────────────────────────

# These cover the 5+ required text types plus additional interesting cases.

TEST_TEXTS = {
    "prose": {
        "text": "The Federal Reserve announced a 25 basis point rate cut yesterday, bringing the target range to 4.25-4.50 percent. Markets responded positively, with the S&P 500 rising 1.2% in after-hours trading.",
        "label": "English Prose (Market Report)",
        "why": "Common content type for AW Analysis. Tests standard English tokenisation."
    },
    "code": {
        "text": '''def calculate_moving_average(prices: list[float], window: int = 20) -> list[float]:
    """Calculate simple moving average for a price series."""
    if len(prices) < window:
        return []
    return [sum(prices[i:i+window]) / window for i in range(len(prices) - window + 1)]''',
        "label": "Python Code",
        "why": "Code has lots of punctuation, indentation, and special chars. Often tokenises less efficiently than prose."
    },
    "numbers": {
        "text": "BTC: $84,521.30 (+2.34%) | ETH: $3,891.45 (-0.67%) | SOL: $178.23 (+5.12%) | Total Market Cap: $3.21T | 24h Volume: $142.8B | Fear & Greed Index: 72/100",
        "label": "Numbers and Financial Data",
        "why": "Numbers tokenise surprisingly poorly. Each digit group may split into multiple tokens. Important for cost estimation in financial pipelines."
    },
    "multilingual": {
        "text": "Bitcoin (ビットコイン) erreichte heute ein neues Allzeithoch. Le marché des cryptomonnaies est en pleine expansion. 加密货币市场持续增长。",
        "label": "Multilingual (Japanese, German, French, Chinese)",
        "why": "Non-English text is typically 2-3x more expensive per character. Critical for global applications."
    },
    "special_chars": {
        "text": "Alert ⚠️: BTC/USDT dropped below the 200-day MA 📉 | RSI(14) = 28.3 [oversold] | Support: $80,000 → $78,500 → $75,000 | Resistance: $85,000 ← $87,500 ← $90,000 | Pattern: H&S 🔴",
        "label": "Special Characters and Emoji",
        "why": "Emoji and special chars often get individual tokens. Tests tokeniser handling of unusual characters."
    },
    "json": {
        "text": '{"ticker": "AAPL", "price": 189.84, "change": -1.23, "volume": 52431876, "market_cap": "2.95T", "pe_ratio": 29.4, "52w_high": 199.62, "52w_low": 164.08, "sector": "Technology"}',
        "label": "JSON Structured Data",
        "why": "JSON is common in API responses and tool use. Tests how efficiently structured formats tokenise."
    },
    "repetitive": {
        "text": "Bitcoin Bitcoin Bitcoin price price price analysis analysis analysis market market market trend trend trend bullish bullish bullish signal signal signal confirmed confirmed confirmed",
        "label": "Repetitive Text",
        "why": "Tests whether common words get consistent single-token treatment. Repeated tokens should be efficient."
    },
    "urls_and_ids": {
        "text": "Source: https://api.coingecko.com/api/v3/coins/bitcoin?localization=false&tickers=false | Ref: TX-2024-03-29-BTC-84521-USD | Hash: 0x7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
        "label": "URLs, IDs, and Hashes",
        "why": "Technical identifiers with unusual character patterns. Often tokenise very poorly."
    },
}