"""
Bias experiments that piggyback on the same judge.

Two tests:
  1. POSITION BIAS — pairwise comparison: when comparing two answers, does the
     judge prefer whichever came first (or second)? We test this with a
     pairwise judge prompt that asks 'which is better: A or B?', then run the
     same comparison with the order swapped. If the judge is unbiased, the
     winner should be the same in both orderings. If position bias exists,
     one position will win disproportionately.

  2. LENGTH BIAS — same content, different verbosity: we score two answers
     that say the same thing but at different lengths. If the judge is unbiased,
     the scores should be equal (or very close). If length bias exists, the
     longer answer will score higher even though it adds nothing.

These are quick probes, not full bias studies. The point is to know whether
your judge has these biases at all, and roughly how strong they are.
"""

import json
import os
from collections import Counter
import anthropic

from judge import JUDGE_MODEL, _call_judge, RUBRICS, DEFAULT_VERSION


# ===========================================================================
# POSITION BIAS
# ===========================================================================

# Each test: a query and two answers of similar quality. We don't tell you
# which is "better" because in the position-bias test we don't care — we care
# whether the judge picks the same one regardless of order.
POSITION_TEST_CASES = [
    {
        "query": "What caused the 2022 Bitcoin crash?",
        "answer_a": (
            "Bitcoin's 2022 decline was driven by the Terra/Luna collapse in May, "
            "the FTX bankruptcy in November, and Federal Reserve rate hikes."
        ),
        "answer_b": (
            "Three main factors caused the 2022 Bitcoin crash: contagion from the "
            "Terra/Luna failure, the collapse of FTX, and aggressive Fed tightening."
        ),
    },
    {
        "query": "What is the Ethereum Merge?",
        "answer_a": (
            "The Merge was the transition of Ethereum from Proof of Work to Proof "
            "of Stake, completed in September 2022."
        ),
        "answer_b": (
            "The Ethereum Merge moved the network from Proof of Work to Proof of "
            "Stake. It happened in September 2022."
        ),
    },
    {
        "query": "Why is gold considered a safe haven?",
        "answer_a": (
            "Gold is treated as a safe haven because it holds value during currency "
            "debasement, has no counterparty risk, and tends to perform well during "
            "geopolitical and financial stress."
        ),
        "answer_b": (
            "Gold's safe-haven status comes from three properties: it preserves "
            "purchasing power against inflation, carries no issuer risk, and "
            "investors flock to it during periods of uncertainty."
        ),
    },
]


def pairwise_compare(query: str, answer_a: str, answer_b: str) -> str:
    """
    Ask the judge to pick the better of two answers. Returns 'A', 'B', or 'tie'.
    """
    prompt = f"""You are comparing two answers to the same query. Pick the better one.

Query: {query}

Answer A:
\"\"\"
{answer_a}
\"\"\"

Answer B:
\"\"\"
{answer_b}
\"\"\"

Which answer is better? Return ONLY a JSON object:
{{"winner": "A" | "B" | "tie", "reasoning": "<1 sentence>"}}
"""
    result = _call_judge(prompt)
    winner = str(result.get("winner", "tie")).upper().strip()
    if winner not in ("A", "B", "TIE"):
        return "tie"
    return winner


def run_position_bias_test() -> dict:
    """
    Run each comparison in both orderings. Tally how often the same answer wins
    regardless of position (consistent) vs flips with position (position-biased).
    """
    consistent = 0
    flipped = 0
    a_first_wins = Counter()  # 'A', 'B', 'TIE'
    b_first_wins = Counter()
    details = []

    for case in POSITION_TEST_CASES:
        # Original order: answer_a first
        winner_original = pairwise_compare(case["query"], case["answer_a"], case["answer_b"])
        a_first_wins[winner_original] += 1

        # Swapped order: answer_b first
        winner_swapped = pairwise_compare(case["query"], case["answer_b"], case["answer_a"])
        # Flip the label so we can compare like-for-like:
        # in the swapped call, "A" position contains answer_b, so a 'A' winner = b
        flipped_label = {"A": "B", "B": "A", "TIE": "TIE"}[winner_swapped]
        b_first_wins[winner_swapped] += 1

        if winner_original == flipped_label:
            consistent += 1
        else:
            flipped += 1

        details.append({
            "query": case["query"],
            "winner_when_a_first": winner_original,
            "winner_when_b_first": winner_swapped,
            "consistent": winner_original == flipped_label,
        })

    total = len(POSITION_TEST_CASES)
    return {
        "total": total,
        "consistent": consistent,
        "flipped": flipped,
        "consistency_rate": consistent / total if total else 0,
        "a_first_winners": dict(a_first_wins),
        "b_first_winners": dict(b_first_wins),
        "details": details,
    }


# ===========================================================================
# LENGTH BIAS
# ===========================================================================

# Each test: same query, same factual content, different verbosity.
# A faithful judge should give both the same score.
LENGTH_TEST_CASES = [
    {
        "query": "What caused the 2022 Bitcoin crash?",
        "context": (
            "Bitcoin fell roughly 65% in 2022. The collapse of Terra/Luna in May "
            "triggered crypto contagion. The bankruptcy of FTX in November destroyed "
            "trust in centralised exchanges. Federal Reserve rate hikes drained "
            "liquidity from risk assets throughout the year."
        ),
        "short": (
            "The 2022 Bitcoin crash was driven by the Terra/Luna collapse in May, "
            "the FTX bankruptcy in November, and Fed rate hikes."
        ),
        "long": (
            "The 2022 Bitcoin crash was driven by three major factors that played "
            "out over the course of the year. First, the collapse of Terra/Luna in "
            "May 2022 triggered widespread contagion across the crypto ecosystem, "
            "wiping out billions in value and damaging confidence in algorithmic "
            "stablecoins. Second, the bankruptcy of FTX in November 2022 destroyed "
            "trust in centralised exchanges and revealed widespread mismanagement "
            "in the industry. Third, the Federal Reserve's aggressive rate hike "
            "cycle throughout 2022 drained liquidity from risk assets generally, "
            "and Bitcoin — being correlated with tech stocks during this period — "
            "sold off alongside the broader risk-asset complex. These three factors "
            "compounded one another to drive the year's significant decline."
        ),
        "dimension": "faithfulness",
    },
    {
        "query": "What did the Ethereum Merge do?",
        "context": (
            "The Ethereum Merge completed on 15 September 2022, transitioning the "
            "network from Proof of Work to Proof of Stake. The change reduced "
            "Ethereum's energy consumption by approximately 99.95%."
        ),
        "short": (
            "The Merge moved Ethereum from Proof of Work to Proof of Stake on "
            "15 September 2022, cutting energy consumption by about 99.95%."
        ),
        "long": (
            "The Ethereum Merge was a major upgrade to the Ethereum network that "
            "completed on 15 September 2022. The core change was the transition "
            "from a Proof of Work consensus mechanism — the same one used by "
            "Bitcoin — to a Proof of Stake mechanism. Under Proof of Stake, "
            "validators secure the network by locking up ETH as collateral rather "
            "than competing to solve cryptographic puzzles. The most dramatic "
            "consequence was a reduction in the network's energy consumption "
            "by approximately 99.95%, addressing one of the longest-standing "
            "criticisms of Ethereum and of blockchain technology more broadly."
        ),
        "dimension": "faithfulness",
    },
]


def grade_with_judge(pair: dict, version: str = DEFAULT_VERSION) -> dict:
    """Score a single (query, context, answer) tuple using the faithfulness rubric."""
    rubric = RUBRICS[version]["faithfulness"]
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
    return _call_judge(prompt)


def run_length_bias_test() -> dict:
    """
    For each test case, score the short and long versions separately and
    measure the score gap. Mean gap > 0 means the judge favours longer answers.
    """
    results = []
    gaps = []

    for case in LENGTH_TEST_CASES:
        short_pair = {
            "context": case["context"],
            "answer": case["short"],
        }
        long_pair = {
            "context": case["context"],
            "answer": case["long"],
        }

        short_result = grade_with_judge(short_pair)
        long_result = grade_with_judge(long_pair)

        short_score = short_result.get("score", 0)
        long_score = long_result.get("score", 0)
        gap = long_score - short_score
        gaps.append(gap)

        results.append({
            "query": case["query"],
            "short_score": short_score,
            "long_score": long_score,
            "gap": gap,
            "short_chars": len(case["short"]),
            "long_chars": len(case["long"]),
        })

    return {
        "total": len(results),
        "mean_gap": sum(gaps) / len(gaps) if gaps else 0,
        "max_gap": max(gaps) if gaps else 0,
        "details": results,
    }   