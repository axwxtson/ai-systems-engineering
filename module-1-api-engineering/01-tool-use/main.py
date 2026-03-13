import anthropic
import json
import ast
import operator

client = anthropic.Anthropic() 

tools = [
    {  
        "name": "get_weather",
        "description": "Get current weather for a city. Returns temperature in Celsius and conditions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name. e.g. 'London'"
                }
            },
            "required": ["city"]
        }   
    },
    {
        "name": "search_database",
        "description": "Search a market data database. Returns matching records.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query, e.g. 'Bitcoin price'"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "calculate",
        "description": "Evaluate a mathematical expression. Supports +, -, *, /.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression to evaluate, e.g. '12 * 9/5 + 32'"
                }
            },
            "required": ["expression"]
        }
    }
]

def safe_calculate(expression: str) -> float:
    """Safely evaluate basic math expressions."""
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }
    
    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            return allowed_operators[type(node.op)](left, right)
        else:
            raise ValueError(f"Unsupported operation: {type(node)}")
    
    tree = ast.parse(expression, mode='eval')
    return _eval(tree)
    

def execute_tool(name: str, input_data: dict) -> str:
    """This is my code — Claude doesn't touch it."""
    if name == "get_weather":
        # Mock data. In production this hits a real API
        return json.dumps({
            "city": input_data["city"],
            "temperature_c": 12,
            "conditions": "overcast",
            "humidity": 78
        })
    elif name == "search_database":
        return json.dumps({
            "query": input_data["query"],
            "results": [
                {"asset": "BTC", "price": 42000, "date": "2026-03-13"},
                {"asset": "BTC", "price": 43500, "date": "2026-03-12"},
                {"asset": "BTC", "price": 41800, "date": "2026-03-11"}
            ]
        })
    elif name == "calculate":
        try:
            result = safe_calculate(input_data["expression"])
            return json.dumps({
                "expression": input_data["expression"],
                "result": result
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to calculate: {str(e)}"})
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})




def run_agent(user_message: str, tools: list, tool_executor: callable, max_steps: int = 10):
    """
    The core agent loop. This is what frameworks abstract and what I need to understand fully.
    """
    messages = [{"role": "user", "content": user_message}]

    for step in range(max_steps):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        # Add Claude's response to conversation history
        messages.append({"role": "assistant", "content": response.content})

        # If Claude is done (no more tool calls), return the final response
        if response.stop_reason == "end_turn":
            # Extract text from the response
            return "".join(
                block.text for block in response.content if block.type == "text"
            )

        # Otherwise, execute all tool calls and send results back
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f" Step {step + 1}: Calling {block.name}({json.dumps(block.input)})")
                result = tool_executor(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })
                
        # Send all tool results back in one user message
        messages.append({"role": "user", "content": tool_results})
    
    return "Max steps reached — agent did not complete."

if __name__ == "__main__":
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == "quit":
            break
        result = run_agent(user_input, tools, execute_tool)
        print(f"\nClaude: {result}")