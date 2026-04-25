"""
main.py — CLI entry point for the framework survey.

Workflow:
  1. Run the hand-rolled SDK baseline against all 5 test queries.
  2. Render each framework sketch with its annotations.
  3. Score every implementation against the rubric.
  4. Print the comparison table to stdout and write comparison_report.md.

Exit code 0 on successful baseline runs, 1 on baseline failure.
The framework sketches don't run, so they never affect exit code.

Usage:
  PYTHONPATH=$(pwd) python3 main.py           # full run
  PYTHONPATH=$(pwd) python3 main.py --no-baseline   # skip the API calls
  PYTHONPATH=$(pwd) python3 main.py --only-sketches # just render sketches
"""

import argparse
import sys
from pathlib import Path

from colorama import Fore, Style, init as colorama_init

from baseline_agent import BaselineAgent
from tasks import TEST_QUERIES
from sketches import ALL_SKETCHES
from rubric import score_baseline, score_sketch
from comparison import build_markdown_report, print_comparison_table, write_report


def count_baseline_loc() -> int:
    """Count non-blank, non-comment lines in baseline_agent.py for the rubric."""
    path = Path(__file__).parent / "baseline_agent.py"
    count = 0
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        count += 1
    return count


def run_baseline() -> bool:
    """Run the baseline agent against all test queries. Returns True if all succeed."""
    print(Fore.CYAN + "\n" + "=" * 78)
    print(" HAND-ROLLED SDK BASELINE ".center(78, "="))
    print("=" * 78 + Style.RESET_ALL)
    print(
        Fore.WHITE
        + "\nRunning the baseline agent against 5 test queries. This is the "
        + "reference\nimplementation — the one that actually makes API calls.\n"
        + Style.RESET_ALL
    )

    agent = BaselineAgent()
    all_ok = True

    for tq in TEST_QUERIES:
        print(Fore.YELLOW + f"[{tq.qid}] ({tq.difficulty})" + Style.RESET_ALL)
        print(Fore.WHITE + f"  Query: {tq.query}" + Style.RESET_ALL)
        print(Fore.WHITE + f"  Expected: {tq.expected_pattern}" + Style.RESET_ALL)
        try:
            result = agent.run(tq.query)
            print(Fore.GREEN + f"  Steps: {result.steps}   "
                  f"Tool calls: {len(result.tool_calls)}   "
                  f"Tokens in/out: {result.input_tokens}/{result.output_tokens}"
                  + Style.RESET_ALL)
            if result.tool_calls:
                for tc in result.tool_calls:
                    print(Fore.BLUE + f"    -> {tc.name}({tc.arguments})" + Style.RESET_ALL)
            # Truncate answer for readability
            answer_preview = result.final_answer.replace("\n", " ")
            if len(answer_preview) > 200:
                answer_preview = answer_preview[:197] + "..."
            print(Fore.WHITE + f"  Answer: {answer_preview}" + Style.RESET_ALL)
            print()
        except Exception as exc:
            print(Fore.RED + f"  FAILED: {exc}" + Style.RESET_ALL)
            all_ok = False
            print()

    return all_ok


def render_sketches() -> None:
    """Pretty-print each framework sketch with annotations."""
    print(Fore.CYAN + "\n" + "=" * 78)
    print(" FRAMEWORK SKETCHES ".center(78, "="))
    print("=" * 78 + Style.RESET_ALL)
    print(
        Fore.WHITE
        + "\nFour annotated framework pseudocode sketches. These are NOT "
        + "executed —\nthey exist to be read, compared, and critiqued "
        + "against the baseline.\n"
        + Style.RESET_ALL
    )

    for sketch in ALL_SKETCHES:
        print(Fore.MAGENTA + "\n" + "=" * 78 + Style.RESET_ALL)
        print(Fore.MAGENTA + f" {sketch.name} ".center(78, "=") + Style.RESET_ALL)
        print(Fore.MAGENTA + "=" * 78 + Style.RESET_ALL)
        print(Fore.YELLOW + f"\nLayer: {sketch.layer}" + Style.RESET_ALL)
        print(Fore.YELLOW + f"When to reach for it: {sketch.when_to_reach}\n"
              + Style.RESET_ALL)

        print(Fore.CYAN + "--- CODE ---" + Style.RESET_ALL)
        print(sketch.code)

        print(Fore.CYAN + "--- ANNOTATIONS ---" + Style.RESET_ALL)
        print(sketch.annotations)


def main() -> int:
    colorama_init()
    parser = argparse.ArgumentParser(description="Framework survey comparison tool")
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="Skip running the live baseline agent (no API calls)",
    )
    parser.add_argument(
        "--only-sketches",
        action="store_true",
        help="Only render framework sketches, skip baseline and comparison",
    )
    args = parser.parse_args()

    baseline_loc = count_baseline_loc()
    print(Fore.CYAN + Style.BRIGHT + "\n"
          + "Exercise 8.1: Framework Survey".center(78)
          + Style.RESET_ALL)
    print(Fore.WHITE + (
        "Comparing the same AW Analysis mini-agent across five implementations:\n"
        "1. Hand-rolled Anthropic SDK baseline (runnable)\n"
        "2. LangChain sketch (annotated pseudocode)\n"
        "3. LangGraph sketch (annotated pseudocode)\n"
        "4. Pydantic AI sketch (annotated pseudocode)\n"
        "5. LiteLLM sketch (annotated pseudocode)\n"
    ) + Style.RESET_ALL)
    print(Fore.WHITE + f"Baseline LoC (non-blank, non-comment): {baseline_loc}"
          + Style.RESET_ALL)

    baseline_ok = True
    if not args.no_baseline and not args.only_sketches:
        baseline_ok = run_baseline()
        if baseline_ok:
            print(Fore.GREEN + "Baseline: all queries succeeded."
                  + Style.RESET_ALL)
        else:
            print(Fore.RED + "Baseline: one or more queries failed."
                  + Style.RESET_ALL)

    render_sketches()

    if args.only_sketches:
        print(Fore.YELLOW + "\n[--only-sketches] Skipping comparison report."
              + Style.RESET_ALL)
        return 0

    # Build rubric scores
    baseline_score = score_baseline(baseline_loc)
    sketch_scores = [score_sketch(s) for s in ALL_SKETCHES]

    # Print the comparison table
    print_comparison_table(baseline_score, sketch_scores)

    # Write the markdown report
    report_md = build_markdown_report(baseline_score, sketch_scores, baseline_loc)
    out_path = write_report(report_md, Path(__file__).parent)
    print(Fore.GREEN + f"Comparison report written to: {out_path}"
          + Style.RESET_ALL)

    return 0 if baseline_ok else 1


if __name__ == "__main__":
    sys.exit(main())