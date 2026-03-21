import anthropic
import json
from tools import TOOLS, execute_tool, ToolExecutor

client = anthropic.Anthropic()


def run_react_agent(
    user_message: str,
    system_prompt: str,
    max_steps: int = 10,
    verbose: bool = True
) -> dict:
    messages = [{"role": "user", "content": user_message}]
    steps_log = []
    total_input_tokens = 0
    total_output_tokens = 0
    tool_call_count = 0

    executor = ToolExecutor(max_retries=2, base_delay=1.0)

    for step in range(max_steps):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages
        )

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens
        messages.append({"role": "assistant", "content": response.content})

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

        if response.stop_reason == "end_turn":
            final_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            cost = estimate_cost(total_input_tokens, total_output_tokens)
            return {
                "response": final_text,
                "steps": steps_log,
                "total_tokens": {
                    "input": total_input_tokens,
                    "output": total_output_tokens,
                    "total": total_input_tokens + total_output_tokens
                },
                "tool_calls": tool_call_count,
                "tool_stats": executor.get_stats(),
                "cost_estimate": cost
            }

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_call_count += 1
                if verbose:
                    print(f"\n  ACTION: {block.name}({json.dumps(block.input)})")

                result = executor.execute(block.name, block.input, execute_tool)

                if verbose:
                    display_result = result[:200] + "..." if len(result) > 200 else result
                    print(f"  RESULT: {display_result}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })
                step_info["tool_calls"][-1]["result"] = result

        messages.append({"role": "user", "content": tool_results})

    return {
        "response": "Max steps reached. Partial data was collected but analysis could not be completed.",
        "steps": steps_log,
        "total_tokens": {
            "input": total_input_tokens,
            "output": total_output_tokens,
            "total": total_input_tokens + total_output_tokens
        },
        "tool_calls": tool_call_count,
        "tool_stats": executor.get_stats(),
        "cost_estimate": estimate_cost(total_input_tokens, total_output_tokens),
        "partial": True
    }


def estimate_cost(input_tokens: int, output_tokens: int) -> dict:
    input_cost = (input_tokens / 1000) * 0.003
    output_cost = (output_tokens / 1000) * 0.015
    total = input_cost + output_cost
    return {
        "input": round(input_cost, 6),
        "output": round(output_cost, 6),
        "total": round(total, 6)
    }