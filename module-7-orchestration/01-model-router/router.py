"""Routing policy — derives a per-class model assignment from a profile run.

The decision rule is deliberately simple and deterministic so it can be read
in code review:

    For each query class:
        1. Filter to models whose mean quality meets the QUALITY_FLOOR.
        2. From the filtered set, pick the model with the lowest mean cost.
        3. If no model meets the floor, pick the highest-quality model
           regardless of cost (don't ship garbage to save money).

v1 used a relative rule ("within tolerance of the best model"). That failed
in practice: when Opus scored 5.0 and Sonnet scored 4.5 on medium queries,
Sonnet was excluded even though 4.5 is a perfectly shippable score. The
relative rule chases the best model; the floor rule asks "is this good
enough?" — which is the actual production question.

There is no manual tuning. The full table is in code so it can be reviewed.
"""

from collections import defaultdict
from dataclasses import dataclass
from statistics import mean

from profiler import CallRecord
from pricing import display_name, MODEL_PRICES


# Minimum acceptable mean quality for a model to be considered for a class.
# 4.0 on a 1-5 scale means "good — minor omissions but substantively correct."
# Any model below this floor is excluded regardless of cost savings.
QUALITY_FLOOR = 4.0


@dataclass
class ClassStats:
    query_class: str
    model: str
    n: int
    mean_quality: float
    mean_cost: float
    p50_latency: float
    p95_latency: float


def aggregate_by_class_and_model(records: list[CallRecord]) -> list[ClassStats]:
    """Reduce raw call records to per-(class, model) summary stats."""
    grouped: dict[tuple[str, str], list[CallRecord]] = defaultdict(list)
    for r in records:
        if r.error:
            continue
        grouped[(r.query_class, r.model)].append(r)

    stats: list[ClassStats] = []
    for (cls, model), group in grouped.items():
        latencies = sorted(r.latency_seconds for r in group)
        n = len(latencies)
        p50 = latencies[n // 2] if n > 0 else 0.0
        p95_idx = max(0, int(round(0.95 * (n - 1))))
        p95 = latencies[p95_idx] if n > 0 else 0.0

        stats.append(
            ClassStats(
                query_class=cls,
                model=model,
                n=n,
                mean_quality=mean(r.quality_score for r in group),
                mean_cost=mean(r.cost_usd for r in group),
                p50_latency=p50,
                p95_latency=p95,
            )
        )
    return stats


def derive_policy(
    stats: list[ClassStats],
    quality_floor: float = QUALITY_FLOOR,
) -> dict[str, str]:
    """For each query class, pick the cheapest model that meets the quality floor.

    If no model meets the floor, pick the highest-quality model regardless of
    cost — don't ship garbage to save money.

    Returns: {query_class: model_id}
    """
    by_class: dict[str, list[ClassStats]] = defaultdict(list)
    for s in stats:
        by_class[s.query_class].append(s)

    policy: dict[str, str] = {}
    for cls, candidates in by_class.items():
        if not candidates:
            continue

        above_floor = [c for c in candidates if c.mean_quality >= quality_floor]

        if above_floor:
            # Pick the cheapest model that clears the bar.
            chosen = min(
                above_floor,
                key=lambda c: (c.mean_cost, MODEL_PRICES[c.model]["tier"]),
            )
        else:
            # Nothing meets the floor — pick highest quality as a safe default.
            chosen = max(candidates, key=lambda c: c.mean_quality)

        policy[cls] = chosen.model

    return policy


def policy_explanation(policy: dict[str, str]) -> str:
    """Human-readable description of a derived policy."""
    lines = ["Routing policy (derived from profile):"]
    for cls, model in policy.items():
        lines.append(f"  {cls:8s}  →  {display_name(model)}")
    return "\n".join(lines)


class Router:
    """Lookup-based router that uses a derived policy."""

    def __init__(self, policy: dict[str, str], default: str = "claude-sonnet-4-6"):
        self.policy = policy
        self.default = default

    def route(self, query_class: str) -> str:
        return self.policy.get(query_class, self.default)