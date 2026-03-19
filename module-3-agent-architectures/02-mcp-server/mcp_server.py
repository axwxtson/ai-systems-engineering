from mcp.server.fastmcp import FastMCP
import json
import ast
import operator

# Create server
mcp = FastMCP("market-data")


@mcp.tool()
def get_stock_price(symbol: str) -> str:
    """Get current price and basic stats for a stock or crypto asset.
    Returns price, 24h change, and volume.
    """
    symbol = symbol.upper()
    
    prices = {
        "BTC": {"price": 84250.00, "change_24h": 2.3, "volume": "28.5B", "currency": "USD"},
        "ETH": {"price": 1920.50, "change_24h": -1.1, "volume": "12.8B", "currency": "USD"},
        "AAPL": {"price": 178.50, "change_24h": 0.8, "volume": "52.3M", "currency": "USD"},
        "GOOGL": {"price": 171.20, "change_24h": -0.3, "volume": "18.7M", "currency": "USD"},
        "NVDA": {"price": 124.80, "change_24h": 3.1, "volume": "45.2M", "currency": "USD"},
    }
    
    if symbol in prices:
        return json.dumps({"symbol": symbol, **prices[symbol]})
    else:
        return json.dumps({"error": f"Symbol '{symbol}' not found. Available: {list(prices.keys())}"})


@mcp.tool()
def get_news(query: str, limit: int = 5) -> str:
    """Get recent news headlines for a given topic or asset.
    Returns up to 5 recent headlines with sources and dates.
    """
    # Same mock data as Exercise 3.1
    news = {
        "bitcoin": [
            {"headline": "Bitcoin breaks above $84k as institutional inflows accelerate", "source": "CoinDesk", "date": "2026-03-15"},
            {"headline": "US Treasury signals clearer crypto regulatory framework", "source": "Reuters", "date": "2026-03-14"},
            {"headline": "MicroStrategy announces additional Bitcoin purchase of 2,500 BTC", "source": "Bloomberg", "date": "2026-03-14"},
        ],
        "ethereum": [
            {"headline": "Ethereum staking yields stabilise around 4.2%", "source": "CoinDesk", "date": "2026-03-15"},
            {"headline": "Major DeFi protocol announces migration to Ethereum L2", "source": "The Block", "date": "2026-03-14"},
        ],
    }
    
    query_lower = query.lower()
    for topic, articles in news.items():
        if topic in query_lower:
            return json.dumps({"query": query, "results": articles[:limit]})
    
    return json.dumps({"query": query, "results": [], "note": "No news found"})


@mcp.tool()
def get_historical_prices(symbol: str, days: int = 7) -> str:
    """Get historical daily closing prices for an asset.
    Returns date and closing price for the specified number of days.
    """
    symbol = symbol.upper()
    
    historical = {
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
    }
    
    if symbol in historical:
        return json.dumps({"symbol": symbol, "prices": historical[symbol][:days]})
    else:
        return json.dumps({"error": f"No historical data for '{symbol}'"})


@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression. Supports +, -, *, /, parentheses.
    Use for percentage calculations, comparisons, and any arithmetic.
    """
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
    result = _eval(tree)
    return json.dumps({"expression": expression, "result": round(result, 4)})


if __name__ == "__main__":
    mcp.run(transport="stdio")