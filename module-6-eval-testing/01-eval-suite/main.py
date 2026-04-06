"""
CLI entry point for the eval suite.

Runs the full eval over the golden dataset, prints progressive results
per case, then displays an aggregated report with per-metric and
per-difficulty breakdowns. Flags regressions in red.

Usage:
    PYTHONPATH=$(pwd) python3 main.py
    PYTHONPATH=$(pwd) python3 main.py --verbose
"""

import argparse
import sys
from colorama import init, Fore, Style

from eval_runner import run_full_eval, AggregateReport, CaseResult


init(autoreset=True)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _colour_score(score) -> str:
    """Colour a 1-5 score: green >=4, yellow 3, red <=2."""
    if score is None:
        return f"{Fore.WHITE}  - {Style.RESET_ALL}"
    if score >= 4:
        colour = Fore.GREEN
    elif score == 3:
        colour = Fore.YELLOW
    else:
        colour = Fore.RED
    return f"{colour}{score}/5{Style.RESET_ALL}"


def _colour_bool(value) -> str:
    """Colour a pass/fail: green pass, red fail."""
    if value is None:
        return f"{Fore.WHITE}  - {Style.RESET_ALL}"
    if value:
        return f"{Fore.GREEN}PASS{Style.RESET_ALL}"
    return f"{Fore.RED}FAIL{Style.RESET_ALL}"


def _colour_rate(rate: float) -> str:
    """Colour a pass rate: green >=0.9, yellow 0.7-0.9, red <0.7."""
    if rate >= 0.9:
        colour = Fore.GREEN
    elif rate >= 0.7:
        colour = Fore.YELLOW
    else:
        colour = Fore.RED
    return f"{colour}{rate * 100:.1f}%{Style.RESET_ALL}"


def _colour_mean(mean: float) -> str:
    """Colour a mean 1-5 score."""
    if mean >= 4.0:
        colour = Fore.GREEN
    elif mean >= 3.0:
        colour = Fore.YELLOW
    else:
        colour = Fore.RED
    return f"{colour}{mean:.2f}/5{Style.RESET_ALL}"


# ---------------------------------------------------------------------------
# Output sections
# ---------------------------------------------------------------------------

def print_header():
    print(f"\n{Fore.CYAN}{'=' * 72}")
    print(f"  EVAL SUITE — Market Analysis System")
    print(f"{'=' * 72}{Style.RESET_ALL}\n")


def print_case_progress(idx: int, total: int, r: CaseResult):
    """Print a one-line progress indicator for each completed case."""
    if r.error:
        status = f"{Fore.RED}ERROR{Style.RESET_ALL}"
    elif r.unit_passed and r.trajectory_passed:
        # Worst of the judge scores determines colour
        judge_scores = [
            s for s in (r.faithfulness_score, r.relevance_score, r.refusal_score)
            if s is not None
        ]
        min_judge = min(judge_scores) if judge_scores else 5
        if min_judge >= 4:
            status = f"{Fore.GREEN}OK   {Style.RESET_ALL}"
        elif min_judge >= 3:
            status = f"{Fore.YELLOW}WARN {Style.RESET_ALL}"
        else:
            status = f"{Fore.RED}FAIL {Style.RESET_ALL}"
    else:
        status = f"{Fore.RED}FAIL {Style.RESET_ALL}"

    print(
        f"  [{idx:2d}/{total}] {status} "
        f"{r.case_id:<30} "
        f"U:{_colour_bool(r.unit_passed)} "
        f"T:{_colour_bool(r.trajectory_passed)} "
        f"F:{_colour_score(r.faithfulness_score)} "
        f"R:{_colour_score(r.relevance_score)} "
        f"X:{_colour_score(r.refusal_score)} "
        f"({r.latency_seconds:.1f}s)"
    )


def print_aggregate(report: AggregateReport):
    """Print the aggregate summary section."""
    print(f"\n{Fore.CYAN}{'-' * 72}")
    print(f"  AGGREGATE RESULTS")
    print(f"{'-' * 72}{Style.RESET_ALL}")

    print(f"\n  Total cases:         {report.total_cases}")
    if report.cases_with_errors:
        print(f"  {Fore.RED}Execution errors:    {report.cases_with_errors}{Style.RESET_ALL}")
    print(f"  Total latency:       {report.total_latency:.1f}s")
    print(f"  Mean latency / case: {report.mean_latency:.1f}s")

    print(f"\n  {Style.BRIGHT}Pass rates:{Style.RESET_ALL}")
    print(f"    Unit evals:        {_colour_rate(report.unit_pass_rate)}")
    print(f"    Trajectory evals:  {_colour_rate(report.trajectory_pass_rate)}")

    print(f"\n  {Style.BRIGHT}LLM-as-judge means:{Style.RESET_ALL}")
    print(f"    Faithfulness:      {_colour_mean(report.mean_faithfulness)}")
    print(f"    Relevance:         {_colour_mean(report.mean_relevance)}")
    if report.mean_refusal:
        print(f"    Refusal (refuse cases only): {_colour_mean(report.mean_refusal)}")


def print_by_difficulty(report: AggregateReport):
    """Break down results by difficulty level."""
    print(f"\n{Fore.CYAN}{'-' * 72}")
    print(f"  BY DIFFICULTY")
    print(f"{'-' * 72}{Style.RESET_ALL}\n")

    print(f"  {'Difficulty':<15} {'N':>3}  {'Unit':>8}  {'Traj':>8}  {'Faith':>10}  {'Rel':>10}")
    print(f"  {'-' * 15} {'-' * 3}  {'-' * 8}  {'-' * 8}  {'-' * 10}  {'-' * 10}")

    order = ["easy", "multi_hop", "edge", "out_of_scope", "boundary"]
    for d in order:
        if d not in report.by_difficulty:
            continue
        s = report.by_difficulty[d]
        unit_rate = s["unit_passes"] / s["count"] if s["count"] else 0
        traj_rate = s["trajectory_passes"] / s["count"] if s["count"] else 0
        print(
            f"  {d:<15} {s['count']:>3}  "
            f"{_colour_rate(unit_rate):>17}  "  # colours add ANSI chars, need wider field
            f"{_colour_rate(traj_rate):>17}  "
            f"{_colour_mean(s['mean_faithfulness']):>19}  "
            f"{_colour_mean(s['mean_relevance']):>19}"
        )


def print_regressions(report: AggregateReport):
    """List cases that failed or scored poorly on any metric."""
    print(f"\n{Fore.CYAN}{'-' * 72}")
    print(f"  REGRESSIONS / FAILURES ({len(report.regressions)})")
    print(f"{'-' * 72}{Style.RESET_ALL}\n")

    if not report.regressions:
        print(f"  {Fore.GREEN}No regressions detected.{Style.RESET_ALL}\n")
        return

    for reg in report.regressions:
        r: CaseResult = reg["result"]
        flagged = ", ".join(reg["flagged"])
        print(f"  {Fore.RED}✗{Style.RESET_ALL} {r.case_id} ({r.difficulty})")
        print(f"    Query:        {r.query}")
        print(f"    Flagged:      {flagged}")
        if r.error:
            print(f"    {Fore.RED}Error:        {r.error}{Style.RESET_ALL}")
        if r.unit_passed is False:
            print(f"    Unit reason:  {r.unit_reason}")
        if r.trajectory_passed is False:
            print(f"    Traj reason:  {r.trajectory_reason}")
        if r.faithfulness_score is not None and r.faithfulness_score <= 2:
            print(f"    Faithfulness: {r.faithfulness_score}/5 — {r.faithfulness_reasoning}")
        if r.relevance_score is not None and r.relevance_score <= 2:
            print(f"    Relevance:    {r.relevance_score}/5 — {r.relevance_reasoning}")
        if r.refusal_score is not None and r.refusal_score <= 2:
            print(f"    Refusal:      {r.refusal_score}/5 — {r.refusal_reasoning}")
        print(f"    Answer:       {r.answer[:180]}{'...' if len(r.answer) > 180 else ''}")
        print()


def print_footer(report: AggregateReport):
    """Print a final summary line and exit code guidance."""
    print(f"{Fore.CYAN}{'=' * 72}{Style.RESET_ALL}")

    # Simple 'did we pass overall' heuristic
    overall_pass = (
        report.unit_pass_rate >= 0.9
        and report.trajectory_pass_rate >= 0.8
        and report.mean_faithfulness >= 4.0
        and report.mean_relevance >= 4.0
    )
    if overall_pass:
        print(f"  {Fore.GREEN}{Style.BRIGHT}OVERALL: PASS{Style.RESET_ALL}")
    else:
        print(f"  {Fore.RED}{Style.BRIGHT}OVERALL: REVIEW NEEDED{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 72}{Style.RESET_ALL}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run the market analysis eval suite.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print tool calls during each case (slower but useful for debugging)",
    )
    args = parser.parse_args()

    print_header()
    print(f"  Running eval on golden dataset...\n")

    report = run_full_eval(
        verbose=args.verbose,
        on_case_complete=print_case_progress,
    )

    print_aggregate(report)
    print_by_difficulty(report)
    print_regressions(report)
    print_footer(report)

    # Exit non-zero if there are regressions — useful for CI integration
    if report.regressions or report.cases_with_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()