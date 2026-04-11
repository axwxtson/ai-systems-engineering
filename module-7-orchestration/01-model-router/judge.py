"""Calibrated LLM-as-judge for routing eval.

Reuses the Module 6 calibration pattern: a single grader model (Sonnet) scoring
a free-form output against the query and a rubric focus on a 1-5 scale.

The judge does not see which model produced the answer — that would bias the
score. It only sees query, rubric guidance, and the answer.

Score scale (matches Module 6 v1 rubric):
  5 = Excellent. Fully correct, well-reasoned, no unsupported claims.
  4 = Good. Correct, minor omissions or imprecision.
  3 = Acceptable. Substantively correct but with notable gaps or vagueness.
  2 = Weak. Partially correct but with material errors or missing core content.
  1 = Bad. Incorrect, hallucinated, or fails to address the question.
"""

import json
import re
from dataclasses import dataclass

import anthropic


# Use Sonnet as the judge — same as Module 6's calibrated v1 judge.
JUDGE_MODEL = "claude-sonnet-4-6"


JUDGE_SYSTEM_PROMPT = """You are a calibrated grader of financial market analysis answers.

You will be given:
- A user query
- A rubric guidance note describing what a good answer should cover
- An answer to grade

Score the answer on a 1-5 scale:

5 = Excellent. Fully addresses the query, factually correct, well-reasoned, \
covers the rubric points, no unsupported claims. Minor stylistic issues do not \
prevent a 5.

4 = Good. Correct and substantive, covers most rubric points, but has minor \
omissions, slight imprecision, or one small error that does not affect the \
core conclusion.

3 = Acceptable. Substantively addresses the question but with notable gaps, \
vagueness, or a missing dimension from the rubric. Still useful but visibly weaker.

2 = Weak. Partially correct but with material errors, missing core content, \
or substantial vagueness. A user relying on this answer could be misled on \
important points.

1 = Bad. Incorrect, hallucinated, off-topic, or fails to address the question \
in a meaningful way.

Be calibrated, not generous. A 5 should be reserved for genuinely strong answers. \
A 3 is the honest score for an answer that "tries but is missing things."

Respond with a JSON object only, no other text:
{"score": <1-5 integer>, "reason": "<one sentence explaining the score>"}"""


@dataclass
class JudgeResult:
    score: int
    reason: str
    raw_text: str


def grade(query: str, rubric_focus: str, answer: str) -> JudgeResult:
    """Run the calibrated judge on a single (query, answer) pair."""
    client = anthropic.Anthropic()

    user_message = (
        f"QUERY:\n{query}\n\n"
        f"RUBRIC GUIDANCE (what a good answer should cover):\n{rubric_focus}\n\n"
        f"ANSWER TO GRADE:\n{answer}"
    )

    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=300,
        system=JUDGE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = "".join(b.text for b in response.content if b.type == "text").strip()
    parsed = _parse_judge_response(raw)
    return JudgeResult(
        score=parsed["score"],
        reason=parsed["reason"],
        raw_text=raw,
    )


def _parse_judge_response(text: str) -> dict:
    """Parse the judge's JSON, with a fallback for extra text around the JSON."""
    # First try direct parse
    try:
        obj = json.loads(text)
        return {"score": int(obj["score"]), "reason": str(obj.get("reason", ""))}
    except (json.JSONDecodeError, KeyError, ValueError):
        pass

    # Fallback: find a JSON object in the text
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            return {"score": int(obj["score"]), "reason": str(obj.get("reason", ""))}
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    # Final fallback: extract a digit and label as parse failure
    digit = re.search(r"[1-5]", text)
    score = int(digit.group(0)) if digit else 3
    return {"score": score, "reason": f"[parse fallback] {text[:100]}"}