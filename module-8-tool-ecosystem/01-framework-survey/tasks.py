"""
tasks.py — shared task spec + test queries for the framework survey.

The task is deliberately simple so the focus stays on HOW each framework
models it, not on the problem itself. A market-analysis agent with two
tools — get_price and search_knowledge_base — that answers user questions
about crypto, equities, forex, and commodities.

Every framework implementation (real or sketched) solves the same task
with the same tools and the same test queries, so the comparison is apples
to apples.
"""

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Task specification — the shared contract every implementation satisfies.
# ---------------------------------------------------------------------------

TASK_NAME = "aw_analysis_mini"

SYSTEM_PROMPT = """\
You are AW Analysis, a cross-asset market intelligence assistant.
You cover equities, crypto, forex, and commodities.

You have two tools available:
  - get_price(ticker): returns the current price and 24h change for a ticker
  - search_knowledge_base(query): returns short context snippets about
    recent market events

Rules:
  - Use tools when you need a price or recent context. Do not guess prices.
  - Keep responses under 120 words unless the user asks for detail.
  - If the user asks for investment advice ("should I buy?"), decline and
    explain why — you are an analysis assistant, not an advisor.
  - Use British English spelling in all responses.
"""

# ---------------------------------------------------------------------------
# Tool definitions — the shared tool schema.
# These JSON Schema definitions are what the SDK baseline uses directly,
# and what the framework sketches wrap in their own abstractions.
# ---------------------------------------------------------------------------

TOOLS_SCHEMA = [
    {
        "name": "get_price",
        "description": (
            "Fetch the current price and 24h change for a ticker. "
            "Use for live price queries."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The ticker symbol, e.g. BTC, AAPL, EURUSD, GOLD",
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "search_knowledge_base",
        "description": (
            "Search the AW Analysis knowledge base for recent market events, "
            "news, and context. Returns short snippets."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
            },
            "required": ["query"],
        },
    },
]


# ---------------------------------------------------------------------------
# Mock tool implementations — deterministic, no external dependencies.
# Real AW Analysis would call a market data API and a real retriever.
# For the survey we keep them canned so every run is reproducible and the
# comparison isn't muddied by network variance.
# ---------------------------------------------------------------------------

MOCK_PRICES = {
    "BTC": {"price": 92_450.12, "change_24h_pct": 2.4},
    "ETH": {"price": 3_280.55, "change_24h_pct": -1.1},
    "AAPL": {"price": 241.30, "change_24h_pct": 0.6},
    "TSLA": {"price": 358.90, "change_24h_pct": -2.2},
    "EURUSD": {"price": 1.0847, "change_24h_pct": 0.1},
    "GOLD": {"price": 3_120.50, "change_24h_pct": 0.8},
}

MOCK_KB = {
    "ethereum etf": (
        "April 2026: US SEC approved spot Ethereum ETF applications from "
        "BlackRock, Fidelity, and Grayscale. Trading begins May 1."
    ),
    "bitcoin halving": (
        "The 2024 Bitcoin halving reduced block rewards to 3.125 BTC. "
        "The next halving is expected in 2028."
    ),
    "fed rate": (
        "March 2026 FOMC: Federal Reserve held rates at 4.25–4.50%. "
        "Powell signalled patience on further cuts pending inflation data."
    ),
    "aapl earnings": (
        "Apple Q2 2026 earnings beat on services revenue, missed on iPhone "
        "unit sales. Vision Pro contribution remains below 2% of revenue."
    ),
    "eurusd": (
        "April 2026: EUR/USD trading in 1.08–1.09 range as ECB and Fed "
        "maintain divergent rate paths."
    ),
    "gold": (
        "Gold broke above $3,000/oz in early 2026 on central bank buying "
        "and sustained geopolitical risk premium."
    ),
}


def execute_get_price(ticker: str) -> dict:
    """Execute the get_price tool — returns canned data or an error."""
    ticker_upper = ticker.upper().strip()
    if ticker_upper in MOCK_PRICES:
        data = MOCK_PRICES[ticker_upper]
        return {
            "ticker": ticker_upper,
            "price": data["price"],
            "change_24h_pct": data["change_24h_pct"],
            "currency": "USD",
        }
    return {"error": f"Unknown ticker: {ticker}"}


def execute_search_knowledge_base(query: str) -> dict:
    """Execute the search_knowledge_base tool — returns matching snippets."""
    q = query.lower().strip()
    matches = []
    for key, snippet in MOCK_KB.items():
        if any(word in q for word in key.split()):
            matches.append({"topic": key, "snippet": snippet})
    if not matches:
        return {"results": [], "note": "No relevant entries found."}
    return {"results": matches[:3]}


def execute_tool(name: str, arguments: dict) -> dict:
    """Dispatcher — matches tool name to implementation."""
    if name == "get_price":
        return execute_get_price(arguments.get("ticker", ""))
    if name == "search_knowledge_base":
        return execute_search_knowledge_base(arguments.get("query", ""))
    return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Test queries — five cases covering different interaction patterns.
# ---------------------------------------------------------------------------

@dataclass
class TestQuery:
    qid: str
    query: str
    expected_pattern: str  # what the agent should roughly do
    difficulty: str        # easy | medium | hard


TEST_QUERIES: list[TestQuery] = [
    TestQuery(
        qid="q1_price_only",
        query="What's the current price of Bitcoin?",
        expected_pattern="single get_price call, short summary",
        difficulty="easy",
    ),
    TestQuery(
        qid="q2_kb_only",
        query="What happened with the Ethereum ETF approval?",
        expected_pattern="single search_knowledge_base call, short summary",
        difficulty="easy",
    ),
    TestQuery(
        qid="q3_multi_tool",
        query=(
            "Give me the current Ethereum price and explain what's been "
            "happening with the ETH ETF recently."
        ),
        expected_pattern="get_price + search_knowledge_base, combined answer",
        difficulty="medium",
    ),
    TestQuery(
        qid="q4_refusal",
        query="Should I buy Bitcoin right now? Give me a yes or no.",
        expected_pattern=(
            "refusal — explain the assistant is analysis, not advisory, "
            "no tool calls needed"
        ),
        difficulty="medium",
    ),
    TestQuery(
        qid="q5_multi_hop",
        query=(
            "Compare Apple and Tesla on price action today, then tell me "
            "what the most recent AAPL earnings report showed."
        ),
        expected_pattern=(
            "two get_price calls (AAPL + TSLA), one search_knowledge_base "
            "call, synthesised comparison"
        ),
        difficulty="hard",
    ),
]