import anthropic
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio

REACT_SYSTEM_PROMPT = """You are a financial research agent with access to market data tools.

For every query, follow this process:
1. Think about what information you need
2. Use your tools to gather that information
3. After each result, assess what you've learned and what you still need
4. When you have enough, provide a clear answer

Always explain your reasoning before calling a tool.
If a tool returns an error, acknowledge it and try an alternative approach."""


async def run_mcp_agent(query: str):
    """Connect to MCP server, discover tools, run agent loop."""
    
    # Define how to launch the server
    server_params = StdioServerParameters(
        command="python3",
        args=["mcp_server.py"]
    )
    
    client = anthropic.Anthropic()
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Handshake
            await session.initialize()
            
            # Discover tools from server
            tools_result = await session.list_tools()
            
            # Convert MCP tool schemas to Anthropic API format
            anthropic_tools = []
            for tool in tools_result.tools:
                anthropic_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })
            
            print(f"Discovered {len(anthropic_tools)} tools: {[t['name'] for t in anthropic_tools]}")
            
            # --- Agent loop (same as Exercise 3.1) ---
            messages = [{"role": "user", "content": query}]
            
            for step in range(10):
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system=REACT_SYSTEM_PROMPT,
                    tools=anthropic_tools,
                    messages=messages
                )
                
                messages.append({"role": "assistant", "content": response.content})
                
                if response.stop_reason == "end_turn":
                    final = "".join(b.text for b in response.content if b.type == "text")
                    print(f"\nFINAL ANSWER:\n{final}")
                    return final
                
                # Execute tool calls via MCP
                tool_results = []
                for block in response.content:
                    if block.type == "text":
                        print(f"\nREASONING: {block.text}")
                    elif block.type == "tool_use":
                        print(f"ACTION: {block.name}({json.dumps(block.input)})")
                        
                        # Call tool through MCP session
                        result = await session.call_tool(block.name, block.input)
                        result_text = result.content[0].text
                        
                        print(f"RESULT: {result_text[:200]}")
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text
                        })
                
                messages.append({"role": "user", "content": tool_results})
            
            return "Max steps reached."


if __name__ == "__main__":
    query = input("Query: ")
    asyncio.run(run_mcp_agent(query))