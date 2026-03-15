"""
Exercise 2.2: Prompt Chain for Research Reports
3-stage chain with validation gates, compared against single-prompt baseline.
"""

import anthropic
import json
from prompts import (
    STAGE_1_EXTRACT,
    STAGE_2_ANALYSE,
    STAGE_3_FORMAT,
    SINGLE_PROMPT_BASELINE,
)

client = anthropic.Anthropic()


# Raw test data ─────────────────────────────────────────────────

RAW_MARKET_DATA = [
    # Test 1: Rich data, clear signals
    """Bitcoin (BTC) - Market Update March 15 2026
    Current price: $84,200 (up 12.4% this week)
    24h volume: $48.2 billion (40% above 20-day average)
    Broke through $80,000 resistance on March 12
    RSI (14): 72 - approaching overbought territory
    50-day MA: $74,500 (price well above)
    200-day MA: $68,200 (price well above)
    Funding rates on perpetual futures: 0.05% (elevated but not extreme)
    Open interest up 22% week-over-week
    Fear & Greed Index: 78 (Greed)
    Notable: MicroStrategy announced additional $500M BTC purchase
    ETF inflows: $1.2B net this week across spot Bitcoin ETFs""",

    # Test 2: Mixed signals, less data
    """NVIDIA (NVDA) quick update:
    Stock at $890, down 3.2% today after being up 180% over past year.
    New AI chip (Blackwell Ultra) announced yesterday.
    Potential China export restrictions being discussed in Congress.
    P/E ratio at 65x forward earnings.
    Revenue grew 122% YoY last quarter to $22.1B.
    Competitors AMD and Intel both gaining AI chip market share.
    Insider selling: CEO sold $30M in shares last month.""",

    # Test 3: Sparse, messy data
    """heard gold is up again, around $2,340 per ounce. dollar index 
    dropped like 1.2% this week. real yields falling. some analyst 
    on twitter said $3,000 by year end. china and india central banks 
    still buying apparently. inflation data out next week.""",
]


# Helper functions ──────────────────────────────────────────────

def call_claude(system_prompt: str, user_message: str, max_tokens: int = 1024) -> str:
    """Make a single Claude API call and return the text response."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text.strip()


def parse_json_response(raw: str) -> dict | None:
    """Try to parse JSON from Claude's response, handling markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# Validation gates ──────────────────────────────────────────────

def validate_stage_1(data: dict | None) -> tuple[bool, str]:
    """Check Stage 1 output has required fields and reasonable content."""
    if data is None:
        return False, "Stage 1 returned invalid JSON"

    required = ["asset", "asset_class", "data_points"]
    missing = [f for f in required if f not in data]
    if missing:
        return False, f"Stage 1 missing fields: {missing}"

    if not data["data_points"]:
        return False, "Stage 1 extracted zero data points"

    if data["asset_class"] not in ["equity", "crypto", "forex", "commodity"]:
        return False, f"Stage 1 invalid asset_class: {data['asset_class']}"

    return True, f"Stage 1 passed — extracted {len(data['data_points'])} data points"


def validate_stage_2(data: dict | None) -> tuple[bool, str]:
    """Check Stage 2 output has required fields and analysis content."""
    if data is None:
        return False, "Stage 2 returned invalid JSON"

    required = ["asset", "trend", "key_insights", "sentiment", "risks"]
    missing = [f for f in required if f not in data]
    if missing:
        return False, f"Stage 2 missing fields: {missing}"

    if not data["key_insights"]:
        return False, "Stage 2 produced zero insights"

    sentiment = data.get("sentiment", {})
    if sentiment.get("rating") not in ["bullish", "bearish", "neutral"]:
        return False, f"Stage 2 invalid sentiment: {sentiment.get('rating')}"

    return True, f"Stage 2 passed — {len(data['key_insights'])} insights, sentiment: {sentiment.get('rating')}"


# The chain ─────────────────────────────────────────────────────

def run_chain(raw_data: str, label: str) -> str | None:
    """Run the full 3-stage chain with validation gates."""
    print(f"\n{'='*60}")
    print(f"CHAIN: {label}")
    print(f"{'='*60}")

    # Stage 1: Extract
    print("\n  Stage 1: Extracting data...")
    raw_extraction = call_claude(STAGE_1_EXTRACT, raw_data)
    extraction = parse_json_response(raw_extraction)
    passed, message = validate_stage_1(extraction)
    print(f"  Gate 1: {message}")
    if not passed:
        print("  ❌ Chain aborted at Stage 1")
        return None

    # Stage 2: Analyse
    print("\n  Stage 2: Analysing...")
    raw_analysis = call_claude(STAGE_2_ANALYSE, json.dumps(extraction, indent=2))
    analysis = parse_json_response(raw_analysis)
    passed, message = validate_stage_2(analysis)
    print(f"  Gate 2: {message}")
    if not passed:
        print("  ❌ Chain aborted at Stage 2")
        return None

    # Stage 3: Format
    print("\n  Stage 3: Formatting report...")
    report = call_claude(STAGE_3_FORMAT, json.dumps(analysis, indent=2))
    print(f"  ✅ Chain complete")

    return report


def run_single_prompt(raw_data: str, label: str) -> str:
    """Run the single-prompt baseline for comparison."""
    print(f"\n{'='*60}")
    print(f"SINGLE PROMPT: {label}")
    print(f"{'='*60}")

    report = call_claude(SINGLE_PROMPT_BASELINE, raw_data)
    print(f"  ✅ Complete")

    return report


# Main ──────────────────────────────────────────────────────────

def main():
    labels = [
        "Bitcoin — rich data, clear signals",
        "Nvidia — mixed signals, moderate data",
        "Gold — sparse, messy data",
    ]

    print("PROMPT CHAIN vs SINGLE PROMPT COMPARISON")
    print("="*60)

    for i, (raw_data, label) in enumerate(zip(RAW_MARKET_DATA, labels)):
        # Run the chain
        chain_report = run_chain(raw_data, label)
        if chain_report:
            print(f"\n--- CHAIN REPORT ---\n{chain_report}")

        # Run single prompt baseline
        single_report = run_single_prompt(raw_data, label)
        print(f"\n--- SINGLE PROMPT REPORT ---\n{single_report}")

        print(f"\n{'─'*60}")


if __name__ == "__main__":
    main()