"""
tools.py — AW Analysis agent tools.

This is Exercise 3.3's tools.py with two new RAG-powered tools added:
  - search_knowledge_base: Search reference documents (market reports, research)
  - search_past_analyses: Search past agent analyses (replaces 3.4's keyword matching)

The existing tools (get_stock_price, get_news, get_historical_prices, calculate)
are unchanged. The agent loop in agent.py is unchanged. Only this file grew.

THIS IS THE KEY ARCHITECTURAL POINT: RAG is just better tools.
"""

import json
import time
import random
from datetime import datetime, timedelta
from memory import search_memories
from rag_pipeline import RAGCollection


# ── Tool Definitions (JSON Schema for Claude) ─────────────────────────

TOOLS = [
    # ── Existing tools from Exercise 3.3 ──────────────────────────────
    {
        "name": "get_stock_price",
        "description": "Get the current price, 24h change, volume, and market cap for a stock or cryptocurrency.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol (e.g., BTC, ETH, AAPL, NVDA)"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_news",
        "description": "Get recent news headlines and sentiment for a stock or cryptocurrency.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol (e.g., BTC, ETH, AAPL)"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_historical_prices",
        "description": "Get daily closing prices for the past N days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of history (max 30)",
                    "default": 7
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "calculate",
        "description": "Evaluate a mathematical expression. Use for percentage changes, averages, ratios.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression to evaluate (e.g., '(84250 - 78000) / 78000 * 100')"
                }
            },
            "required": ["expression"]
        }
    },

    # ── NEW: RAG-powered tools ────────────────────────────────────────
    {
        "name": "search_knowledge_base",
        "description": "Search the knowledge base of market research reports, analyst notes, and historical analyses. Use this when you need historical context, background information, or reference data that isn't available from current price/news tools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query — describe what information you need (e.g., 'Bitcoin 2022 crash causes', 'Federal Reserve rate policy impact on crypto')"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_past_analyses",
        "description": "Search your memory of past analyses. Use this when the user references previous work, asks about trends over time, or wants to compare current data with past assessments.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query — asset names, topics, or timeframes"
                }
            },
            "required": ["query"]
        }
    },
]


# ── Mock Market Data (same as Exercise 3.3) ───────────────────────────

MOCK_PRICES = {
    "BTC": {"price": 84250.00, "change_24h": 2.34, "volume": 28500000000, "market_cap": 1650000000000},
    "ETH": {"price": 3180.00, "change_24h": -1.12, "volume": 14200000000, "market_cap": 382000000000},
    "SOL": {"price": 142.50, "change_24h": 5.67, "volume": 3800000000, "market_cap": 62000000000},
    "AAPL": {"price": 178.50, "change_24h": 0.45, "volume": 52000000, "market_cap": 2780000000000},
    "GOOGL": {"price": 141.80, "change_24h": -0.23, "volume": 21000000, "market_cap": 1750000000000},
    "NVDA": {"price": 875.30, "change_24h": 3.12, "volume": 42000000, "market_cap": 2150000000000},
    "TSLA": {"price": 245.60, "change_24h": -2.45, "volume": 98000000, "market_cap": 780000000000},
    "MSFT": {"price": 415.20, "change_24h": 0.89, "volume": 22000000, "market_cap": 3090000000000},
}

MOCK_NEWS = {
    "BTC": [
        {"headline": "Bitcoin ETF inflows reach record $2B weekly", "sentiment": "bullish", "source": "CoinDesk"},
        {"headline": "Institutional adoption accelerates as pension funds add BTC", "sentiment": "bullish", "source": "Bloomberg"},
        {"headline": "Bitcoin mining difficulty hits new all-time high", "sentiment": "neutral", "source": "The Block"},
    ],
    "ETH": [
        {"headline": "Ethereum L2 transaction volume surpasses mainnet", "sentiment": "bullish", "source": "The Block"},
        {"headline": "SEC delays decision on Ethereum staking ETFs", "sentiment": "bearish", "source": "Reuters"},
    ],
    "SOL": [
        {"headline": "Solana DeFi TVL crosses $8B milestone", "sentiment": "bullish", "source": "DeFiLlama"},
        {"headline": "Network experiences brief congestion during memecoin surge", "sentiment": "bearish", "source": "CoinDesk"},
    ],
    "NVDA": [
        {"headline": "NVIDIA announces next-gen Blackwell Ultra GPUs for AI", "sentiment": "bullish", "source": "Reuters"},
        {"headline": "Data centre revenue expected to double in FY2025", "sentiment": "bullish", "source": "Bloomberg"},
        {"headline": "China AI chip restrictions create uncertainty", "sentiment": "bearish", "source": "WSJ"},
    ],
}


def _generate_historical(symbol: str, days: int) -> list:
    """Generate mock historical prices."""
    if symbol not in MOCK_PRICES:
        return []
    base = MOCK_PRICES[symbol]["price"]
    history = []
    for i in range(days, 0, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        variation = random.uniform(-0.03, 0.03)
        price = round(base * (1 + variation * (i / days)), 2)
        history.append({"date": date, "close": price})
    return history


# ── Tool Executor with Retries (from Exercise 3.3) ───────────────────

class ToolExecutor:
    """Wraps tool execution with retries, logging, and error handling."""

    def __init__(self, max_retries: int = 2, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.stats = {"calls": 0, "retries": 0, "failures": 0}

    def execute(self, name: str, input_data: dict, execute_fn) -> str:
        """Execute a tool with retries and logging."""
        self.stats["calls"] += 1

        for attempt in range(self.max_retries + 1):
            try:
                result = execute_fn(name, input_data)
                return result
            except Exception as e:
                if attempt < self.max_retries:
                    self.stats["retries"] += 1
                    delay = self.base_delay * (2 ** attempt)
                    time.sleep(delay)
                else:
                    self.stats["failures"] += 1
                    return json.dumps({"error": f"Tool '{name}' failed after {self.max_retries + 1} attempts: {str(e)}"})


# ── Tool Router ───────────────────────────────────────────────────────

def execute_tool(name: str, input_data: dict) -> str:
    """Route tool calls to the appropriate handler.

    Returns a JSON string — always. The agent reads this as a tool_result.

    WHAT'S NEW VS EXERCISE 3.3:
    Two new cases at the bottom: search_knowledge_base and search_past_analyses.
    Everything else is identical.
    """
    if name == "get_stock_price":
        symbol = input_data["symbol"].upper()
        if symbol in MOCK_PRICES:
            return json.dumps({"symbol": symbol, **MOCK_PRICES[symbol]})
        return json.dumps({"error": f"Unknown symbol: {symbol}. Available: {list(MOCK_PRICES.keys())}"})

    elif name == "get_news":
        symbol = input_data["symbol"].upper()
        if symbol in MOCK_NEWS:
            return json.dumps({"symbol": symbol, "headlines": MOCK_NEWS[symbol]})
        return json.dumps({"symbol": symbol, "headlines": [], "note": "No recent news available"})

    elif name == "get_historical_prices":
        symbol = input_data["symbol"].upper()
        days = min(input_data.get("days", 7), 30)
        if symbol in MOCK_PRICES:
            history = _generate_historical(symbol, days)
            return json.dumps({"symbol": symbol, "days": days, "prices": history})
        return json.dumps({"error": f"Unknown symbol: {symbol}"})

    elif name == "calculate":
        expression = input_data["expression"]
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return json.dumps({"expression": expression, "result": round(float(result), 4)})
        except Exception as e:
            return json.dumps({"error": f"Calculation error: {str(e)}"})

    # ── NEW: RAG-powered tools ────────────────────────────────────────

    elif name == "search_knowledge_base":
        query = input_data["query"]
        collection = RAGCollection("knowledge_base")

        if collection.collection.count() == 0:
            return json.dumps({"results": [], "note": "Knowledge base is empty. Run ingest.py first."})

        results = collection.search(query, top_k=5, use_rerank=True)
        formatted = []
        for r in results:
            formatted.append({
                "content": r["text"],
                "source": r["metadata"].get("source", "unknown"),
                "title": r["metadata"].get("title", "unknown"),
                "relevance_score": round(r["score"], 3),
            })
        return json.dumps({"query": query, "results": formatted})

    elif name == "search_past_analyses":
        query = input_data["query"]
        results = search_memories(query, limit=5)

        if not results:
            return json.dumps({"query": query, "results": [], "note": "No past analyses found."})

        formatted = []
        for r in results:
            formatted.append({
                "query": r.get("query", ""),
                "timestamp": r.get("timestamp", ""),
                "analysis_excerpt": r.get("response", "")[:500],  # Truncate to avoid blowing up context
                "relevance_score": round(r.get("relevance_score", 0), 3),
            })
        return json.dumps({"query": query, "results": formatted})

    else:
        return json.dumps({"error": f"Unknown tool: {name}"})