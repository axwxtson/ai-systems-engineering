"""
CLI entry point for the calibration analysis.

Reads your human grades from human_grades.json, runs the judge over the same
reference set, computes agreement metrics, prints the report.

Two main sections:
  1. JUDGE-vs-HUMAN AGREEMENT — exact, ±1, direction agreement, confusion
     matrix, per-dimension breakdown, top disagreements
  2. BIAS TESTS — position bias and length bias probes

Optional flags:
  --rubric-version v2     Use a different rubric version (after you iterate)
  --skip-bias             Skip the bias tests (faster, cheaper)
  --skip-judge            Use cached judge grades from judge_grades.json
                          (useful when iterating on the printer without
                          re-spending API calls)

Usage:
    PYTHONPATH=$(pwd) python3 main.py
    PYTHONPATH=$(pwd) python3 main.py --skip-bias
    PYTHONPATH=$(pwd) python3 main.py --rubric-version v2
"""

import argparse
import json
import sys
from pathlib import Path
from colorama import init, Fore, Style

from reference_set import REFERENCE_SET
from judge import grade_pair, DEFAULT_VERSION, RUBRICS
from agreement import (
    exact_agreement,
    within_one_agreement,
    direction_agreement,
    per_dimension_agreement,
    confusion_matrix,
    find_disagreements,
    signed_bias,
)
from bias_tests import run_position_bias_test, run_length_bias_test


init(autoreset=True)

GRADES_FILE = Path(__file__).parent / "human_grades.json"
JUDGE_GRADES_FILE = Path(__file__).parent / "judge_grades.json"


def load_human_grades() -> dict:
    if not GRADES_FILE.exists():
        print(f"\n{Fore.RED}No human grades found.{Style.RESET_ALL}")
        print(f"Run {Fore.CYAN}python3 grade_reference_set.py{Style.RESET_ALL} first.\n")
        sys.exit(1)
    return json.loads(GRADES_FILE.read_text())


def run_judge_grades(version: str, on_progress=None) -> dict:
    """Run the judge over every pair in the reference set."""
    grades = {}
    reasonings = {}
    total = len(REFERENCE_SET)
    for idx, pair in enumerate(REFERENCE_SET, start=1):
        result = grade_pair(pair, version=version)
        score = result.get("score", 0)
        grades[pair["id"]] = score
        reasonings[pair["id"]] = result.get("reasoning", "")
        if on_progress:
            on_progress(idx, total, pair["id"], score)
    # Save for re-use
    JUDGE_GRADES_FILE.write_text(json.dumps({
        "version": version,
        "scores": grades,
        "reasonings": reasonings,
    }, indent=2))
    return grades


def load_cached_judge_grades() -> dict:
    if not JUDGE_GRADES_FILE.exists():
        print(f"\n{Fore.RED}No cached judge grades.{Style.RESET_ALL}")
        print("Remove --skip-judge to run them.\n")
        sys.exit(1)
    data = json.loads(JUDGE_GRADES_FILE.read_text())
    return data["scores"]


# ===========================================================================
# Output
# ===========================================================================

def print_header(version: str):
    print(f"\n{Fore.CYAN}{'=' * 72}")
    print(f"  LLM-as-Judge Calibration  ·  rubric version: {version}")
    print(f"{'=' * 72}{Style.RESET_ALL}\n")


def _colour_rate(rate: float, good: float = 0.8, ok: float = 0.6) -> str:
    if rate >= good:
        c = Fore.GREEN
    elif rate >= ok:
        c = Fore.YELLOW
    else:
        c = Fore.RED
    return f"{c}{rate * 100:.1f}%{Style.RESET_ALL}"


def print_judge_progress(idx: int, total: int, pair_id: str, score: int):
    print(f"  [{idx:2d}/{total}] {pair_id:<10} → judge: {score}/5")


def print_overall_agreement(human: dict, judge: dict):
    print(f"\n{Fore.CYAN}{'─' * 72}")
    print(f"  OVERALL AGREEMENT")
    print(f"{'─' * 72}{Style.RESET_ALL}\n")

    exact = exact_agreement(human, judge)
    within_one = within_one_agreement(human, judge)
    direction = direction_agreement(human, judge)
    bias = signed_bias(human, judge)

    print(f"  Exact agreement:      {_colour_rate(exact)}      (judge == human)")
    print(f"  Within ±1 agreement:  {_colour_rate(within_one)}      (|judge − human| ≤ 1)")
    print(f"  Direction agreement:  {_colour_rate(direction)}      (same pass/fail/middle bucket)")
    print()

    bias_colour = Fore.GREEN if abs(bias) < 0.3 else Fore.YELLOW if abs(bias) < 0.6 else Fore.RED
    direction_word = "lenient" if bias > 0 else "strict" if bias < 0 else "neutral"
    print(f"  Mean signed bias:     {bias_colour}{bias:+.2f}{Style.RESET_ALL}      "
          f"(judge is {direction_word} relative to you)")


def print_per_dimension(human: dict, judge: dict):
    print(f"\n{Fore.CYAN}{'─' * 72}")
    print(f"  PER-DIMENSION BREAKDOWN")
    print(f"{'─' * 72}{Style.RESET_ALL}\n")

    results = per_dimension_agreement(human, judge, REFERENCE_SET)
    print(f"  {'Dimension':<15} {'N':>3}  {'Exact':>8}  {'±1':>8}  {'Dir':>8}  {'Hμ':>5}  {'Jμ':>5}")
    print(f"  {'-' * 15} {'-' * 3}  {'-' * 8}  {'-' * 8}  {'-' * 8}  {'-' * 5}  {'-' * 5}")
    for dim in ("faithfulness", "relevance", "refusal"):
        if dim not in results:
            continue
        r = results[dim]
        print(
            f"  {dim:<15} {r['n']:>3}  "
            f"{_colour_rate(r['exact']):>17}  "
            f"{_colour_rate(r['within_one']):>17}  "
            f"{_colour_rate(r['direction']):>17}  "
            f"{r['mean_human']:>5.2f}  "
            f"{r['mean_judge']:>5.2f}"
        )


def print_confusion(human: dict, judge: dict):
    print(f"\n{Fore.CYAN}{'─' * 72}")
    print(f"  CONFUSION MATRIX  (rows: your scores · cols: judge scores)")
    print(f"{'─' * 72}{Style.RESET_ALL}\n")

    matrix = confusion_matrix(human, judge)

    print(f"        " + "  ".join(f"J{j}" for j in range(1, 6)))
    for h in range(1, 6):
        row_cells = []
        for j in range(1, 6):
            count = matrix[h][j]
            if count == 0:
                cell = f"{Style.DIM}.{Style.RESET_ALL} "
            elif h == j:
                cell = f"{Fore.GREEN}{count}{Style.RESET_ALL} "
            elif abs(h - j) == 1:
                cell = f"{Fore.YELLOW}{count}{Style.RESET_ALL} "
            else:
                cell = f"{Fore.RED}{count}{Style.RESET_ALL} "
            row_cells.append(cell)
        print(f"  H{h}    " + "  ".join(row_cells))
    print(f"\n  {Style.DIM}Diagonal = exact match. Off-diagonal-1 = within ±1. Further = significant disagreement.{Style.RESET_ALL}")


def print_disagreements(human: dict, judge: dict):
    print(f"\n{Fore.CYAN}{'─' * 72}")
    print(f"  TOP DISAGREEMENTS  (|judge − human| > 1)")
    print(f"{'─' * 72}{Style.RESET_ALL}\n")

    disagreements = find_disagreements(human, judge, REFERENCE_SET, threshold=1)

    if not disagreements:
        print(f"  {Fore.GREEN}No significant disagreements.{Style.RESET_ALL}\n")
        return

    judge_data = json.loads(JUDGE_GRADES_FILE.read_text()) if JUDGE_GRADES_FILE.exists() else {"reasonings": {}}
    judge_reasonings = judge_data.get("reasonings", {})

    for d in disagreements[:10]:
        pair = d["pair"]
        arrow = "↑" if d["direction"] == "judge_higher" else "↓"
        colour = Fore.YELLOW if d["gap"] == 2 else Fore.RED
        print(f"  {colour}{arrow} {pair['id']}{Style.RESET_ALL}  "
              f"({pair['dimension']})  "
              f"H:{d['human_score']}  J:{d['judge_score']}  "
              f"(gap {d['gap']})  target was {pair['target_score']}")
        print(f"    Query:  {pair['query']}")
        ans = pair["answer"][:140]
        if len(pair["answer"]) > 140:
            ans += "..."
        print(f"    Answer: {ans}")
        if pair["id"] in judge_reasonings:
            print(f"    {Style.DIM}Judge said: {judge_reasonings[pair['id']]}{Style.RESET_ALL}")
        print()


def print_bias_section(position_result: dict, length_result: dict):
    print(f"\n{Fore.CYAN}{'─' * 72}")
    print(f"  BIAS TESTS")
    print(f"{'─' * 72}{Style.RESET_ALL}\n")

    # Position bias
    print(f"  {Style.BRIGHT}Position bias{Style.RESET_ALL}  (pairwise comparisons run in both orderings)")
    consistency = position_result["consistency_rate"]
    consistency_colour = Fore.GREEN if consistency >= 0.8 else Fore.YELLOW if consistency >= 0.6 else Fore.RED
    print(f"    Consistency rate:  {consistency_colour}{consistency * 100:.0f}%{Style.RESET_ALL}  "
          f"({position_result['consistent']}/{position_result['total']} cases gave the same winner regardless of order)")

    if position_result["flipped"] > 0:
        print(f"    {Fore.YELLOW}{position_result['flipped']} case(s) flipped — judge has some position sensitivity.{Style.RESET_ALL}")
    else:
        print(f"    {Fore.GREEN}No flips — no detectable position bias.{Style.RESET_ALL}")

    # Length bias
    print(f"\n  {Style.BRIGHT}Length bias{Style.RESET_ALL}  (same content, short vs long version)")
    mean_gap = length_result["mean_gap"]
    gap_colour = Fore.GREEN if abs(mean_gap) < 0.3 else Fore.YELLOW if abs(mean_gap) < 0.7 else Fore.RED
    direction = "longer answers score higher" if mean_gap > 0 else "shorter answers score higher" if mean_gap < 0 else "no preference"
    print(f"    Mean score gap (long − short):  {gap_colour}{mean_gap:+.2f}{Style.RESET_ALL}  ({direction})")
    for d in length_result["details"]:
        print(f"      · {d['query'][:50]}: short={d['short_score']}/5, long={d['long_score']}/5  "
              f"({d['short_chars']} vs {d['long_chars']} chars)")


def print_footer(human: dict, judge: dict):
    within_one = within_one_agreement(human, judge)
    print(f"\n{Fore.CYAN}{'=' * 72}{Style.RESET_ALL}")
    if within_one >= 0.8:
        print(f"  {Fore.GREEN}{Style.BRIGHT}CALIBRATION PASS{Style.RESET_ALL}  "
              f"— ±1 agreement {within_one * 100:.0f}% (target ≥ 80%)")
    else:
        print(f"  {Fore.YELLOW}{Style.BRIGHT}CALIBRATION NEEDS WORK{Style.RESET_ALL}  "
              f"— ±1 agreement {within_one * 100:.0f}% (target ≥ 80%)")
        print(f"  Iterate the rubric in {Fore.CYAN}judge.py > RUBRICS['v2']{Style.RESET_ALL} and re-run with --rubric-version v2")
    print(f"{Fore.CYAN}{'=' * 72}{Style.RESET_ALL}\n")


# ===========================================================================
# Main
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description="LLM-judge calibration analysis.")
    parser.add_argument("--rubric-version", default=DEFAULT_VERSION, help="Rubric version key from judge.RUBRICS")
    parser.add_argument("--skip-bias", action="store_true", help="Skip the position/length bias tests")
    parser.add_argument("--skip-judge", action="store_true", help="Use cached judge_grades.json instead of re-running the judge")
    args = parser.parse_args()

    if args.rubric_version not in RUBRICS:
        print(f"{Fore.RED}Unknown rubric version: {args.rubric_version}{Style.RESET_ALL}")
        print(f"Available: {', '.join(RUBRICS.keys())}")
        sys.exit(1)

    print_header(args.rubric_version)

    human = load_human_grades()
    if len(human) < len(REFERENCE_SET):
        missing = len(REFERENCE_SET) - len(human)
        print(f"  {Fore.YELLOW}Note: {missing} pairs ungraded by you.{Style.RESET_ALL}")
        print(f"  Run {Fore.CYAN}python3 grade_reference_set.py{Style.RESET_ALL} to finish, "
              f"or proceed with the {len(human)} you've graded.\n")

    if args.skip_judge:
        judge = load_cached_judge_grades()
        print(f"  Loaded {len(judge)} cached judge grades.\n")
    else:
        print(f"  Running judge over {len(REFERENCE_SET)} pairs (rubric {args.rubric_version})...\n")
        judge = run_judge_grades(args.rubric_version, on_progress=print_judge_progress)

    print_overall_agreement(human, judge)
    print_per_dimension(human, judge)
    print_confusion(human, judge)
    print_disagreements(human, judge)

    if not args.skip_bias:
        print(f"\n  Running position bias test...")
        position_result = run_position_bias_test()
        print(f"  Running length bias test...")
        length_result = run_length_bias_test()
        print_bias_section(position_result, length_result)

    print_footer(human, judge)


if __name__ == "__main__":
    main()