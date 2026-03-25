"""
agent.py — The AW Analysis ReAct agent.

THIS FILE IS FUNCTIONALLY IDENTICAL TO EXERCISE 3.3/3.4.

The agent loop didn't change. The tool definitions changed (tools.py gained
two new tools). The memory system changed (memory.py uses vector search
instead of keyword matching). But the agent loop — the core while loop
that sends messages to Claude, checks for tool calls, executes them,
and sends results back — is exactly the same.

This is the architectural point of Exercise 4.4: RAG is a retrieval upgrade
to the tools, not a change to the agent architecture.
"""

import json
import anthropic
from tools import TOOLS, execute_tool, ToolExecutor
from config import CLAUDE_MODEL

client = anthropic.Anthropic()


def run_react_agent(
    user_message: str,
    system_prompt: str,
    max_steps: int = 10,
    verbose: bool = True,
) -> dict:
    """Run a ReAct agent with planning, ToolExecutor, and structured logging.

    Returns a dict with:
    - "response": the final text response
    - "steps": list of step logs
    - "total_tokens": token usage breakdown
    - "tool_calls": total number of tool calls
    - "cost_estimate": estimated dollar cost
    """
    messages = [{"role": "user", "content": user_message}]
    steps_log = []
    total_input_tokens = 0
    total_output_tokens = 0
    tool_call_count = 0

    executor = ToolExecutor(max_retries=2, base_delay=1.0)

    for step in range(max_steps):
        # ── THINK + ACT ──────────────────────────────────────────────
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens
        messages.append({"role": "assistant", "content": response.content})

        # ── Log this step ─────────────────────────────────────────────
        step_info = {
            "step": step + 1,
            "reasoning": [],
            "tool_calls": [],
        }

        for block in response.content:
            if block.type == "text":
                step_info["reasoning"].append(block.text)
                if verbose:
                    print(f"\n  [Step {step + 1}] {block.text[:200]}...")

        # ── Check if done ─────────────────────────────────────────────
        if response.stop_reason == "end_turn":
            steps_log.append(step_info)
            final_text = ""
            for block in response.content:
                if block.type == "text":
                    final_text += block.text

            return {
                "response": final_text,
                "steps": steps_log,
                "total_tokens": {
                    "input": total_input_tokens,
                    "output": total_output_tokens,
                    "total": total_input_tokens + total_output_tokens,
                },
                "tool_calls": tool_call_count,
                "cost_estimate": round(
                    (total_input_tokens * 0.003 + total_output_tokens * 0.015) / 1000, 4
                ),
            }

        # ── Execute tool calls ────────────────────────────────────────
        tool_results = []

        for block in response.content:
            if block.type == "tool_use":
                tool_call_count += 1
                if verbose:
                    print(f"  [Tool] {block.name}({json.dumps(block.input)[:100]})")

                result = executor.execute(block.name, block.input, execute_tool)

                step_info["tool_calls"].append({
                    "tool": block.name,
                    "input": block.input,
                    "result": result[:200],  # Truncate for logging
                })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        steps_log.append(step_info)
        messages.append({"role": "user", "content": tool_results})

    # Max steps reached
    return {
        "response": "Max steps reached — agent did not complete.",
        "steps": steps_log,
        "total_tokens": {
            "input": total_input_tokens,
            "output": total_output_tokens,
            "total": total_input_tokens + total_output_tokens,
        },
        "tool_calls": tool_call_count,
        "cost_estimate": round(
            (total_input_tokens * 0.003 + total_output_tokens * 0.015) / 1000, 4
        ),
    }