import anthropic
import json

client = anthropic.Anthropic() # read ANTHROPIC_API_KEY from env

# Step 1: Define tools as JSON Schema
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
    }
]

# Step 2: Send request — Claude decides whether to use a tool
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": "What's the weather in London?"}] 
)

# Step 3: Check what Claude returned
print(response.stop_reason)  # "tool_use" — Claude wants to call a tool
print(response.content)

# [
#   TextBlock(type="text", text="I'll check the weather in London for you."),
#   ToolUseBlock(type="tool_use", id="toolu_abc123", name="get_weather", input={"city": "London"})
# ]

# Step 4: Your code executes the tool
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
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})

# Step 5: Find the tool_use block, execute it, send the result back
tool_use_block = next(b for b in response.content if b.type == "tool_use")

tool_result = execute_tool(tool_use_block.name, tool_use_block.input)

# Step 6: Send the result back — note the message structure
followup = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": "What's the weather in London?"},
        {"role": "assistant", "content": response.content}, # Claude's previous response INCLUDING the tool_use block
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id, # must match the tool_use id
                    "content": tool_result
                }
            ]
        }
    ]
)

print(followup.content[0].text)
# "The weather in London is currently 12°C and overcast, with 78% humidity."


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
                print(f" Step {step + 1}: Calling {block.name}({json.dumps(block.input)}")
                result = tool_executor(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })
                
        # Send all tool results back in one user message
        messages.append({"role": "user", "content": tool_results})
    
    return "Max steps reached — agent did not complete."

