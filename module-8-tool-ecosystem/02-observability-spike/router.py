"""
router.py — Simplified Module 7 router with emit hooks.

A deterministic routing policy: easy → Haiku, medium → Sonnet,
hard → Sonnet (with escalation to Opus on failure). The policy is
deliberately simple because the exercise is about the observability
layer, not the routing logic.

Every routing decision emits a RoutingEvent through the Emitter.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

import anthropic

from backends.base import RoutingEvent
from emit import Emitter
from pricing import compute_cost, MODEL_ALIASES


# --- Routing policy ---

ROUTING_POLICY: dict[str, str] = {
    "easy": "haiku",
    "medium": "sonnet",
    "hard": "sonnet",
}

SYSTEM_PROMPT = (
    "You are an AW Analysis market intelligence assistant. "
    "Provide concise, factual analysis. Use British English spelling. "
    "If asked for investment advice, refuse and explain you provide "
    "analysis, not recommendations. Keep responses under 150 words."
)


# --- Query dataset ---

@dataclass
class TestQuery:
    id: str
    query: str
    query_class: str  # easy / medium / hard
    expected_behaviour: str


TEST_QUERIES: list[TestQuery] = [
    TestQuery(
        id="q1_price",
        query="What is the current price of Bitcoin?",
        query_class="easy",
        expected_behaviour="Short factual answer, no analysis needed",
    ),
    TestQuery(
        id="q2_summary",
        query="Summarise the key themes from today's European market session.",
        query_class="medium",
        expected_behaviour="Multi-point summary requiring synthesis",
    ),
    TestQuery(
        id="q3_refusal",
        query="Should I sell all my Tesla shares right now?",
        query_class="easy",
        expected_behaviour="Refusal — analysis not advisory",
    ),
    TestQuery(
        id="q4_synthesis",
        query=(
            "Compare the macro implications of the latest US CPI print "
            "for both crypto markets and traditional equities. Consider "
            "the Fed's likely response and historical precedent."
        ),
        query_class="hard",
        expected_behaviour="Multi-factor synthesis across asset classes",
    ),
    TestQuery(
        id="q5_formatting",
        query=(
            "Give me a table comparing Apple, Microsoft, and Google on: "
            "P/E ratio, market cap, and YTD performance."
        ),
        query_class="medium",
        expected_behaviour="Structured table output with specific data points",
    ),
    TestQuery(
        id="q6_simple",
        query="What does RSI stand for in technical analysis?",
        query_class="easy",
        expected_behaviour="One-line definition",
    ),
]


# --- Router ---

class Router:
    """Routes queries to models based on query class, emitting events."""

    def __init__(self, emitter: Emitter, session_id: str | None = None) -> None:
        self._client = anthropic.Anthropic()
        self._emitter = emitter
        self._session_id = session_id or f"session-{uuid.uuid4().hex[:8]}"

    def route(self, test_query: TestQuery) -> RoutingEvent:
        """Route a query, call the model, emit the event, return it."""

        # 1. Routing decision
        alias = ROUTING_POLICY.get(test_query.query_class, "sonnet")
        model = MODEL_ALIASES[alias]
        decision = f"policy:{test_query.query_class}→{alias}"

        # 2. Call the model
        start = time.perf_counter()
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": test_query.query}],
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            answer = ""
            for block in response.content:
                if block.type == "text":
                    answer += block.text

            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = compute_cost(model, input_tokens, output_tokens)

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            answer = f"[ERROR: {e}]"
            input_tokens = 0
            output_tokens = 0
            cost = 0.0
            decision = f"error:{type(e).__name__}"

        # 3. Build and emit the event
        event = RoutingEvent(
            trace_id=uuid.uuid4().hex,
            query=test_query.query,
            query_class=test_query.query_class,
            model=model,
            routing_decision=decision,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(elapsed_ms, 1),
            cost_usd=round(cost, 6),
            answer=answer,
            session_id=self._session_id,
            tags=[test_query.query_class, test_query.id],
        )

        self._emitter.emit(event)
        return event

    def run_all(self, queries: list[TestQuery] | None = None) -> list[RoutingEvent]:
        """Route all test queries and return the events."""
        targets = queries or TEST_QUERIES
        events = []
        for tq in targets:
            event = self.route(tq)
            events.append(event)
        return events