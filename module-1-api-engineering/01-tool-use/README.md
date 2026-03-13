# Exercise 1.1: Tool Use from Scratch

Demonstrates the full Claude tool use cycle — defining tools as JSON Schema, 
handling the agent loop, parallel and sequential tool calls, and error handling.

## What it does

A CLI agent with three tools:
- `get_weather` — returns mock weather data for a city
- `search_database` — returns mock market data search results
- `calculate` — safely evaluates math expressions

## Run it
```bash
pip install anthropic
export ANTHROPIC_API_KEY=""
python3 main.py
```

## Key concepts demonstrated

- Tool use protocol (tool_use → execute → tool_result → continue)
- Parallel tool calls (multiple tools in one response)
- Sequential tool chaining (output of one tool informs the next)
- Error handling for unknown/failed tools
- Agent loop with max_steps circuit breaker