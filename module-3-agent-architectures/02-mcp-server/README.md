# Exercise 3.2: MCP Server for Market Data

## What This Is

A Model Context Protocol (MCP) server that exposes market data tools, paired with a client that connects to it and runs a ReAct agent. Same tools and data as Exercise 3.1, but decoupled — the tools live in a server, the agent lives in a client, and they communicate via MCP (JSON-RPC over stdio).

## What It Demonstrates

- **MCP server**: Tools defined with `@mcp.tool()` decorators, schemas generated from Python type hints
- **MCP client**: Connects to server, discovers tools automatically, converts to Anthropic API format
- **Protocol transparency**: Agent loop is identical to Exercise 3.1 — only the tool execution layer changed
- **Separation of concerns**: Tool implementation is decoupled from agent logic
- **Async Python**: Client uses `async`/`await` for MCP communication

## How to Run
```bash
pip install anthropic mcp
export ANTHROPIC_API_KEY="sk-ant-..."

# Run the client (it spawns the server automatically)
python3 mcp_client.py
```

Do NOT run `mcp_server.py` directly — the client launches it as a subprocess.

## Key Insight

The only line that changed from Exercise 3.1:
```python
# Exercise 3.1 (direct):
result = execute_tool(block.name, block.input)

# Exercise 3.2 (MCP):
result = await session.call_tool(block.name, block.input)
```

MCP is a transport layer, not a new paradigm. The agent loop stays the same.

## File Structure

- `mcp_server.py` — MCP server exposing 4 market data tools
- `mcp_client.py` — Client that discovers tools and runs ReAct agent
- `requirements.txt` — anthropic, mcp

## Connection to AW Analysis

In production, this server connects to real market data APIs instead of mock data. Multiple agents or clients can connect to the same server. The server can be deployed independently and versioned separately from the agent.
```