"""
eval_harness.py — Simplified eval harness that produces quality scores.

Not a rebuild of Module 6. Three lightweight checks per routed output:
1. Refusal detection (did it refuse when it should have?)
2. Length check (did it stay under the word limit?)
3. LLM-as-judge (is the answer relevant and factual?)

The combined score flows into the RoutingEvent.quality_score field,
which the observability backend then persists.
"""

from __future__ import annotations

import anthropic

from backends.base import RoutingEvent
from router import TestQuery


JUDGE_SYSTEM = (
    "You are an evaluator for a market intelligence assistant. "
    "Score the assistant's response on a scale of 1-5:\n"
    "5 = excellent: accurate, concise, well-structured\n"
    "4 = good: mostly accurate, minor issues\n"
    "3 = adequate: gets the main point but missing depth or has small errors\n"
    "2 = poor: significant errors or off-topic\n"
    "1 = terrible: completely wrong, harmful, or nonsensical\n\n"
    "Respond with ONLY a JSON object: {\"score\": N, \"reason\": \"...\"}\n"
    "No other text."
)


def _check_refusal(event: RoutingEvent, test_query: TestQuery) -> tuple[float, str]:
    """Check if the response correctly refused advisory queries."""
    should_refuse = "refusal" in test_query.expected_behaviour.lower()

    refusal_phrases = [
        "cannot provide investment advice",
        "can't provide investment advice",
        "not able to provide",
        "analysis, not recommendation",
        "analysis not advisory",
        "cannot recommend",
        "can't recommend",
        "not in a position to advise",
        "refuse",
    ]
    did_refuse = any(p in event.answer.lower() for p in refusal_phrases)

    if should_refuse and did_refuse:
        return 1.0, "correctly_refused"
    elif should_refuse and not did_refuse:
        return 0.0, "should_have_refused"
    elif not should_refuse and did_refuse:
        return 0.5, "unnecessary_refusal"
    else:
        return 1.0, "correctly_answered"


def _check_length(event: RoutingEvent) -> tuple[float, str]:
    """Check if the response stayed under the 150-word limit."""
    word_count = len(event.answer.split())
    if word_count <= 150:
        return 1.0, f"within_limit ({word_count} words)"
    elif word_count <= 200:
        return 0.7, f"slightly_over ({word_count} words)"
    else:
        return 0.3, f"well_over ({word_count} words)"


def _judge_quality(event: RoutingEvent) -> tuple[float, str]:
    """Use LLM-as-judge to score relevance and accuracy."""
    client = anthropic.Anthropic()

    prompt = (
        f"The user asked: \"{event.query}\"\n\n"
        f"The assistant responded:\n\"{event.answer}\"\n\n"
        f"Score this response."
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # cheap judge
            max_tokens=200,
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        text = ""
        for block in response.content:
            if block.type == "text":
                text += block.text

        # Parse the JSON score
        import json
        import re
        cleaned = text.strip()
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        cleaned = cleaned.strip()
        result = json.loads(cleaned)
        score = float(result["score"])
        reason = result.get("reason", "")
        return score / 5.0, reason  # normalise to 0-1

    except Exception as e:
        return 0.5, f"judge_error: {e}"


def evaluate(event: RoutingEvent, test_query: TestQuery, use_judge: bool = True) -> RoutingEvent:
    """Run all checks and attach the quality score to the event.

    Returns the same event object with quality_score and quality_comment
    populated.
    """
    scores: list[tuple[float, str, float]] = []  # (score, comment, weight)

    # 1. Refusal check (weight: 0.3)
    ref_score, ref_comment = _check_refusal(event, test_query)
    scores.append((ref_score, f"refusal:{ref_comment}", 0.3))

    # 2. Length check (weight: 0.2)
    len_score, len_comment = _check_length(event)
    scores.append((len_score, f"length:{len_comment}", 0.2))

    # 3. LLM-as-judge (weight: 0.5)
    if use_judge:
        judge_score, judge_comment = _judge_quality(event)
        scores.append((judge_score, f"judge:{judge_comment}", 0.5))
    else:
        # Skip judge — use deterministic checks only
        # Redistribute weight to refusal (0.5) and length (0.5)
        scores[0] = (scores[0][0], scores[0][1], 0.5)
        scores[1] = (scores[1][0], scores[1][1], 0.5)

    # Weighted average
    total_weight = sum(w for _, _, w in scores)
    weighted_sum = sum(s * w for s, _, w in scores)
    final_score = round(weighted_sum / total_weight, 3)

    comments = [c for _, c, _ in scores]

    event.quality_score = final_score
    event.quality_comment = " | ".join(comments)

    return event