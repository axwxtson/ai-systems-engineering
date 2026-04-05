"""
Exercise 5.2: Temperature and Sampling Lab — Main CLI

Run: python3 main.py

Requires:
  pip3 install anthropic python-Levenshtein numpy colorama
  export ANTHROPIC_API_KEY="sk-ant-..."

This exercise sends the same prompts to Claude at different temperature
and top-p settings, then measures output diversity statistically.

Total API calls: 3 prompts × 4 temperatures × 10 runs = 120 calls
                + 3 prompts × 3 top-p settings × 10 runs = 90 calls
                = 210 total calls to Haiku (cheap)

Estimated cost: ~$0.05-0.10 total
Estimated time: ~5-8 minutes (with rate limit delays)
"""

import os
import sys

import anthropic
from colorama import Fore, Style, init as colorama_init

from sampling import (
    TEST_PROMPTS,
    TEMPERATURE_SETTINGS,
    run_temperature_experiment,
    run_top_p_experiment,
    MODEL,
    RUNS_PER_SETTING,
)
from analysis import analyse_experiment, calculate_experiment_cost

colorama_init()


# ─── Display Helpers ────────────────────────────────────────────────

def print_header(text: str):
    width = 80
    print(f"\n{'=' * width}")
    print(f"  {text}")
    print(f"{'=' * width}")


def print_subheader(text: str):
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print(f"{'─' * 60}")


def progress_callback(setting_label: str, run: int, total: int):
    """Print progress indicator for each API call."""
    bar_len = 20
    filled = int(bar_len * run / total)
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"\r  {setting_label:<25} [{bar}] {run}/{total}", end="", flush=True)
    if run == total:
        print()  # newline after completion


# ─── Section 1: Temperature Experiment ──────────────────────────────

def run_and_display_temperature(client: anthropic.Anthropic) -> dict:
    """
    Run temperature experiment across all prompt types and display results.
    """
    print_header("SECTION 1: TEMPERATURE EXPERIMENT")
    print(f"  Model: {MODEL}")
    print(f"  Temperatures: {TEMPERATURE_SETTINGS}")
    print(f"  Runs per setting: {RUNS_PER_SETTING}")

    all_results = {}

    for prompt_key, prompt_info in TEST_PROMPTS.items():
        print_subheader(f"Prompt Type: {prompt_info['label']}")
        print(f"  Prompt: \"{prompt_info['prompt']}\"")
        print(f"  Why: {prompt_info['why']}")
        print()

        # Run the experiment
        results = run_temperature_experiment(client, prompt_key, callback=progress_callback)
        analyses = analyse_experiment(results)
        all_results[prompt_key] = {"results": results, "analyses": analyses}

        # Display comparison table
        print(f"\n  {'Setting':<12} {'Unique':>7} {'Ratio':>7} {'Avg Edit':>9} {'Norm Edit':>10} "
              f"{'Jaccard':>8} {'Avg Len':>8} {'Len CV':>7}")
        print(f"  {'─' * 12} {'─' * 7} {'─' * 7} {'─' * 9} {'─' * 10} "
              f"{'─' * 8} {'─' * 8} {'─' * 7}")

        for setting_label, analysis in analyses.items():
            ls = analysis["length_stats"]
            # Colour code the unique ratio
            ratio = analysis["unique_ratio"]
            if ratio == 1.0:
                ratio_str = f"{Fore.GREEN}{ratio:.2f}{Style.RESET_ALL}"
            elif ratio <= 0.3:
                ratio_str = f"{Fore.RED}{ratio:.2f}{Style.RESET_ALL}"
            else:
                ratio_str = f"{Fore.YELLOW}{ratio:.2f}{Style.RESET_ALL}"

            print(f"  {setting_label:<12} {analysis['unique_count']:>7} {ratio_str:>17} "
                  f"{analysis['avg_edit_distance']:>9.1f} {analysis['normalised_edit_distance']:>10.3f} "
                  f"{analysis['avg_jaccard_similarity']:>8.3f} {ls['mean']:>8.0f} {ls['cv']:>7.3f}")

        # Show sample outputs at temp=0 and temp=1.0
        print(f"\n  Sample outputs at temp=0 (first 3 runs):")
        for i, r in enumerate(results["temp=0"][:3]):
            text = r["text"].strip()[:120]
            print(f"    Run {i+1}: {Fore.CYAN}{text}{Style.RESET_ALL}")

        print(f"\n  Sample outputs at temp=1.0 (first 3 runs):")
        for i, r in enumerate(results["temp=1.0"][:3]):
            text = r["text"].strip()[:120]
            print(f"    Run {i+1}: {Fore.YELLOW}{text}{Style.RESET_ALL}")

    return all_results


# ─── Section 2: Top-p Experiment ────────────────────────────────────

def run_and_display_top_p(client: anthropic.Anthropic) -> dict:
    """
    Run top-p experiment at fixed temperature=1.0 to isolate top-p's effect.
    """
    print_header("SECTION 2: TOP-P EXPERIMENT (temperature=1.0 fixed)")
    print(f"  Testing how top-p filtering affects diversity independently of temperature.")

    all_results = {}

    # Only run on creative prompt — that's where top-p differences are most visible
    prompt_key = "creative"
    prompt_info = TEST_PROMPTS[prompt_key]
    print_subheader(f"Prompt Type: {prompt_info['label']}")
    print(f"  Prompt: \"{prompt_info['prompt']}\"")
    print()

    results = run_top_p_experiment(client, prompt_key, callback=progress_callback)
    analyses = analyse_experiment(results)
    all_results[prompt_key] = {"results": results, "analyses": analyses}

    # Display comparison table
    print(f"\n  {'Setting':<30} {'Unique':>7} {'Ratio':>7} {'Avg Edit':>9} {'Norm Edit':>10} "
          f"{'Jaccard':>8}")
    print(f"  {'─' * 30} {'─' * 7} {'─' * 7} {'─' * 9} {'─' * 10} {'─' * 8}")

    for setting_label, analysis in analyses.items():
        ratio = analysis["unique_ratio"]
        if ratio == 1.0:
            ratio_str = f"{Fore.GREEN}{ratio:.2f}{Style.RESET_ALL}"
        elif ratio <= 0.3:
            ratio_str = f"{Fore.RED}{ratio:.2f}{Style.RESET_ALL}"
        else:
            ratio_str = f"{Fore.YELLOW}{ratio:.2f}{Style.RESET_ALL}"

        print(f"  {setting_label:<30} {analysis['unique_count']:>7} {ratio_str:>17} "
              f"{analysis['avg_edit_distance']:>9.1f} {analysis['normalised_edit_distance']:>10.3f} "
              f"{analysis['avg_jaccard_similarity']:>8.3f}")

    return all_results


# ─── Section 3: Cost Summary ───────────────────────────────────────

def display_cost_summary(temp_results: dict, top_p_results: dict):
    """Show total token usage and cost across all experiments."""
    print_header("SECTION 3: COST SUMMARY")

    total_input = 0
    total_output = 0

    for prompt_data in temp_results.values():
        cost = calculate_experiment_cost(prompt_data["analyses"])
        total_input += cost["total_input_tokens"]
        total_output += cost["total_output_tokens"]

    for prompt_data in top_p_results.values():
        cost = calculate_experiment_cost(prompt_data["analyses"])
        total_input += cost["total_input_tokens"]
        total_output += cost["total_output_tokens"]

    input_cost = (total_input / 1_000_000) * 0.80
    output_cost = (total_output / 1_000_000) * 4.00
    total_cost = input_cost + output_cost

    print(f"\n  Total input tokens:  {total_input:,}")
    print(f"  Total output tokens: {total_output:,}")
    print(f"  Input cost:          ${input_cost:.4f}")
    print(f"  Output cost:         ${output_cost:.4f}")
    print(f"  {Fore.GREEN}Total cost:            ${total_cost:.4f}{Style.RESET_ALL}")
    print(f"\n  Total API calls:     {sum(len(r) for pd in temp_results.values() for r in pd['results'].values()) + sum(len(r) for pd in top_p_results.values() for r in pd['results'].values())}")


# ─── Section 4: Recommendations ────────────────────────────────────

def display_recommendations(temp_results: dict):
    """Display practical recommendations based on observed data."""
    print_header("SECTION 4: RECOMMENDATIONS")

    recommendations = [
        (
            "Temperature 0 for structured output and tool use",
            "As expected, temperature 0 produces near-identical outputs across runs for factual "
            "questions. For your AW Analysis agent's tool calls and structured output extraction, "
            "temperature 0 is correct — any variance risks breaking JSON parsing or tool selection. "
            "The minimal variance you observe at temp=0 comes from GPU floating-point non-determinism "
            "and infrastructure-level batching effects, not from sampling."
        ),
        (
            "Temperature 0.3-0.5 for analytical tasks",
            "Analytical responses (like listing risks) benefit from a small amount of temperature "
            "to avoid repetitive phrasing across sessions, while keeping the core content consistent. "
            "For AW Analysis market commentary that users read repeatedly, slight wording variation "
            "feels more natural without sacrificing accuracy."
        ),
        (
            "Temperature 0.7-1.0 for creative content",
            "Taglines, summaries, and narrative content should use higher temperature for genuine "
            "diversity. If your AW Analysis agent generates user-facing market summaries, "
            "0.7 gives variety without incoherence."
        ),
        (
            "Top-p is a safety net, not a primary control",
            "Adjusting temperature is simpler and more predictable than tuning top-p. Use top-p=0.9 "
            "as a default safety net to prevent the model from selecting extremely unlikely tokens "
            "at high temperatures. Don't try to fine-tune both simultaneously — the interaction is "
            "hard to reason about."
        ),
        (
            "Why temperature 0 still shows variance",
            "Temperature 0 means greedy decoding (always pick the highest logit), so in theory "
            "outputs should be identical. In practice, slight differences occur because: "
            "(1) GPU floating-point arithmetic isn't bit-reproducible across different hardware "
            "or parallelism configurations, (2) the request might be routed to different GPU "
            "instances with slightly different numerical behaviour, and (3) batching with other "
            "requests can change the computation order. These effects are tiny — usually just "
            "a word or two of difference — but they mean you should never rely on exact string "
            "matching for temp=0 outputs."
        ),
    ]

    for i, (title, body) in enumerate(recommendations, 1):
        print(f"\n  {i}. {Fore.CYAN}{title}{Style.RESET_ALL}")
        words = body.split()
        line = "     "
        for word in words:
            if len(line) + len(word) + 1 > 76:
                print(line)
                line = "     " + word
            else:
                line += " " + word if line.strip() else "     " + word
        if line.strip():
            print(line)

    # Quick-reference table
    print(f"\n  {Fore.CYAN}Quick Reference:{Style.RESET_ALL}")
    print(f"\n  {'Use Case':<35} {'Temperature':>12} {'Top-p':>7}")
    print(f"  {'─' * 35} {'─' * 12} {'─' * 7}")
    print(f"  {'Tool use / JSON extraction':<35} {'0':>12} {'—':>7}")
    print(f"  {'Factual Q&A':<35} {'0':>12} {'—':>7}")
    print(f"  {'Code generation':<35} {'0–0.2':>12} {'0.95':>7}")
    print(f"  {'Market analysis (AW Analysis)':<35} {'0–0.3':>12} {'0.9':>7}")
    print(f"  {'Summarisation':<35} {'0.3–0.5':>12} {'0.9':>7}")
    print(f"  {'Creative writing / brainstorming':<35} {'0.7–1.0':>12} {'0.95':>7}")


# ─── Main ───────────────────────────────────────────────────────────

def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"{Fore.RED}Error: ANTHROPIC_API_KEY not set.{Style.RESET_ALL}")
        print("Run: export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    print(f"{Fore.CYAN}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║        Exercise 5.2: Temperature and Sampling Lab          ║")
    print("║        Module 5 — LLM Fundamentals                        ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{Style.RESET_ALL}")
    print(f"  This will make ~150 API calls to Haiku. Estimated cost: ~$0.05-0.10")
    print(f"  Estimated time: ~5-8 minutes\n")

    client = anthropic.Anthropic()

    # Section 1: Temperature experiment
    temp_results = run_and_display_temperature(client)

    # Section 2: Top-p experiment
    top_p_results = run_and_display_top_p(client)

    # Section 3: Cost summary
    display_cost_summary(temp_results, top_p_results)

    # Section 4: Recommendations
    display_recommendations(temp_results)

    print(f"\n{'=' * 80}")
    print(f"  {Fore.GREEN}Exercise 5.2 complete.{Style.RESET_ALL}")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()