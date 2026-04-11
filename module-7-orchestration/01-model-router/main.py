"""Exercise 7.1 — Model Router for AW Analysis.

CLI that:
  1. Profiles every (model, query) pair across the golden dataset.
  2. Builds a per-class cost/latency/quality table.
  3. Derives a routing policy from the table.
  4. Re-runs the eval with the routing policy in place (post-routing eval).
  5. Reports baseline-vs-routed comparison and flags any quality regressions.
  6. Saves all results to results.json.

Run from this directory with:
    PYTHONPATH=$(pwd) python3 main.py
"""

import json
import sys
import time
from collections import defaultdict
from statistics import mean

from colorama import Fore, Style, init

import anthropic

from golden_dataset_v2 import GOLDEN_DATASET, query_classes, by_class
from judge import grade
from pricing import MODEL_PRICES, all_models, cost_for_call, display_name
from profiler import (
    CallRecord,
    profile_all,
    profile_case,
)
from router import (
    QUALITY_FLOOR,
    Router,
    aggregate_by_class_and_model,
    derive_policy,
    policy_explanation,
)


# Quality drop greater than this between baseline and routed counts as a regression.
REGRESSION_THRESHOLD = 0.5

# The baseline is "every query goes to Sonnet" — this is what we are trying to beat
# on cost without losing per-class quality.
BASELINE_MODEL = "claude-sonnet-4-6"

# All candidate models the profiler will measure.
CANDIDATE_MODELS = all_models()  # haiku, sonnet, opus in tier order


init(autoreset=True)


# ---------- printing helpers ----------


def header(text: str) -> None:
    bar = "=" * 70
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{bar}")
    print(f"{text}")
    print(f"{bar}{Style.RESET_ALL}")


def subheader(text: str) -> None:
    print(f"\n{Fore.CYAN}{text}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'-' * len(text)}{Style.RESET_ALL}")


def success(text: str) -> None:
    print(f"{Fore.GREEN}{text}{Style.RESET_ALL}")


def warn(text: str) -> None:
    print(f"{Fore.YELLOW}{text}{Style.RESET_ALL}")


def fail(text: str) -> None:
    print(f"{Fore.RED}{text}{Style.RESET_ALL}")


def dim(text: str) -> None:
    print(f"{Style.DIM}{text}{Style.RESET_ALL}")


def colour_for_score(score: float) -> str:
    if score >= 4.5:
        return Fore.GREEN
    if score >= 3.5:
        return Fore.YELLOW
    return Fore.RED


# ---------- progress callback ----------


def make_progress_printer(label: str):
    def cb(idx: int, total: int, record: CallRecord) -> None:
        score_str = f"{record.quality_score}/5" if record.error is None else "ERR"
        score_colour = (
            colour_for_score(record.quality_score)
            if record.error is None
            else Fore.RED
        )
        print(
            f"  [{idx:3d}/{total:3d}] {label:9s}  "
            f"{display_name(record.model):11s}  "
            f"{record.case_id:9s}  "
            f"{score_colour}{score_str}{Style.RESET_ALL}  "
            f"{record.latency_seconds:5.2f}s  "
            f"${record.cost_usd:.5f}"
            f"{'  ' + Fore.RED + record.error + Style.RESET_ALL if record.error else ''}"
        )
    return cb


# ---------- table printing ----------


def print_profile_table(stats_list) -> None:
    """Print the per-class profile table."""
    subheader("Per-class profile (mean quality, mean cost, latency p50/p95)")

    by_cls: dict[str, list] = defaultdict(list)
    for s in stats_list:
        by_cls[s.query_class].append(s)

    for cls in query_classes():
        rows = sorted(
            by_cls.get(cls, []),
            key=lambda r: MODEL_PRICES[r.model]["tier"],
        )
        if not rows:
            continue

        n = rows[0].n
        print(f"\n{Style.BRIGHT}Query class: {cls}  (n={n}){Style.RESET_ALL}")
        print(
            f"  {'Model':12s}  {'Quality':>9s}  {'Cost/call':>11s}  "
            f"{'p50 lat':>9s}  {'p95 lat':>9s}"
        )
        print(f"  {'-' * 12}  {'-' * 9}  {'-' * 11}  {'-' * 9}  {'-' * 9}")
        best_quality = max(r.mean_quality for r in rows)
        for r in rows:
            q_colour = colour_for_score(r.mean_quality)
            marker = " ★" if r.mean_quality == best_quality else "  "
            print(
                f"  {display_name(r.model):12s}  "
                f"{q_colour}{r.mean_quality:6.2f}/5{Style.RESET_ALL}{marker} "
                f"${r.mean_cost:>9.5f}  "
                f"{r.p50_latency:>7.2f}s  "
                f"{r.p95_latency:>7.2f}s"
            )


def print_baseline_vs_routed(
    baseline_records: list[CallRecord],
    routed_records: list[CallRecord],
) -> dict:
    """Print and return the baseline-vs-routed comparison.

    Returns a comparison dict suitable for JSON serialisation.
    """
    subheader("Baseline (all-Sonnet) vs Routed — per-class comparison")

    def per_class_summary(records: list[CallRecord]) -> dict:
        out: dict[str, dict] = {}
        groups: dict[str, list[CallRecord]] = defaultdict(list)
        for r in records:
            if r.error:
                continue
            groups[r.query_class].append(r)
        for cls, group in groups.items():
            out[cls] = {
                "n": len(group),
                "mean_quality": mean(r.quality_score for r in group),
                "total_cost": sum(r.cost_usd for r in group),
                "mean_latency": mean(r.latency_seconds for r in group),
            }
        return out

    baseline = per_class_summary(baseline_records)
    routed = per_class_summary(routed_records)

    print(
        f"\n  {'Class':8s}  {'Baseline Q':>11s}  {'Routed Q':>9s}  "
        f"{'ΔQ':>7s}  {'Baseline $':>11s}  {'Routed $':>10s}  {'Δ$ %':>7s}"
    )
    print(
        f"  {'-' * 8}  {'-' * 11}  {'-' * 9}  {'-' * 7}  "
        f"{'-' * 11}  {'-' * 10}  {'-' * 7}"
    )

    regressions: list[dict] = []
    comparison: dict[str, dict] = {}

    for cls in query_classes():
        if cls not in baseline or cls not in routed:
            continue
        b = baseline[cls]
        r = routed[cls]
        dq = r["mean_quality"] - b["mean_quality"]
        d_cost_pct = (
            ((r["total_cost"] - b["total_cost"]) / b["total_cost"] * 100)
            if b["total_cost"] > 0 else 0.0
        )

        dq_colour = (
            Fore.RED if dq < -REGRESSION_THRESHOLD
            else (Fore.YELLOW if dq < -0.1 else Fore.GREEN)
        )
        cost_colour = Fore.GREEN if d_cost_pct < 0 else Fore.RED

        print(
            f"  {cls:8s}  "
            f"{b['mean_quality']:8.2f}/5  "
            f"{r['mean_quality']:6.2f}/5  "
            f"{dq_colour}{dq:+6.2f}{Style.RESET_ALL}  "
            f"${b['total_cost']:>9.5f}  "
            f"${r['total_cost']:>8.5f}  "
            f"{cost_colour}{d_cost_pct:+6.1f}%{Style.RESET_ALL}"
        )

        if dq < -REGRESSION_THRESHOLD:
            regressions.append(
                {
                    "query_class": cls,
                    "baseline_quality": b["mean_quality"],
                    "routed_quality": r["mean_quality"],
                    "delta": dq,
                }
            )

        comparison[cls] = {
            "baseline": b,
            "routed": r,
            "delta_quality": dq,
            "delta_cost_pct": d_cost_pct,
        }

    # Aggregate cost saving across all classes
    total_baseline_cost = sum(b["total_cost"] for b in baseline.values())
    total_routed_cost = sum(r["total_cost"] for r in routed.values())
    total_saving_pct = (
        ((total_routed_cost - total_baseline_cost) / total_baseline_cost * 100)
        if total_baseline_cost > 0 else 0.0
    )

    print(f"\n  {'-' * 8}  {'-' * 11}  {'-' * 9}  {'-' * 7}  "
          f"{'-' * 11}  {'-' * 10}  {'-' * 7}")
    cost_colour = Fore.GREEN if total_saving_pct < 0 else Fore.RED
    print(
        f"  {'TOTAL':8s}  {'':11s}  {'':9s}  {'':7s}  "
        f"${total_baseline_cost:>9.5f}  ${total_routed_cost:>8.5f}  "
        f"{cost_colour}{total_saving_pct:+6.1f}%{Style.RESET_ALL}"
    )

    return {
        "per_class": comparison,
        "total_baseline_cost": total_baseline_cost,
        "total_routed_cost": total_routed_cost,
        "total_cost_saving_pct": total_saving_pct,
        "regressions": regressions,
    }


# ---------- routed-eval runner ----------


def run_routed_eval(
    cases,
    router: Router,
    progress_callback,
) -> list[CallRecord]:
    """Re-run every case but ask the router which model to use for each one.

    This is the live routing measurement — not the same as predicting from the
    profile, because the same query can produce a different output on a fresh
    call (and a different judge score). The point is to verify that the router
    in operation behaves like the profile-based prediction.
    """
    client = anthropic.Anthropic()
    records: list[CallRecord] = []
    total = len(cases)
    for i, case in enumerate(cases, start=1):
        chosen_model = router.route(case.query_class)
        record = profile_case(client, case, chosen_model)
        records.append(record)
        if progress_callback:
            progress_callback(i, total, record)
    return records


# ---------- main ----------


def main() -> int:
    header("Exercise 7.1 — Model Router for AW Analysis")
    print(f"Golden dataset: {len(GOLDEN_DATASET)} cases across "
          f"{len(query_classes())} classes")
    print(f"Candidate models: {', '.join(display_name(m) for m in CANDIDATE_MODELS)}")
    print(f"Baseline: {display_name(BASELINE_MODEL)}")
    print(f"Quality floor: {QUALITY_FLOOR}/5 (models below this are excluded)")
    print(f"Regression threshold (Δ quality): {REGRESSION_THRESHOLD}")

    overall_start = time.perf_counter()

    # Phase 1 — profile every (model, case) pair.
    subheader("Phase 1 — Profile run (every model × every case)")
    profile_records = profile_all(
        cases=GOLDEN_DATASET,
        models=CANDIDATE_MODELS,
        progress_callback=make_progress_printer("profile"),
    )

    profile_errors = [r for r in profile_records if r.error]
    if profile_errors:
        warn(f"\n{len(profile_errors)} call(s) errored during profiling — see results.json")

    # Phase 2 — aggregate and print the per-class table.
    stats = aggregate_by_class_and_model(profile_records)
    print_profile_table(stats)

    # Phase 3 — derive routing policy.
    policy = derive_policy(stats)
    subheader("Phase 2 — Derived routing policy")
    print(policy_explanation(policy))

    router = Router(policy=policy)

    # Phase 4 — baseline + routed re-runs (live measurement).
    # Baseline = all-Sonnet, taken directly from the profile run for cost.
    baseline_records = [r for r in profile_records if r.model == BASELINE_MODEL]

    subheader("Phase 3 — Routed re-run (live router behaviour)")
    routed_records = run_routed_eval(
        cases=GOLDEN_DATASET,
        router=router,
        progress_callback=make_progress_printer("routed"),
    )

    routed_errors = [r for r in routed_records if r.error]
    if routed_errors:
        warn(f"\n{len(routed_errors)} call(s) errored during routed re-run")

    # Phase 5 — comparison.
    comparison = print_baseline_vs_routed(baseline_records, routed_records)

    # Phase 6 — verdict.
    subheader("Verdict")
    saving = -comparison["total_cost_saving_pct"]
    if comparison["regressions"]:
        fail(f"  {len(comparison['regressions'])} per-class quality regression(s) "
             f"exceed ±{REGRESSION_THRESHOLD}:")
        for reg in comparison["regressions"]:
            fail(
                f"    - {reg['query_class']}: "
                f"{reg['baseline_quality']:.2f} → {reg['routed_quality']:.2f} "
                f"(Δ {reg['delta']:+.2f})"
            )
        fail("  ROUTING POLICY NOT SHIPPABLE — investigate per-case before deploying.")
    elif saving > 0:
        success(f"  No per-class regressions. Cost saving: {saving:.1f}%.")
        success("  Routing policy is shippable.")
    else:
        warn("  No regressions, but no meaningful cost saving either. "
             "Worth re-checking the tolerance.")

    overall_elapsed = time.perf_counter() - overall_start
    total_calls = len(profile_records) + len(routed_records)
    total_cost = sum(r.cost_usd for r in profile_records) + sum(
        r.cost_usd for r in routed_records
    )
    dim(
        f"\n  {total_calls} model calls + judge calls in {overall_elapsed:.1f}s. "
        f"Total run cost ≈ ${total_cost:.4f}"
    )

    # Save everything to JSON for later inspection.
    out = {
        "config": {
            "candidate_models": CANDIDATE_MODELS,
            "baseline_model": BASELINE_MODEL,
            "quality_floor": QUALITY_FLOOR,
            "regression_threshold": REGRESSION_THRESHOLD,
        },
        "profile_records": [r.to_dict() for r in profile_records],
        "routed_records": [r.to_dict() for r in routed_records],
        "stats": [
            {
                "query_class": s.query_class,
                "model": s.model,
                "n": s.n,
                "mean_quality": s.mean_quality,
                "mean_cost": s.mean_cost,
                "p50_latency": s.p50_latency,
                "p95_latency": s.p95_latency,
            }
            for s in stats
        ],
        "policy": policy,
        "comparison": comparison,
    }
    with open("results.json", "w") as f:
        json.dump(out, f, indent=2)
    dim("  Full results saved to results.json")

    return 1 if comparison["regressions"] else 0


if __name__ == "__main__":
    sys.exit(main())