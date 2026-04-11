"""Profiler — runs every (model, query) pair and collects metrics.

This is the data collection step. For each query in the golden dataset and
each candidate model, we:

1. Call the model with the analyst system prompt
2. Measure wall-clock latency
3. Record token usage and compute cost
4. Send the answer to the calibrated judge for a quality score

The output is a list of CallRecord objects, one per (model, query) pair.
That list is the raw data the routing policy is derived from.
"""

import time
from dataclasses import dataclass, asdict
from typing import Optional

import anthropic

from golden_dataset_v2 import GoldenCase
from judge import grade, JudgeResult
from pricing import cost_for_call


ANALYST_SYSTEM_PROMPT = """You are a market analyst. Answer the user's query \
clearly and concisely. Cover the substance the user is asking about. Do not \
add disclaimers or unsolicited financial advice warnings unless the user is \
asking for personal investment guidance — in which case, decline politely. \
For factual or analytical questions, give the analytical answer."""


@dataclass
class CallRecord:
    case_id: str
    query_class: str
    model: str
    answer: str
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    cost_usd: float
    quality_score: int  # 1-5 from the judge
    judge_reason: str
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def call_model(
    client: anthropic.Anthropic,
    model: str,
    query: str,
    max_tokens: int = 1024,
) -> tuple[str, int, int, float]:
    """Single Claude call. Returns (text, input_tokens, output_tokens, latency_seconds)."""
    start = time.perf_counter()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=ANALYST_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": query}],
    )
    elapsed = time.perf_counter() - start

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text, response.usage.input_tokens, response.usage.output_tokens, elapsed


def profile_case(
    client: anthropic.Anthropic,
    case: GoldenCase,
    model: str,
) -> CallRecord:
    """Run one (model, case) pair end-to-end and return a complete record."""
    try:
        answer, in_tok, out_tok, latency = call_model(client, model, case.query)
    except anthropic.APIError as e:
        return CallRecord(
            case_id=case.case_id,
            query_class=case.query_class,
            model=model,
            answer="",
            input_tokens=0,
            output_tokens=0,
            latency_seconds=0.0,
            cost_usd=0.0,
            quality_score=0,
            judge_reason="",
            error=f"{type(e).__name__}: {e}",
        )

    cost = cost_for_call(model, in_tok, out_tok)

    # Grade with the calibrated judge.
    try:
        judge_result: JudgeResult = grade(case.query, case.rubric_focus, answer)
        score = judge_result.score
        reason = judge_result.reason
    except Exception as e:  # noqa: BLE001  judge failures shouldn't kill the run
        score = 0
        reason = f"[judge error] {e}"

    return CallRecord(
        case_id=case.case_id,
        query_class=case.query_class,
        model=model,
        answer=answer,
        input_tokens=in_tok,
        output_tokens=out_tok,
        latency_seconds=latency,
        cost_usd=cost,
        quality_score=score,
        judge_reason=reason,
    )


def profile_all(
    cases: list[GoldenCase],
    models: list[str],
    progress_callback=None,
) -> list[CallRecord]:
    """Run every (model, case) pair. Returns the full list of CallRecords.

    progress_callback(record_index, total, current_record) is invoked after
    each completed call so the CLI can stream progress.
    """
    client = anthropic.Anthropic()
    records: list[CallRecord] = []
    total = len(cases) * len(models)

    idx = 0
    for case in cases:
        for model in models:
            record = profile_case(client, case, model)
            records.append(record)
            idx += 1
            if progress_callback:
                progress_callback(idx, total, record)

    return records