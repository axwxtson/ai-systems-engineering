import json
import ast
import operator
import time
from typing import Callable
from memory import search_memories

# ============================================================
# Tool Executor (same as Exercise 3.3)
# ============================================================

class ToolExecutor:
    """Production-grade tool execution with retries, timeouts, and validation."""

    def __init__(self, max_retries: int = 2, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.call_log = []

    def execute(self, name: str, input_data: dict, handler: Callable) -> str:
        """Execute a tool with retry logic. ALWAYS returns valid JSON."""
        for attempt in range(self.max_retries + 1):
            start_time = time.time()

            try:
                result = handler(name, input_data)
                elapsed = time.time() - start_time

                self.call_log.append({
                    "tool": name,
                    "input": input_data,
                    "attempt": attempt + 1,
                    "elapsed": round(elapsed, 3),
                    "status": "success"
                })

                json.loads(result)  # Validate JSON
                return result

            except json.JSONDecodeError:
                self.call_log.append({
                    "tool": name, "attempt": attempt + 1, "status": "invalid_json"
                })
                return json.dumps({
                    "error": f"Tool '{name}' returned invalid data."
                })

            except Exception as e:
                self.call_log.append({
                    "tool": name, "attempt": attempt + 1,
                    "status": "error", "error": str(e)
                })
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                return json.dumps({
                    "error": f"Tool '{name}' failed after {self.max_retries + 1} attempts: {str(e)}"
                })

    def get_stats(self) -> dict:
        total = len(self.call_log)
        failures = sum(1 for c in self.call_log if c["status"] != "success")
        return {
            "total_calls": total,
            "failures": failures,
            "success_rate": round((total - failures) / total * 100, 1) if total > 0 else 0,
            "log": self.call_log
        }


# ============================================================
# Tool Definitions — includes memory tool
# ============================================================

TOOLS = [
    {
        "name": "get_stock_price",
        "description": "Get the current price and basic stats for a stock or crypto asset. Returns price, 24h change, volume, and market cap category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol, e.g. 'AAPL', 'BTC', 'ETH'"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_news",
        "description": "Get recent news headlines for a given topic or asset. Returns up to 5 recent headlines with sources, dates, and sentiment tags.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query, e.g. 'Bitcoin regulation' or 'AAPL earnings'"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of headlines to return (default 5)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_historical_prices",
        "description": "Get historical daily closing prices for an asset over a given period. Returns date and closing price for calculating trends and percentage changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol, e.g. 'AAPL', 'BTC'"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of history to return (default 7, max 30)"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "calculate",
        "description": "Evaluate a mathematical expression. Supports +, -, *, /, parentheses. Use for percentage calculations, comparisons, and any arithmetic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression, e.g. '(42000 - 38000) / 38000 * 100'"
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "search_past_analyses",
        "description": "Search your memory of past analyses you have performed. Use this when the user references previous work, asks about trends over time, asks what you've analysed before, or wants to compare current data with past assessments. Returns previous analyses with timestamps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query — asset names, topics, or keywords, e.g. 'Bitcoin analysis' or 'Ethereum'"
                }
            },
            "required": ["query"]
        }
    }
]


# ============================================================
# Mock Data (same as Exercise 3.3)
# ============================================================

MOCK_PRICES = {
    "BTC":   {"price": 84250.00, "change_24h": 2.3,  "volume": "28.5B", "currency": "USD", "market_cap": "1.67T"},
    "ETH":   {"price": 1920.50,  "change_24h": -1.1, "volume": "12.8B", "currency": "USD", "market_cap": "231B"},
    "SOL":   {"price": 142.30,   "change_24h": 4.7,  "volume": "3.2B",  "currency": "USD", "market_cap": "65B"},
    "AAPL":  {"price": 178.50,   "change_24h": 0.8,  "volume": "52.3M", "currency": "USD", "market_cap": "2.75T"},
    "GOOGL": {"price": 171.20,   "change_24h": -0.3, "volume": "18.7M", "currency": "USD", "market_cap": "2.12T"},
    "NVDA":  {"price": 124.80,   "change_24h": 3.1,  "volume": "45.2M", "currency": "USD", "market_cap": "3.05T"},
    "TSLA":  {"price": 248.90,   "change_24h": -2.4, "volume": "38.1M", "currency": "USD", "market_cap": "795B"},
    "MSFT":  {"price": 415.60,   "change_24h": 0.5,  "volume": "22.4M", "currency": "USD", "market_cap": "3.09T"},
}

MOCK_NEWS = {
    "bitcoin": [
        {"headline": "Bitcoin breaks above $84k as institutional inflows accelerate", "source": "CoinDesk", "date": "2026-03-15", "sentiment": "bullish"},
        {"headline": "US Treasury signals clearer crypto regulatory framework", "source": "Reuters", "date": "2026-03-14", "sentiment": "bullish"},
        {"headline": "MicroStrategy announces additional Bitcoin purchase of 2,500 BTC", "source": "Bloomberg", "date": "2026-03-14", "sentiment": "bullish"},
        {"headline": "Bitcoin mining difficulty reaches all-time high", "source": "The Block", "date": "2026-03-13", "sentiment": "neutral"},
        {"headline": "Analysts predict Bitcoin could test $90k by end of Q1", "source": "CNBC", "date": "2026-03-12", "sentiment": "bullish"},
    ],
    "ethereum": [
        {"headline": "Ethereum staking yields stabilise around 4.2%", "source": "CoinDesk", "date": "2026-03-15", "sentiment": "neutral"},
        {"headline": "Major DeFi protocol announces migration to Ethereum L2", "source": "The Block", "date": "2026-03-14", "sentiment": "bullish"},
        {"headline": "Ethereum gas fees drop to 6-month low", "source": "Etherscan", "date": "2026-03-13", "sentiment": "bullish"},
    ],
    "solana": [
        {"headline": "Solana DEX volume surges past $2B daily", "source": "The Block", "date": "2026-03-15", "sentiment": "bullish"},
        {"headline": "Solana network uptime hits 99.9% over last 90 days", "source": "CoinDesk", "date": "2026-03-14", "sentiment": "bullish"},
        {"headline": "New Solana phone pre-orders exceed expectations", "source": "Decrypt", "date": "2026-03-13", "sentiment": "bullish"},
    ],
    "apple": [
        {"headline": "Apple Vision Pro 2 rumoured for Q3 2026 launch", "source": "Bloomberg", "date": "2026-03-15", "sentiment": "bullish"},
        {"headline": "Apple services revenue hits record $25B quarterly", "source": "CNBC", "date": "2026-03-14", "sentiment": "bullish"},
        {"headline": "Apple expands AI features across product line", "source": "The Verge", "date": "2026-03-13", "sentiment": "bullish"},
    ],
    "nvidia": [
        {"headline": "Nvidia reports record data centre revenue driven by AI demand", "source": "Reuters", "date": "2026-03-15", "sentiment": "bullish"},
        {"headline": "Nvidia announces next-gen Blackwell Ultra GPUs", "source": "The Verge", "date": "2026-03-14", "sentiment": "bullish"},
        {"headline": "Cloud providers increase Nvidia GPU orders by 40%", "source": "Bloomberg", "date": "2026-03-13", "sentiment": "bullish"},
    ],
    "tesla": [
        {"headline": "Tesla Robotaxi pilot expands to 5 new US cities", "source": "Reuters", "date": "2026-03-15", "sentiment": "bullish"},
        {"headline": "Tesla Q1 deliveries miss analyst expectations", "source": "Bloomberg", "date": "2026-03-14", "sentiment": "bearish"},
        {"headline": "Tesla energy storage division revenue doubles year-over-year", "source": "CNBC", "date": "2026-03-13", "sentiment": "bullish"},
    ],
    "microsoft": [
        {"headline": "Microsoft Azure AI revenue grows 55% year-over-year", "source": "Reuters", "date": "2026-03-15", "sentiment": "bullish"},
        {"headline": "Microsoft Copilot reaches 100M monthly active users", "source": "The Verge", "date": "2026-03-14", "sentiment": "bullish"},
        {"headline": "Microsoft faces EU antitrust scrutiny over cloud bundling", "source": "Bloomberg", "date": "2026-03-13", "sentiment": "bearish"},
    ],
    "google": [
        {"headline": "Google Gemini 2.5 benchmarks show significant reasoning gains", "source": "The Verge", "date": "2026-03-15", "sentiment": "bullish"},
        {"headline": "Google Cloud wins major government contract", "source": "Reuters", "date": "2026-03-14", "sentiment": "bullish"},
        {"headline": "Alphabet announces $70B share buyback programme", "source": "Bloomberg", "date": "2026-03-13", "sentiment": "bullish"},
    ],
}

MOCK_HISTORICAL = {
    "BTC": [
        {"date": "2026-03-15", "close": 84250.00},
        {"date": "2026-03-14", "close": 82300.00},
        {"date": "2026-03-13", "close": 81100.00},
        {"date": "2026-03-12", "close": 79800.00},
        {"date": "2026-03-11", "close": 80500.00},
        {"date": "2026-03-10", "close": 78200.00},
        {"date": "2026-03-09", "close": 77900.00},
    ],
    "ETH": [
        {"date": "2026-03-15", "close": 1920.50},
        {"date": "2026-03-14", "close": 1942.00},
        {"date": "2026-03-13", "close": 1935.00},
        {"date": "2026-03-12", "close": 1910.00},
        {"date": "2026-03-11", "close": 1898.00},
        {"date": "2026-03-10", "close": 1875.00},
        {"date": "2026-03-09", "close": 1860.00},
    ],
    "SOL": [
        {"date": "2026-03-15", "close": 142.30},
        {"date": "2026-03-14", "close": 138.50},
        {"date": "2026-03-13", "close": 135.20},
        {"date": "2026-03-12", "close": 131.80},
        {"date": "2026-03-11", "close": 128.90},
        {"date": "2026-03-10", "close": 126.40},
        {"date": "2026-03-09", "close": 124.10},
    ],
    "AAPL": [
        {"date": "2026-03-15", "close": 178.50},
        {"date": "2026-03-14", "close": 177.10},
        {"date": "2026-03-13", "close": 175.80},
        {"date": "2026-03-12", "close": 176.20},
        {"date": "2026-03-11", "close": 174.50},
        {"date": "2026-03-10", "close": 173.90},
        {"date": "2026-03-09", "close": 172.30},
    ],
    "GOOGL": [
        {"date": "2026-03-15", "close": 171.20},
        {"date": "2026-03-14", "close": 172.50},
        {"date": "2026-03-13", "close": 170.80},
        {"date": "2026-03-12", "close": 169.30},
        {"date": "2026-03-11", "close": 168.10},
        {"date": "2026-03-10", "close": 167.50},
        {"date": "2026-03-09", "close": 166.20},
    ],
    "NVDA": [
        {"date": "2026-03-15", "close": 124.80},
        {"date": "2026-03-14", "close": 122.10},
        {"date": "2026-03-13", "close": 119.50},
        {"date": "2026-03-12", "close": 118.20},
        {"date": "2026-03-11", "close": 115.80},
        {"date": "2026-03-10", "close": 113.40},
        {"date": "2026-03-09", "close": 111.90},
    ],
    "TSLA": [
        {"date": "2026-03-15", "close": 248.90},
        {"date": "2026-03-14", "close": 255.10},
        {"date": "2026-03-13", "close": 258.30},
        {"date": "2026-03-12", "close": 261.70},
        {"date": "2026-03-11", "close": 259.40},
        {"date": "2026-03-10", "close": 262.80},
        {"date": "2026-03-09", "close": 265.20},
    ],
    "MSFT": [
        {"date": "2026-03-15", "close": 415.60},
        {"date": "2026-03-14", "close": 413.20},
        {"date": "2026-03-13", "close": 411.80},
        {"date": "2026-03-12", "close": 409.50},
        {"date": "2026-03-11", "close": 407.30},
        {"date": "2026-03-10", "close": 405.10},
        {"date": "2026-03-09", "close": 402.80},
    ],
}


# ============================================================
# Safe Calculator (same as Exercise 3.3)
# ============================================================

def safe_calculate(expression: str) -> float:
    """Safely evaluate basic math expressions without using eval()."""
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
    }

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Non-numeric constant: {node.value}")
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op_type = type(node.op)
            if op_type not in allowed_operators:
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
            return allowed_operators[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            op_type = type(node.op)
            if op_type not in allowed_operators:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
            return allowed_operators[op_type](operand)
        else:
            raise ValueError(f"Unsupported expression: {type(node).__name__}")

    tree = ast.parse(expression, mode='eval')
    return _eval(tree)


# ============================================================
# Tool Executor Function — now includes memory
# ============================================================

def execute_tool(name: str, input_data: dict) -> str:
    """Execute a tool and return the result as a JSON string."""

    if name == "get_stock_price":
        symbol = input_data["symbol"].upper()
        if symbol in MOCK_PRICES:
            return json.dumps({"symbol": symbol, **MOCK_PRICES[symbol]})
        else:
            return json.dumps({"error": f"Symbol '{symbol}' not found. Available: {list(MOCK_PRICES.keys())}"})

    elif name == "get_news":
        query = input_data["query"].lower()
        limit = input_data.get("limit", 5)
        for topic, articles in MOCK_NEWS.items():
            if topic in query:
                return json.dumps({"query": input_data["query"], "results": articles[:limit]})
        return json.dumps({"query": input_data["query"], "results": [], "note": "No news found for this query"})

    elif name == "get_historical_prices":
        symbol = input_data["symbol"].upper()
        days = input_data.get("days", 7)
        if symbol in MOCK_HISTORICAL:
            return json.dumps({"symbol": symbol, "prices": MOCK_HISTORICAL[symbol][:days]})
        else:
            return json.dumps({"error": f"No historical data for '{symbol}'"})

    elif name == "calculate":
        try:
            result = safe_calculate(input_data["expression"])
            return json.dumps({"expression": input_data["expression"], "result": round(result, 4)})
        except Exception as e:
            return json.dumps({"error": f"Calculation failed: {str(e)}"})

    elif name == "search_past_analyses":
        query = input_data["query"]
        memories = search_memories(query, limit=3)
        if memories:
            # Return summaries, not full responses (keep context window manageable)
            results = []
            for m in memories:
                results.append({
                    "timestamp": m["timestamp"],
                    "query": m["query"],
                    "response_preview": m["response"][:500],
                    "metadata": m.get("metadata", {})
                })
            return json.dumps({"results": results, "count": len(results)})
        else:
            return json.dumps({"results": [], "note": "No past analyses found matching your query"})

    else:
        return json.dumps({"error": f"Unknown tool: {name}"})