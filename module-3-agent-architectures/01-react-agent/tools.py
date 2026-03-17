import json
import ast
import operator
from datetime import datetime

# --- Tool Definitions (JSON Schema for Claude) ---

TOOLS = [
    {
        "name": "get_stock_price",
        "description": "Get the current price and basic stats for a stock or crypto asset. Returns price, 24h change, and volume.",
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
        "description": "Get recent news headlines for a given topic or asset. Returns up to 5 recent headlines with sources and dates.",
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
        "description": "Get historical daily closing prices for an asset over a given period. Returns date and closing price.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol, e.g. 'AAPL', 'BTC'"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of history to return (default 7)"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "calculate",
        "description": "Evaluate a mathematical expression. Supports +, -, *, /, parentheses.",
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
    }
]


# --- Mock Data ---

MOCK_PRICES = {
    "BTC": {"price": 84250.00, "change_24h": 2.3, "volume": "28.5B", "currency": "USD"},
    "ETH": {"price": 1920.50, "change_24h": -1.1, "volume": "12.8B", "currency": "USD"},
    "AAPL": {"price": 178.50, "change_24h": 0.8, "volume": "52.3M", "currency": "USD"},
    "GOOGL": {"price": 171.20, "change_24h": -0.3, "volume": "18.7M", "currency": "USD"},
    "NVDA": {"price": 124.80, "change_24h": 3.1, "volume": "45.2M", "currency": "USD"},
}

MOCK_NEWS = {
    "bitcoin": [
        {"headline": "Bitcoin breaks above $84k as institutional inflows accelerate", "source": "CoinDesk", "date": "2026-03-15"},
        {"headline": "US Treasury signals clearer crypto regulatory framework", "source": "Reuters", "date": "2026-03-14"},
        {"headline": "MicroStrategy announces additional Bitcoin purchase of 2,500 BTC", "source": "Bloomberg", "date": "2026-03-14"},
        {"headline": "Bitcoin mining difficulty reaches all-time high", "source": "The Block", "date": "2026-03-13"},
        {"headline": "Analysts predict Bitcoin could test $90k by end of Q1", "source": "CNBC", "date": "2026-03-12"},
    ],
    "ethereum": [
        {"headline": "Ethereum staking yields stabilise around 4.2%", "source": "CoinDesk", "date": "2026-03-15"},
        {"headline": "Major DeFi protocol announces migration to Ethereum L2", "source": "The Block", "date": "2026-03-14"},
        {"headline": "Ethereum gas fees drop to 6-month low", "source": "Etherscan", "date": "2026-03-13"},
    ],
    "apple": [
        {"headline": "Apple Vision Pro 2 rumoured for Q3 2026 launch", "source": "Bloomberg", "date": "2026-03-15"},
        {"headline": "Apple services revenue hits record $25B quarterly", "source": "CNBC", "date": "2026-03-14"},
        {"headline": "Apple expands AI features across product line", "source": "The Verge", "date": "2026-03-13"},
    ],
    "nvidia": [
        {"headline": "Nvidia reports record data centre revenue driven by AI demand", "source": "Reuters", "date": "2026-03-15"},
        {"headline": "Nvidia announces next-gen Blackwell Ultra GPUs", "source": "The Verge", "date": "2026-03-14"},
        {"headline": "Cloud providers increase Nvidia GPU orders by 40%", "source": "Bloomberg", "date": "2026-03-13"},
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
    "AAPL": [
        {"date": "2026-03-15", "close": 178.50},
        {"date": "2026-03-14", "close": 177.10},
        {"date": "2026-03-13", "close": 175.80},
        {"date": "2026-03-12", "close": 176.20},
        {"date": "2026-03-11", "close": 174.50},
        {"date": "2026-03-10", "close": 173.90},
        {"date": "2026-03-09", "close": 172.30},
    ],
}


# --- Safe Calculator ---

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


# --- Tool Executor ---

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
        # Match against known topics
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

    else:
        return json.dumps({"error": f"Unknown tool: {name}"})