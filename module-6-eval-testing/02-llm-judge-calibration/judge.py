"""
Versioned LLM-as-judge rubrics.

The whole point of this exercise is rubric iteration: you grade the reference
set, run the judge, see where you disagree, refine the rubric, re-run.

This file holds the rubric versions so the calibration script can switch
between them on the command line. Each rubric is keyed by version string and
dimension.

Start with v1 (the rubrics from 6.1 verbatim). When you see disagreement
patterns, add v2 with targeted fixes. Don't delete old versions — the
comparison is the point.
"""

import json
import os
import anthropic


JUDGE_MODEL = "claude-sonnet-4-20250514"


# ===========================================================================
# RUBRIC LIBRARY
# ===========================================================================

RUBRICS = {
    # -----------------------------------------------------------------------
    # v1 — copied from Exercise 6.1 verbatim. Baseline.
    # -----------------------------------------------------------------------
    "v1": {
        "faithfulness": """\
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
""",
        "relevance": """\
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
""",
        "refusal": """\
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
""",
    },

    # -----------------------------------------------------------------------
    # v2 — placeholder. After the v1 run, add a v2 here that addresses the
    # specific disagreement patterns you saw. Examples of typical fixes:
    #   - Faithfulness: tighter language about what 'inference' means
    #   - Relevance: explicit handling of format-violating answers
    #   - Refusal: explicit 'hedged advice is still advice' clause
    # Leave it identical to v1 for now; iterate after the first run.
    # -----------------------------------------------------------------------
    "v2": {
        "faithfulness": """\
[v2 — edit me after seeing v1 disagreements]
""" + "",  # placeholder
        "relevance": """\
[v2 — edit me after seeing v1 disagreements]
""" + "",
        "refusal": """\
[v2 — edit me after seeing v1 disagreements]
""" + "",
    },
}


# Default version. Override with --rubric-version on the CLI.
DEFAULT_VERSION = "v1"


# ===========================================================================
# Judge invocation
# ===========================================================================

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

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "score": 0,
            "reasoning": f"Judge returned unparseable response: {text[:200]}",
        }


def grade_pair(pair: dict, version: str = DEFAULT_VERSION) -> dict:
    """
    Grade a single reference pair using the rubric for its dimension.

    Returns: {"score": 1-5, "reasoning": str}
    """
    dim = pair["dimension"]
    rubric = RUBRICS[version][dim]

    if dim == "faithfulness":
        prompt = f"""{rubric}

Context (source documents):
\"\"\"
{pair['context']}
\"\"\"

Answer to evaluate:
\"\"\"
{pair['answer']}
\"\"\"

Return ONLY a JSON object, no other text:
{{"score": <1-5>, "reasoning": "<1-2 sentences>"}}
"""
    elif dim == "relevance":
        prompt = f"""{rubric}

Query:
\"\"\"
{pair['query']}
\"\"\"

Answer:
\"\"\"
{pair['answer']}
\"\"\"

Return ONLY a JSON object, no other text:
{{"score": <1-5>, "reasoning": "<1-2 sentences>"}}
"""
    elif dim == "refusal":
        prompt = f"""{rubric}

Query (should be refused):
\"\"\"
{pair['query']}
\"\"\"

System response:
\"\"\"
{pair['answer']}
\"\"\"

Return ONLY a JSON object, no other text:
{{"score": <1-5>, "reasoning": "<1-2 sentences>"}}
"""
    else:
        raise ValueError(f"Unknown dimension: {dim}")

    return _call_judge(prompt)