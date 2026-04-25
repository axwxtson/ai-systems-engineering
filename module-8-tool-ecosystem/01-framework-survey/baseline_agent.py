"""
baseline_agent.py — the hand-rolled Anthropic SDK implementation.

This is the REFERENCE version of the task. It's the one that actually runs.
It reuses the Module 3 agent loop pattern and the provider-abstraction
style from Module 7 Exercise 7.2 — both kept deliberately minimal so the
comparison with each framework sketch is legible.

Design goals (informing the rubric scoring):
  - Everything is in one file. No framework layers. No magic.
  - The agent loop is explicit: call model -> handle tool_use -> loop.
  - Provider-specific features (extended thinking, prompt caching) are
    one line away from being turned on.
  - Every decision the loop makes is visible in the code path.
"""

from dataclasses import dataclass, field
from typing import Any

from anthropic import Anthropic

from tasks import SYSTEM_PROMPT, TOOLS_SCHEMA, execute_tool


# ---------------------------------------------------------------------------
# Result types — typed containers for what the agent produces.
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    name: str
    arguments: dict
    result: dict


@dataclass
class AgentResult:
    query: str
    final_answer: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    steps: int = 0
    stop_reason: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


# ---------------------------------------------------------------------------
# The agent — ~60 lines of explicit loop.
# ---------------------------------------------------------------------------

class BaselineAgent:
    """
    The hand-rolled SDK baseline.

    One class. One method (run). One loop. If anything goes wrong, you can
    read the code top to bottom and understand exactly where.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_steps: int = 10,
    ):
        self.client = Anthropic()
        self.model = model
        self.max_steps = max_steps

    def run(self, query: str) -> AgentResult:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": query}
        ]
        result = AgentResult(query=query, final_answer="")

        for step in range(self.max_steps):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS_SCHEMA,
                messages=messages,
            )

            result.steps = step + 1
            result.stop_reason = response.stop_reason or ""
            result.input_tokens += response.usage.input_tokens
            result.output_tokens += response.usage.output_tokens

            # Append the model's turn to the conversation exactly as returned.
            messages.append({"role": "assistant", "content": response.content})

            # If Claude is done, stop.
            if response.stop_reason == "end_turn":
                # Extract the final text block — Module 3 pattern.
                for block in response.content:
                    if getattr(block, "type", None) == "text":
                        result.final_answer = block.text
                        break
                return result

            # Otherwise, we got tool_use blocks. Execute them and feed back.
            if response.stop_reason == "tool_use":
                tool_results_content: list[dict] = []
                for block in response.content:
                    if getattr(block, "type", None) != "tool_use":
                        continue
                    tool_output = execute_tool(block.name, dict(block.input))
                    result.tool_calls.append(
                        ToolCall(
                            name=block.name,
                            arguments=dict(block.input),
                            result=tool_output,
                        )
                    )
                    tool_results_content.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(tool_output),
                        }
                    )
                messages.append(
                    {"role": "user", "content": tool_results_content}
                )
                continue

            # Any other stop reason is unexpected — bail out cleanly.
            result.final_answer = (
                f"[Unexpected stop_reason: {response.stop_reason}]"
            )
            return result

        # Max steps exhausted without end_turn — also a clean exit.
        result.final_answer = "[max_steps exhausted]"
        return result