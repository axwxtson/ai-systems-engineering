"""
sketches.py — annotated framework pseudocode for the same task.

Each sketch is a Python string holding code that reflects how a given
framework would model the AW Analysis mini-agent task. The sketches are
NOT imported or executed — they exist to be read, rendered, and compared
against the baseline.

Each sketch is paired with:
  - An `annotations` block: paragraph-level commentary on what the
    framework is doing at each step, where the abstractions live, and
    what the trade-off is.
  - A `when_to_reach` note: the one-liner rule for when you'd pick this
    framework over the SDK baseline.

Reading order: start with the baseline (baseline_agent.py), then read
each sketch and compare. The point of the exercise is calibration —
you are NOT learning these frameworks to use them, you are learning
them well enough to place them on the layer map and critique them.
"""

from dataclasses import dataclass


@dataclass
class FrameworkSketch:
    name: str
    layer: str           # which stack layer(s) it owns
    code: str            # the annotated pseudocode
    annotations: str     # paragraph commentary on the sketch
    when_to_reach: str   # one-line rule

    # These feed the rubric in rubric.py
    estimated_loc: int
    estimated_deps: int
    debuggability: int   # 1 (hidden) - 5 (transparent)
    feature_access: int  # 1 (abstracted away) - 5 (fully exposed)
    abstraction_tax: int # 1 (no tax) - 5 (heavy tax)  NOTE: inverted in scoring
    typing_quality: int  # 1 (dict soup) - 5 (fully typed)


# ---------------------------------------------------------------------------
# 1. LangChain (LCEL + AgentExecutor style)
# ---------------------------------------------------------------------------

LANGCHAIN_SKETCH = FrameworkSketch(
    name="LangChain",
    layer="Layers 1, 3, 4 (provider abstraction + retrieval + agents)",
    code='''\
# LangChain sketch — AgentExecutor + tool decorator style.
# NOTE: This is pseudocode for reading, not running. LangChain's real API
# has churned across versions; this reflects the ~0.3 era shape.

from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent


# (A) Tool definitions — @tool decorator turns a Python function into a
#     LangChain Tool object. Under the hood, this inspects the function
#     signature and docstring to build the JSON schema that Claude needs.
#     The decorator is convenient but hides the schema — if you need to
#     tweak descriptions or add enums, you fight the decorator.
@tool
def get_price(ticker: str) -> dict:
    """Fetch the current price and 24h change for a ticker."""
    return execute_get_price(ticker)  # your existing impl

@tool
def search_knowledge_base(query: str) -> dict:
    """Search the AW Analysis knowledge base for recent market events."""
    return execute_search_knowledge_base(query)


# (B) Prompt template. MessagesPlaceholder("agent_scratchpad") is the
#     LangChain-specific slot where the framework injects tool-call history
#     during the loop. You do not see the scratchpad directly — it lives
#     inside the AgentExecutor.
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])


# (C) Model + agent construction. ChatAnthropic is the Layer-1 provider
#     wrapper. create_tool_calling_agent wires the prompt, model, and tools
#     into an agent runnable. AgentExecutor is the Layer-4 loop that runs
#     it until end_turn.
llm = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=1024)
agent = create_tool_calling_agent(llm, [get_price, search_knowledge_base], prompt)
executor = AgentExecutor(
    agent=agent,
    tools=[get_price, search_knowledge_base],
    max_iterations=10,
    verbose=True,
)


# (D) Invocation. Everything above was construction; this line runs the
#     loop. The result is a dict — the keys depend on the agent type and
#     the output parser.
result = executor.invoke({"input": "What's the current price of Bitcoin?"})
print(result["output"])
''',
    annotations="""\
What LangChain is doing here: the `@tool` decorator wraps each tool function
so the framework can introspect the signature and build the JSON schema
automatically. `create_tool_calling_agent` stitches the prompt, model, and
tools together into a Runnable. `AgentExecutor` is the agent loop — it
handles tool dispatch, scratchpad formatting, and iteration. In roughly 25
lines you get an agent that does what Module 3's loop did in 30.

Where the abstraction costs bite:
1. **Provider-specific features are harder to reach.** Anthropic's prompt
   caching needs `cache_control` breakpoints on specific message blocks;
   Claude's extended thinking needs a dedicated parameter. ChatAnthropic
   exposes both through escape hatches, but the LangChain community has
   to update those escape hatches every time Anthropic ships something.
2. **The scratchpad is invisible.** When the agent makes a decision you
   don't agree with, you cannot just print the message list — you have
   to hook in via callbacks or enable `verbose=True` and parse stdout.
3. **Version churn is real.** This sketch compiles on `langchain 0.3.x`
   but the 0.2 → 0.3 migration broke most `AgentExecutor` code. Anyone
   maintaining LangChain at scale has a story about this.
4. **The typing is partial.** Tools are typed via signature inspection,
   but the agent result is a loosely-typed dict, and the scratchpad
   messages are `BaseMessage` which you'll cast at every boundary.

What LangChain genuinely buys you: integration breadth. If you need to
plug in Notion, Confluence, Slack, a hundred different LLM providers, or
any of several dozen vector stores, LangChain has a pre-built integration
and you save real time. For this specific task — two tools, one model,
one agent loop — the integration advantage is zero.
""",
    when_to_reach=(
        "You need the long tail of integrations or you're prototyping fast "
        "and abstraction tax doesn't matter yet."
    ),
    estimated_loc=40,
    estimated_deps=80,  # langchain pulls a lot of transitive deps
    debuggability=2,
    feature_access=2,
    abstraction_tax=4,
    typing_quality=3,
)


# ---------------------------------------------------------------------------
# 2. LangGraph (state-machine-based agent orchestration)
# ---------------------------------------------------------------------------

LANGGRAPH_SKETCH = FrameworkSketch(
    name="LangGraph",
    layer="Layer 4 (agent orchestration, as an explicit state machine)",
    code='''\
# LangGraph sketch — StateGraph + conditional edges.
# LangGraph models the agent as a state machine: nodes update state,
# edges route between nodes based on conditions. This is what you'd
# build if you took the Module 3 agent loop and made the control flow
# a first-class object.

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.tools import tool


# (A) State schema. This is the defining idea of LangGraph — your agent's
#     entire state is a typed dict that every node reads and returns. The
#     `add_messages` reducer appends new messages to the list instead of
#     overwriting it. Once you see this, the "agent is a state machine"
#     framing clicks.
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# (B) Tools and model — same Layer-1 wrapping as LangChain.
@tool
def get_price(ticker: str) -> dict:
    """Fetch the current price and 24h change for a ticker."""
    return execute_get_price(ticker)

@tool
def search_knowledge_base(query: str) -> dict:
    """Search the AW Analysis knowledge base for recent market events."""
    return execute_search_knowledge_base(query)

tools = [get_price, search_knowledge_base]
llm = ChatAnthropic(model="claude-sonnet-4-20250514").bind_tools(tools)


# (C) Nodes. Each node is just a function (state) -> partial_state_update.
#     This is the part that feels most like the Module 3 loop — no magic,
#     just functions that you can read and unit-test.
def call_model(state: AgentState) -> dict:
    """Ask Claude what to do next, given the conversation so far."""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def call_tools(state: AgentState) -> dict:
    """Execute whichever tools the last assistant message asked for."""
    last_message = state["messages"][-1]
    outputs = []
    for tool_call in last_message.tool_calls:
        result = {"get_price": get_price, "search_knowledge_base": search_knowledge_base}[
            tool_call["name"]
        ].invoke(tool_call["args"])
        outputs.append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"],
        ))
    return {"messages": outputs}


# (D) Edges. The routing function looks at state and decides where to go
#     next. If the last message has tool calls, loop back to tools; if
#     not, we're done.
def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


# (E) Graph assembly.
graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_node("tools", call_tools)
graph.add_edge("tools", "agent")  # after tools, go back to the agent
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph.set_entry_point("agent")
app = graph.compile()


# (F) Invocation — now the agent runs as a state machine, and you can
#     snapshot state at any step, resume from a checkpoint, or inject
#     a human-in-the-loop between nodes.
from langchain_core.messages import HumanMessage
result = app.invoke({"messages": [HumanMessage(content="What's the current price of Bitcoin?")]})
print(result["messages"][-1].content)
''',
    annotations="""\
What LangGraph is doing here: the agent is modelled as an explicit state
machine. `AgentState` is the state shape, nodes are functions that update
it, edges route between nodes based on conditions. The defining feature
is that state and control flow are both first-class — you can serialise
state, resume from a checkpoint, pause for human input, or branch.

This is the framework on the list that's closest to what you'd build
yourself. If you took the Module 3 agent loop, extracted the control
flow into an explicit state machine, and named the transitions, you'd
end up somewhere near LangGraph. That's not a coincidence — the library
is a deliberate attempt to fix the old `AgentExecutor` by admitting that
agents are state machines and making the state machine legible.

What LangGraph buys you over the Module 3 loop:
1. **Checkpointing and resume.** A LangGraph agent can pause, serialise
   its state, and resume later. Doing this manually on top of the Module
   3 loop is possible but tedious. For long-running agents or for any
   human-in-the-loop workflow, this is a real feature.
2. **Multi-agent patterns.** Once the graph is explicit, you can compose
   multiple agents as subgraphs. The supervisor pattern, the committee
   pattern, and the hand-off pattern all become routine.
3. **Streaming of intermediate state.** You can stream updates per node,
   which is useful for UI where the user wants to see the agent's
   thinking in real time.

What it costs:
1. **Still pulls LangChain.** LangGraph depends on `langchain-core`, so
   you get most of LangChain's weight even if you only use LangGraph.
2. **Provider features still gated through ChatAnthropic.** Same
   Layer-1 constraint as LangChain proper.
3. **Learning curve.** The state-machine mental model is correct but
   unfamiliar to anyone whose mental model is a for-loop.

For AW Analysis specifically, the question is whether checkpointing and
multi-agent patterns are on the roadmap. If yes, LangGraph is a real
candidate. If not, the Module 3 loop is still simpler.
""",
    when_to_reach=(
        "Complex agent workflows with explicit state: checkpointing, "
        "human-in-the-loop, multi-agent supervisors, or resume-from-failure."
    ),
    estimated_loc=55,
    estimated_deps=60,
    debuggability=4,
    feature_access=3,
    abstraction_tax=3,
    typing_quality=4,
)


# ---------------------------------------------------------------------------
# 3. Pydantic AI (type-first agent framework)
# ---------------------------------------------------------------------------

PYDANTIC_AI_SKETCH = FrameworkSketch(
    name="Pydantic AI",
    layer="Layers 2, 4 (structured output + agent orchestration, type-first)",
    code='''\
# Pydantic AI sketch — type-first agent with dependency injection.
# The Pydantic team's answer to "LangChain, but Python-native."
# Prompts, tools, and outputs are all typed; the agent loop runs under
# the hood with no scratchpad gymnastics.

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel


# (A) Optional structured output type. If you declare one, the agent
#     will produce an instance of this class instead of a raw string —
#     same forcing-function trick you used in Module 1, but wrapped in
#     framework ergonomics.
class MarketAnswer(BaseModel):
    summary: str
    tickers_mentioned: list[str]
    used_tools: list[str]
    refused: bool = False


# (B) Agent construction. Model string format is "provider:model_id".
#     The system prompt is a plain string argument — no prompt templates,
#     no message placeholders, no scratchpad. This is deliberately the
#     closest thing to "just call the SDK" that any framework offers.
agent = Agent(
    "anthropic:claude-sonnet-4-20250514",
    system_prompt=SYSTEM_PROMPT,
    result_type=MarketAnswer,
)


# (C) Tools as decorated functions. The @agent.tool decorator inspects
#     the function signature and builds the JSON schema the same way
#     LangChain does, but the result is a tighter abstraction because
#     the framework owns less of the stack.
@agent.tool
async def get_price(ctx: RunContext, ticker: str) -> dict:
    """Fetch the current price and 24h change for a ticker."""
    return execute_get_price(ticker)

@agent.tool
async def search_knowledge_base(ctx: RunContext, query: str) -> dict:
    """Search the AW Analysis knowledge base for recent market events."""
    return execute_search_knowledge_base(query)


# (D) Invocation. The agent runs the loop internally; `result.data` is
#     a typed MarketAnswer, not a dict. No casting, no parsing, no
#     fragile attribute-lookup dance.
result = await agent.run("What's the current price of Bitcoin?")
print(result.data.summary)
print(result.data.tickers_mentioned)
''',
    annotations="""\
What Pydantic AI is doing here: it wraps the Module 1 "tool use as forcing
function" trick and the Module 3 agent loop in a type-first API. The
structured output type is a Pydantic model. Tools are decorated functions.
The agent loop runs internally. Everything is typed end-to-end and the
compiler actually helps you at every boundary.

This is the framework I'd evaluate most seriously for a Python-only
greenfield project. It's the closest thing to "the SDK, with nice edges"
of any framework on this list. The abstraction is thin enough that you
can read the source in an afternoon and understand exactly what it does.

Strengths:
1. **Typing is first-class, not bolted on.** The `result_type` pattern
   gives you a typed instance without manual parsing. Tools' input types
   come from function signatures and are enforced.
2. **Small surface area.** The public API is about a dozen classes and
   functions. Compare that to LangChain's hundreds.
3. **Python-native feel.** No prompt templates, no message placeholders,
   no scratchpad. It reads like normal Python.
4. **Active and well-maintained.** The Pydantic team writes Pydantic AI;
   there's no second-class maintenance status.

Weaknesses:
1. **Newer and less battle-tested.** Fewer production war stories than
   LangChain or LlamaIndex. Fewer Stack Overflow answers when something
   goes wrong.
2. **Python only.** No TypeScript port. If you need a full-stack typed
   experience, you're still reaching for Vercel AI SDK on the frontend.
3. **Provider-specific features still constrained.** Same Layer-1 issue:
   Anthropic's extended thinking and prompt caching are exposed through
   escape hatches because the abstraction is provider-agnostic.
4. **The agent loop is hidden.** For the Module 8 "read the loop" reflex,
   this is mildly uncomfortable — you can't just `print(messages)` without
   dropping into library internals.

For AW Analysis, Pydantic AI is the closest real-world alternative to the
baseline. If you were starting today without Module 3's loop already
written, it would be worth a two-day spike.
""",
    when_to_reach=(
        "Python-only greenfield where you want typed agent ergonomics "
        "without LangChain's surface area."
    ),
    estimated_loc=30,
    estimated_deps=10,
    debuggability=3,
    feature_access=3,
    abstraction_tax=2,
    typing_quality=5,
)


# ---------------------------------------------------------------------------
# 4. LiteLLM (pure Layer-1 provider abstraction)
# ---------------------------------------------------------------------------

LITELLM_SKETCH = FrameworkSketch(
    name="LiteLLM",
    layer="Layer 1 only (provider abstraction across ~100 backends)",
    code='''\
# LiteLLM sketch — provider abstraction, no agent layer.
# LiteLLM owns exactly one layer: Layer 1. You still write the agent
# loop yourself, exactly like the Module 3 + Module 7 baseline. The only
# thing that changes is the call site — instead of anthropic.messages.create,
# you call litellm.completion with an OpenAI-shaped interface that routes
# to any of ~100 backends.

import litellm
from tasks import SYSTEM_PROMPT, TOOLS_SCHEMA, execute_tool


# (A) Tool schema conversion. LiteLLM uses the OpenAI tool-schema shape,
#     which is slightly different from Anthropic's native shape. For the
#     AW Analysis tools the conversion is mechanical.
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        },
    }
    for t in TOOLS_SCHEMA
]


# (B) The loop — almost identical to the SDK baseline.
def run_litellm_agent(query: str, model: str = "anthropic/claude-sonnet-4-20250514"):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]

    for step in range(10):
        response = litellm.completion(
            model=model,
            messages=messages,
            tools=OPENAI_TOOLS,
            tool_choice="auto",
            max_tokens=1024,
        )

        choice = response.choices[0]
        messages.append(choice.message.model_dump())

        if choice.finish_reason == "stop":
            return choice.message.content

        if choice.finish_reason == "tool_calls":
            for tc in choice.message.tool_calls:
                args = json.loads(tc.function.arguments)
                result = execute_tool(tc.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })
            continue

        return f"[Unexpected finish_reason: {choice.finish_reason}]"

    return "[max_steps exhausted]"


# (C) Swap providers by changing one string. This is the entire value
#     proposition: the loop, the tools, the messages — all unchanged.
#     `openai/gpt-4o`, `google/gemini-2.5-pro`, `mistral/large-latest`
#     all work with the same code path.
print(run_litellm_agent("What's the current price of Bitcoin?", model="anthropic/claude-sonnet-4-20250514"))
print(run_litellm_agent("What's the current price of Bitcoin?", model="openai/gpt-4o"))
''',
    annotations="""\
What LiteLLM is doing here: it owns exactly one layer — provider
abstraction — and nothing else. There's no agent loop, no prompt
template, no retrieval interface. You write the loop yourself, and
LiteLLM gives you a single `completion()` function that talks to about
a hundred LLM providers behind an OpenAI-shaped interface.

This is the purest example of the "reach for a framework when it owns
a layer you don't want to own" rule. If your product genuinely needs
multi-provider support — customer choice, geographic availability,
pricing leverage, or A/B testing between providers — LiteLLM is the
right tool. You keep every other layer of your stack exactly as it was.

The comparison to your Module 7 Exercise 7.2 fallback chain is the
interesting one. LiteLLM's Router class does roughly what you built:
model list, fallbacks, retry budgets, rate-limit handling. The
abstractions are strikingly similar — links, attempts, per-type retry
policies — which is reassuring because it means your Module 7 code
lives in a well-trodden design space rather than a one-off invention.

Strengths:
1. **Narrow scope, narrow problem.** Owns one layer, does it well.
2. **Huge provider coverage.** ~100 backends, actively maintained.
3. **The router is solid.** Built-in load balancing, fallbacks, rate
   limit handling, and retry logic.
4. **Works alongside anything.** Since it owns so little of the stack,
   you can drop it into an existing codebase without rearchitecting.

Weaknesses:
1. **OpenAI-shaped interface.** Tool schemas, message shapes, and finish
   reasons follow OpenAI's conventions, which means Anthropic-specific
   shapes need conversion at every boundary.
2. **Provider-specific features are escape hatches.** Prompt caching,
   extended thinking, and Anthropic's cache-aware token counts all need
   pass-through parameters, and some features are lost in translation.
3. **No agent abstraction.** You still write the loop. This is also a
   strength, depending on whose perspective you're taking.

For AW Analysis: the right rule is "use LiteLLM only if multi-provider
becomes a real requirement." If it ever does, the Module 7 fallback chain
can be swapped for the LiteLLM router in a day.
""",
    when_to_reach=(
        "You have a real multi-provider requirement — customer choice, "
        "geographic availability, or pricing leverage across backends."
    ),
    estimated_loc=35,
    estimated_deps=25,
    debuggability=4,
    feature_access=3,
    abstraction_tax=2,
    typing_quality=3,
)


# ---------------------------------------------------------------------------
# Master list for iteration.
# ---------------------------------------------------------------------------

ALL_SKETCHES: list[FrameworkSketch] = [
    LANGCHAIN_SKETCH,
    LANGGRAPH_SKETCH,
    PYDANTIC_AI_SKETCH,
    LITELLM_SKETCH,
]