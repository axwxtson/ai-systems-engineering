# Exercise 3.1: ReAct Agent from Scratch

## What This Is

A financial research agent built using the ReAct (Reasoning + Acting) pattern with the Anthropic API. No frameworks — just the API, a system prompt, and a ~60-line agent loop.

The agent has access to 4 tools (stock prices, news, historical prices, calculator) and explicitly reasons before each tool call, creating a visible trace of its decision-making.

## What It Demonstrates

- **ReAct pattern**: Explicit reasoning traces before every action
- **Tool use protocol**: Full tool_use → execute → tool_result loop
- **Parallel tool calls**: Claude calls multiple tools in one step when they're independent
- **Sequential chaining**: Results from one tool inform the next tool call
- **Error handling**: Unknown symbols return errors, agent handles gracefully
- **Instrumentation**: Step logging, token tracking, tool call counting

## How to Run
```bash
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
python3 main.py
```

## Test Queries

| Query | Expected Behaviour |
|-------|-------------------|
| "What's the current price of Bitcoin?" | Single tool call (get_stock_price) |
| "What's Bitcoin's price and how has it changed over the past week?" | Sequential: price → historical → calculate |
| "What's Bitcoin's percentage gain over the last 7 days?" | Historical → calculate |
| "Give me a complete analysis of Bitcoin" | 3-4 tool calls: price, historical, news, calculate |
| "What's the price of DOGE?" | Error handling — symbol not found |
| "Compare Bitcoin and Ethereum" | Parallel calls for both assets, then calculation |

## File Structure

- `agent.py` — The ReAct agent loop with system prompt, step logging, token tracking
- `tools.py` — Tool definitions (JSON Schema), mock data, tool executor
- `main.py` — CLI entry point

## Key Concepts

- **Agent loop**: Send message → check stop_reason → execute tools → send results → repeat
- **ReAct system prompt**: Instructs Claude to explain reasoning before each tool call
- **Structured return**: Agent returns a dict with response, step log, token usage, and tool call count — not just a string
- **max_steps**: Circuit breaker preventing infinite loops (set to 10)

## Connection to AW Analysis

This agent is the prototype for AW Analysis's core analysis engine. In production, the mock data in tools.py gets replaced with real API calls to market data providers, and the system prompt evolves into the production prompt from Module 2 Exercise 2.1.git ad