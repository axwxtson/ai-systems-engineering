import anthropic
import json
from datetime import datetime
from tools import TOOLS, execute_tool

client = anthropic.Anthropic()

REACT_SYSTEM_PROMPT = """You are a financial research agent. You have access to tools for looking up stock/crypto prices, news, historical data, and performing calculations.

For every query, follow this process:

1. Think about what information you need to answer the question
2. Use your tools to gather that information, one step at a time
3. After each tool result, think about what you've learned and what you still need
4. When you have enough information, provide a clear, well-structured answer

IMPORTANT RULES:
- Always explain your reasoning before calling a tool
- After receiving results, briefly assess what the data tells you before continuing
- If a tool returns an error, acknowledge it and try an alternative approach
- When you have enough information, synthesise a final answer — don't keep calling tools unnecessarily
- Cite specific numbers from your tool results in your final answer"""


def run_react_agent(user_message: str, max_steps: int = 10, verbose: bool = True) -> dict:
    """
    Run a ReAct agent that reasons explicitly before each action.
    
    Returns a dict with:
    - "response": the final text response
    - "steps": list of step logs (reasoning + actions)
    - "total_tokens": total token usage
    - "tool_calls": total number of tool calls made
    """
    messages = [{"role": "user", "content": user_message}]
    steps_log = []
    total_input_tokens = 0
    total_output_tokens = 0
    tool_call_count = 0

    for step in range(max_steps):
        # --- THINK + ACT: Send to Claude ---
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=REACT_SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        # Track token usage
        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        # Add Claude's response to conversation
        messages.append({"role": "assistant", "content": response.content})

        # --- Log this step ---
        step_info = {
            "step": step + 1,
            "reasoning": [],
            "tool_calls": [],
        }

        for block in response.content:
            if block.type == "text":
                step_info["reasoning"].append(block.text)
                if verbose:
                    print(f"\n{'='*60}")
                    print(f"Step {step + 1} — REASONING:")
                    print(f"{'='*60}")
                    print(block.text)
            elif block.type == "tool_use":
                step_info["tool_calls"].append({
                    "tool": block.name,
                    "input": block.input,
                    "id": block.id
                })

        steps_log.append(step_info)

        # --- DONE CHECK ---
        if response.stop_reason == "end_turn":
            final_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            return {
                "response": final_text,
                "steps": steps_log,
                "total_tokens": {
                    "input": total_input_tokens,
                    "output": total_output_tokens,
                    "total": total_input_tokens + total_output_tokens
                },
                "tool_calls": tool_call_count
            }

        # --- OBSERVE: Execute tools and send results back ---
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_call_count += 1

                if verbose:
                    print(f"\n  ACTION: {block.name}({json.dumps(block.input)})")

                result = execute_tool(block.name, block.input)

                if verbose:
                    # Truncate long results for display
                    display_result = result[:200] + "..." if len(result) > 200 else result
                    print(f"  RESULT: {display_result}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })

                # Also log the result
                step_info["tool_calls"][-1]["result"] = result

        messages.append({"role": "user", "content": tool_results})

    # Max steps reached
    return {
        "response": "Max steps reached — agent did not complete.",
        "steps": steps_log,
        "total_tokens": {
            "input": total_input_tokens,
            "output": total_output_tokens,
            "total": total_input_tokens + total_output_tokens
        },
        "tool_calls": tool_call_count
    }