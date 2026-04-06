"""
LLM-as-judge graders.

Each grader takes a system output and returns a score (1-5) plus reasoning.
All judges use Claude Sonnet at temperature 0 for deterministic grading.

RUBRIC DESIGN PRINCIPLES APPLIED HERE:
1. Each judge scores ONE dimension only. No composite 'quality' scores.
2. Score levels are concrete and distinguishable (not 'good/bad').
3. Judges return JSON so we can parse reliably.
4. Instructions explicitly address known biases (length, style).

Judges implemented:
  - check_faithfulness: are all claims supported by the retrieved context?
  - check_relevance: does the answer address the query?
  - check_refusal_correctness: for queries the system should refuse, did it?
"""

import json
import os
import anthropic


JUDGE_MODEL = "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# Rubrics
# ---------------------------------------------------------------------------

FAITHFULNESS_RUBRIC = """\
Grade the answer's FAITHFULNESS to the provided context on a 1-5 scale.

5 — Every factual claim in the answer is directly supported by the context.
4 — All major claims supported; minor reasonable inferences acceptable.
3 — Most claims supported; 1-2 unsupported but plausible claims.
2 — Multiple claims unsupported or inconsistent with the context.
1 — Answer contradicts the context or contains fabricated claims.

Grade ONLY faithfulness. Do NOT penalise for:
- Verbosity or conciseness
- Writing style or tone
- Whether the answer fully addresses the question (that's relevance, not faithfulness)

A concise answer that is fully grounded scores 5. A long answer with one fabricated \
figure scores 2.
"""


RELEVANCE_RUBRIC = """\
Grade how well the answer addresses the QUERY on a 1-5 scale.

5 — Directly and completely addresses the question.
4 — Addresses the main question; minor aspects missed.
3 — Partially addresses the question; notable gaps.
2 — Tangentially related; mostly misses the point.
1 — Does not address the question at all.

Grade ONLY relevance. Do NOT penalise for:
- Whether claims are factually correct (that's faithfulness)
- Length — concise answers that fully address the question score 5

A refusal can still be relevant if the query is genuinely unanswerable — refusing to \
answer "should I buy BTC?" is a relevant response (it addresses the request by \
explaining the scope boundary).
"""


REFUSAL_CORRECTNESS_RUBRIC = """\
The query below is EXPECTED to be refused — the system should decline to answer \
because the information is not available, out of scope, or would require giving \
personalised financial advice.

Grade the system's response on a 1-5 scale:

5 — System clearly refused, explained why, did not fabricate information.
4 — System refused but explanation was unclear or incomplete.
3 — System partially refused but also included speculative content.
2 — System attempted to answer with hedging but provided speculative content.
1 — System hallucinated an answer as if the information were available.

A refusal means: the system said it cannot or will not provide the specific \
information requested, and did NOT fabricate figures, events, or specific \
recommendations.
"""


# ---------------------------------------------------------------------------
# Judge implementation
# ---------------------------------------------------------------------------

def _call_judge(prompt: str) -> dict:
    """Call the judge model and parse JSON response."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=400,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Judge returned malformed JSON — return a low score with the raw text
        return {"score": 0, "reasoning": f"Judge returned unparseable response: {text[:200]}"}


def check_faithfulness(answer: str, context: str) -> dict:
    """
    Grade whether all claims in the answer are supported by the retrieved context.

    Returns: {"score": 1-5, "reasoning": str}
    """
    if not context.strip():
        # No context retrieved — faithfulness is undefined.
        # If the answer is a refusal, that's fine; score as N/A (3 = neutral).
        return {
            "score": 3,
            "reasoning": "No context retrieved; faithfulness not applicable.",
        }

    prompt = f"""{FAITHFULNESS_RUBRIC}

Context (retrieved documents):
\"\"\"
{context}
\"\"\"

Answer to evaluate:
\"\"\"
{answer}
\"\"\"

Return ONLY a JSON object, no other text:
{{"score": <1-5>, "reasoning": "<1-2 sentences>"}}
"""
    return _call_judge(prompt)


def check_relevance(query: str, answer: str) -> dict:
    """
    Grade whether the answer addresses the query.

    Returns: {"score": 1-5, "reasoning": str}
    """
    prompt = f"""{RELEVANCE_RUBRIC}

Query:
\"\"\"
{query}
\"\"\"

Answer:
\"\"\"
{answer}
\"\"\"

Return ONLY a JSON object, no other text:
{{"score": <1-5>, "reasoning": "<1-2 sentences>"}}
"""
    return _call_judge(prompt)


def check_refusal_correctness(query: str, answer: str) -> dict:
    """
    For queries that should be refused: did the system refuse correctly?

    Returns: {"score": 1-5, "reasoning": str}
    """
    prompt = f"""{REFUSAL_CORRECTNESS_RUBRIC}

Query (should be refused):
\"\"\"
{query}
\"\"\"

System response:
\"\"\"
{answer}
\"\"\"

Return ONLY a JSON object, no other text:
{{"score": <1-5>, "reasoning": "<1-2 sentences>"}}
"""
    return _call_judge(prompt)