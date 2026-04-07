"""
Agreement metrics between human grades and judge grades.

Three measurements:
  1. Exact agreement: judge score == human score
  2. ±1 agreement:    |judge - human| <= 1 (the looser, more practical metric)
  3. Direction agreement: are they on the same side of the midpoint (>=4 vs <=2)
     — useful when you care about pass/fail more than the exact score

Plus per-dimension breakdowns and the confusion matrix.

Bias measurements (position bias, length bias) live in bias_tests.py and run
as separate experiments. They piggyback on the same judge but use different
input pairs.
"""

from collections import defaultdict


def exact_agreement(human: dict, judge: dict) -> float:
    """Fraction of pairs where judge score == human score."""
    common = set(human) & set(judge)
    if not common:
        return 0.0
    matches = sum(1 for k in common if human[k] == judge[k])
    return matches / len(common)


def within_one_agreement(human: dict, judge: dict) -> float:
    """Fraction of pairs where |judge - human| <= 1."""
    common = set(human) & set(judge)
    if not common:
        return 0.0
    matches = sum(1 for k in common if abs(human[k] - judge[k]) <= 1)
    return matches / len(common)


def direction_agreement(human: dict, judge: dict) -> float:
    """
    Fraction of pairs where human and judge agree on the broad verdict:
      'pass' (>=4) vs 'fail' (<=2) vs 'middle' (==3)
    Middle agrees with middle; pass agrees with pass; fail with fail.
    """
    def bucket(s: int) -> str:
        if s >= 4:
            return "pass"
        if s <= 2:
            return "fail"
        return "middle"

    common = set(human) & set(judge)
    if not common:
        return 0.0
    matches = sum(1 for k in common if bucket(human[k]) == bucket(judge[k]))
    return matches / len(common)


def per_dimension_agreement(human: dict, judge: dict, reference_set: list) -> dict:
    """Compute exact + within-one agreement per dimension."""
    by_dim: dict = defaultdict(lambda: {"human": {}, "judge": {}})

    for pair in reference_set:
        pid = pair["id"]
        if pid in human and pid in judge:
            by_dim[pair["dimension"]]["human"][pid] = human[pid]
            by_dim[pair["dimension"]]["judge"][pid] = judge[pid]

    results = {}
    for dim, scores in by_dim.items():
        results[dim] = {
            "n": len(scores["human"]),
            "exact": exact_agreement(scores["human"], scores["judge"]),
            "within_one": within_one_agreement(scores["human"], scores["judge"]),
            "direction": direction_agreement(scores["human"], scores["judge"]),
            "mean_human": sum(scores["human"].values()) / len(scores["human"]),
            "mean_judge": sum(scores["judge"].values()) / len(scores["judge"]),
        }
    return results


def confusion_matrix(human: dict, judge: dict) -> dict:
    """
    Build a 5x5 confusion matrix: matrix[human_score][judge_score] = count.
    Returns a dict-of-dicts so the printer can format it.
    """
    matrix = {h: {j: 0 for j in range(1, 6)} for h in range(1, 6)}
    for pid in set(human) & set(judge):
        h = human[pid]
        j = judge[pid]
        if 1 <= h <= 5 and 1 <= j <= 5:
            matrix[h][j] += 1
    return matrix


def find_disagreements(human: dict, judge: dict, reference_set: list, threshold: int = 1) -> list:
    """
    Return a list of pairs where |human - judge| > threshold, sorted by gap size.
    """
    disagreements = []
    pair_map = {p["id"]: p for p in reference_set}

    for pid in set(human) & set(judge):
        gap = abs(human[pid] - judge[pid])
        if gap > threshold:
            disagreements.append({
                "pair": pair_map[pid],
                "human_score": human[pid],
                "judge_score": judge[pid],
                "gap": gap,
                "direction": "judge_higher" if judge[pid] > human[pid] else "judge_lower",
            })

    disagreements.sort(key=lambda d: d["gap"], reverse=True)
    return disagreements


def signed_bias(human: dict, judge: dict) -> float:
    """
    Mean of (judge - human). Positive = judge scores higher than you on average
    (lenient bias). Negative = judge is harsher than you (strict bias).
    """
    common = set(human) & set(judge)
    if not common:
        return 0.0
    return sum(judge[k] - human[k] for k in common) / len(common)