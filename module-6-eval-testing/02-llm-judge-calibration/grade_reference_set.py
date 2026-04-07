"""
Interactive human grading CLI.

Walks you through the 30 reference pairs one at a time. For each pair you see:
  - The dimension being graded (faithfulness / relevance / refusal)
  - The query
  - The context (faithfulness only)
  - The answer
  - The dimension's rubric (so you grade against the same standard the judge will)

You enter a score 1-5. After scoring, the teaching note is revealed so you can
sanity-check your reasoning. Your scores get saved to human_grades.json
incrementally — if you ctrl+C halfway through, your progress is saved.

Re-running picks up where you left off. To regrade a pair, delete its entry
from human_grades.json or use --regrade <pair_id>.

Usage:
    PYTHONPATH=$(pwd) python3 grade_reference_set.py
    PYTHONPATH=$(pwd) python3 grade_reference_set.py --regrade faith_03
    PYTHONPATH=$(pwd) python3 grade_reference_set.py --restart
"""

import argparse
import json
import os
import sys
from pathlib import Path
from colorama import init, Fore, Style

from reference_set import REFERENCE_SET
from judge import RUBRICS, DEFAULT_VERSION


init(autoreset=True)

GRADES_FILE = Path(__file__).parent / "human_grades.json"


def load_grades() -> dict:
    if GRADES_FILE.exists():
        return json.loads(GRADES_FILE.read_text())
    return {}


def save_grades(grades: dict) -> None:
    GRADES_FILE.write_text(json.dumps(grades, indent=2))


def print_header():
    print(f"\n{Fore.CYAN}{'=' * 72}")
    print(f"  HUMAN GRADING — LLM-as-Judge Calibration Reference Set")
    print(f"{'=' * 72}{Style.RESET_ALL}\n")


def print_progress(done: int, total: int):
    bar_width = 40
    filled = int(bar_width * done / total) if total else 0
    bar = "█" * filled + "░" * (bar_width - filled)
    print(f"  Progress: [{Fore.GREEN}{bar}{Style.RESET_ALL}] {done}/{total}\n")


def print_pair(pair: dict, index: int, total: int):
    """Display a pair for grading."""
    dim = pair["dimension"]
    dim_colour = {
        "faithfulness": Fore.MAGENTA,
        "relevance": Fore.BLUE,
        "refusal": Fore.YELLOW,
    }[dim]

    print(f"{Fore.CYAN}{'─' * 72}{Style.RESET_ALL}")
    print(f"  {Style.BRIGHT}Pair {index}/{total}{Style.RESET_ALL}  "
          f"id: {pair['id']}  "
          f"dimension: {dim_colour}{dim}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'─' * 72}{Style.RESET_ALL}\n")

    print(f"  {Style.BRIGHT}Query:{Style.RESET_ALL}")
    print(f"    {pair['query']}\n")

    if pair["context"]:
        print(f"  {Style.BRIGHT}Context:{Style.RESET_ALL}")
        for line in _wrap(pair["context"], 68):
            print(f"    {line}")
        print()

    print(f"  {Style.BRIGHT}Answer to grade:{Style.RESET_ALL}")
    for line in _wrap(pair["answer"], 68):
        print(f"    {line}")
    print()


def print_rubric(dimension: str):
    """Print the rubric the judge will use, so you grade against the same standard."""
    rubric = RUBRICS[DEFAULT_VERSION][dimension]
    print(f"  {Style.DIM}{Fore.WHITE}── Rubric ─────────────────────────────────────────────────{Style.RESET_ALL}")
    for line in rubric.strip().split("\n"):
        print(f"  {Style.DIM}{Fore.WHITE}{line}{Style.RESET_ALL}")
    print(f"  {Style.DIM}{Fore.WHITE}───────────────────────────────────────────────────────────{Style.RESET_ALL}\n")


def get_score() -> int:
    """Prompt for a score 1-5."""
    while True:
        try:
            raw = input(f"  {Style.BRIGHT}Your score (1-5, or 'q' to quit): {Style.RESET_ALL}").strip().lower()
            if raw in ("q", "quit", "exit"):
                print(f"\n  {Fore.YELLOW}Progress saved. Re-run to continue.{Style.RESET_ALL}\n")
                sys.exit(0)
            score = int(raw)
            if 1 <= score <= 5:
                return score
            print(f"  {Fore.RED}Score must be 1-5.{Style.RESET_ALL}")
        except ValueError:
            print(f"  {Fore.RED}Enter a number 1-5.{Style.RESET_ALL}")


def reveal_note(pair: dict, your_score: int):
    """Show the teaching note after grading."""
    target = pair["target_score"]
    delta = your_score - target

    if delta == 0:
        marker = f"{Fore.GREEN}✓ matches target{Style.RESET_ALL}"
    elif abs(delta) == 1:
        marker = f"{Fore.YELLOW}± 1 from target ({target}){Style.RESET_ALL}"
    else:
        marker = f"{Fore.RED}{delta:+d} from target ({target}){Style.RESET_ALL}"

    print(f"\n  {Style.BRIGHT}Your score: {your_score}{Style.RESET_ALL}  {marker}")
    print(f"\n  {Style.DIM}── Teaching note ─────────────────────────────────────────{Style.RESET_ALL}")
    for line in _wrap(pair["teaching_note"], 68):
        print(f"  {Style.DIM}{line}{Style.RESET_ALL}")
    print(f"  {Style.DIM}──────────────────────────────────────────────────────────{Style.RESET_ALL}\n")

    input(f"  {Style.DIM}Press Enter to continue...{Style.RESET_ALL}")
    print()


def _wrap(text: str, width: int) -> list[str]:
    """Naive word-wrap for display."""
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def main():
    parser = argparse.ArgumentParser(description="Grade the LLM-judge reference set.")
    parser.add_argument("--regrade", type=str, help="Regrade a single pair by id")
    parser.add_argument("--restart", action="store_true", help="Delete all grades and start over")
    args = parser.parse_args()

    if args.restart:
        if GRADES_FILE.exists():
            confirm = input(f"{Fore.RED}Delete all existing grades? [y/N]: {Style.RESET_ALL}")
            if confirm.lower() == "y":
                GRADES_FILE.unlink()
                print(f"{Fore.YELLOW}Grades deleted.{Style.RESET_ALL}")
            else:
                print("Aborted.")
                return

    grades = load_grades()
    print_header()

    if args.regrade:
        try:
            pair = next(p for p in REFERENCE_SET if p["id"] == args.regrade)
        except StopIteration:
            print(f"{Fore.RED}No pair with id '{args.regrade}'{Style.RESET_ALL}")
            return

        print_pair(pair, 1, 1)
        print_rubric(pair["dimension"])
        score = get_score()
        grades[pair["id"]] = score
        save_grades(grades)
        reveal_note(pair, score)
        print(f"{Fore.GREEN}Regrade saved.{Style.RESET_ALL}\n")
        return

    total = len(REFERENCE_SET)
    done = sum(1 for p in REFERENCE_SET if p["id"] in grades)
    print_progress(done, total)

    if done == total:
        print(f"  {Fore.GREEN}All {total} pairs already graded.{Style.RESET_ALL}")
        print(f"  Run {Fore.CYAN}main.py{Style.RESET_ALL} to compare against the judge.")
        print(f"  Use {Fore.CYAN}--regrade <id>{Style.RESET_ALL} to change a single grade.")
        print(f"  Use {Fore.CYAN}--restart{Style.RESET_ALL} to start over.\n")
        return

    for idx, pair in enumerate(REFERENCE_SET, start=1):
        if pair["id"] in grades:
            continue

        print_pair(pair, idx, total)
        print_rubric(pair["dimension"])
        score = get_score()
        grades[pair["id"]] = score
        save_grades(grades)
        reveal_note(pair, score)

    print(f"\n{Fore.GREEN}{'=' * 72}")
    print(f"  All {total} pairs graded. Grades saved to human_grades.json")
    print(f"{'=' * 72}{Style.RESET_ALL}")
    print(f"\n  Next: run {Fore.CYAN}python3 main.py{Style.RESET_ALL} to compare your grades")
    print(f"  against the judge and see calibration results.\n")


if __name__ == "__main__":
    main()