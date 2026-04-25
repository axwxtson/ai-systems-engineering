"""
comparison.py — produces the comparison report across all five implementations.

Outputs:
  1. A per-criterion table (printed + written to comparison_report.md)
  2. A one-paragraph "when to reach for it" note per implementation
  3. A final ranking by total score — with the important caveat that
     the ranking reflects the AW Analysis use case (Python, single
     provider, agent-heavy, Anthropic-specific features matter) and
     would change under different constraints.
"""

from pathlib import Path

from colorama import Fore, Style

from rubric import RubricScore, CRITERIA, CRITERIA_DESCRIPTIONS
from sketches import ALL_SKETCHES


def build_markdown_report(
    baseline_score: RubricScore,
    sketch_scores: list[RubricScore],
    baseline_loc: int,
) -> str:
    """Produce the markdown version of the comparison report."""
    lines: list[str] = []
    lines.append("# Framework Survey — Comparison Report\n")
    lines.append(
        "A comparison of the AW Analysis mini-agent task implemented five "
        "ways: one runnable hand-rolled Anthropic SDK baseline, and four "
        "annotated framework sketches (LangChain, LangGraph, Pydantic AI, "
        "LiteLLM).\n"
    )
    lines.append(
        "**Important caveat:** the rubric scores below reflect the AW Analysis "
        "use case — Python, single provider, agent-heavy, Anthropic-specific "
        "features matter. Under different constraints (multi-provider, "
        "TypeScript frontend, heavy integration surface) some of these scores "
        "would flip.\n"
    )

    lines.append("## Rubric criteria\n")
    for key in CRITERIA:
        lines.append(f"- **{key}** — {CRITERIA_DESCRIPTIONS[key]}")
    lines.append("")

    lines.append("## Scores\n")
    headers = (
        ["Implementation"]
        + CRITERIA
        + ["Total"]
    )
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    all_scores = [baseline_score] + sketch_scores
    for s in all_scores:
        row = [
            s.implementation,
            str(s.lines_of_code),
            str(s.dependencies),
            str(s.debuggability),
            str(s.feature_access),
            str(s.abstraction_tax),
            str(s.typing_quality),
            str(s.total),
        ]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    # Sort by total for the ranking — stable, descending.
    ranked = sorted(all_scores, key=lambda s: s.total, reverse=True)
    lines.append("## Ranked by total\n")
    for i, s in enumerate(ranked, start=1):
        lines.append(f"{i}. **{s.implementation}** — total {s.total}/30")
    lines.append("")

    lines.append("## When to reach for each\n")
    lines.append(
        f"**SDK Baseline (hand-rolled, {baseline_loc} LoC)** — "
        f"The right default for single-provider Python systems where you want "
        f"every Anthropic feature accessible, you need to debug the loop, and "
        f"you already understand the agent pattern. This is the AW Analysis "
        f"choice.\n"
    )
    for sketch in ALL_SKETCHES:
        lines.append(f"**{sketch.name}** ({sketch.layer}) — {sketch.when_to_reach}\n")

    lines.append("## Notes on the scoring\n")
    lines.append(
        "The baseline does not sweep every criterion. It loses on `typing_quality` "
        "because the raw Anthropic SDK returns content blocks that aren't fully "
        "typed at every boundary — you end up using `getattr(block, 'type', None)` "
        "in the loop. Pydantic AI scores highest on typing because typing is its "
        "raison d'être. LangGraph scores well on debuggability because the state "
        "machine is explicit even though it's still inside a framework. LiteLLM "
        "scores well on debuggability because it owns so little of the stack that "
        "the control flow is yours.\n"
    )
    lines.append(
        "The criterion that most favours the baseline is `feature_access`. "
        "Every framework on this list exposes Anthropic-specific features through "
        "escape hatches because the abstractions are provider-agnostic. For AW "
        "Analysis, where prompt caching and extended thinking are not optional, "
        "this criterion is weighted most heavily in practice even though the "
        "rubric gives every criterion equal weight.\n"
    )

    return "\n".join(lines)


def print_comparison_table(
    baseline_score: RubricScore,
    sketch_scores: list[RubricScore],
) -> None:
    """Pretty-print the comparison table with coloured output."""
    all_scores = [baseline_score] + sketch_scores

    print(Fore.CYAN + "\n" + "=" * 78)
    print(" FRAMEWORK SURVEY — COMPARISON TABLE ".center(78, "="))
    print("=" * 78 + Style.RESET_ALL)

    # Column widths
    name_w = 28
    col_w = 6

    # Header
    header = "Implementation".ljust(name_w)
    for key in CRITERIA:
        header += key[:col_w - 1].rjust(col_w)
    header += "Total".rjust(col_w + 1)
    print(Fore.YELLOW + header + Style.RESET_ALL)
    print("-" * 78)

    for s in all_scores:
        row = s.implementation[:name_w - 1].ljust(name_w)
        values = [
            s.lines_of_code,
            s.dependencies,
            s.debuggability,
            s.feature_access,
            s.abstraction_tax,
            s.typing_quality,
        ]
        for v in values:
            colour = Fore.GREEN if v >= 4 else (Fore.YELLOW if v >= 3 else Fore.RED)
            row += colour + str(v).rjust(col_w) + Style.RESET_ALL
        total_colour = Fore.GREEN if s.total >= 22 else (
            Fore.YELLOW if s.total >= 18 else Fore.RED
        )
        row += total_colour + str(s.total).rjust(col_w + 1) + Style.RESET_ALL
        print(row)
    print()

    # Ranked
    ranked = sorted(all_scores, key=lambda s: s.total, reverse=True)
    print(Fore.CYAN + "Ranked by total (AW Analysis use case):" + Style.RESET_ALL)
    for i, s in enumerate(ranked, start=1):
        print(f"  {i}. {s.implementation} — {s.total}/30")
    print()


def write_report(report_md: str, folder: Path) -> Path:
    """Write the markdown report to disk."""
    out_path = folder / "comparison_report.md"
    out_path.write_text(report_md)
    return out_path