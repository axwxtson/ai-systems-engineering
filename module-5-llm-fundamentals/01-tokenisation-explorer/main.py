"""
Exercise 5.1: Tokenisation Explorer — Main CLI

Run: python3 main.py

Requires:
  pip3 install anthropic tiktoken colorama
  export ANTHROPIC_API_KEY="sk-ant-..."
"""

import os
import sys

import anthropic
from colorama import Fore, Style, init as colorama_init

from tokeniser import TEST_TEXTS, compare_tokenisation, get_tiktoken_tokens
from cost_calculator import cost_comparison_table, calculate_cost

# Initialise colorama for cross-platform colour support
colorama_init()


# ─── Display Helpers ────────────────────────────────────────────────

# Colour palette for alternating token colours in boundary visualisation
TOKEN_COLOURS = [Fore.CYAN, Fore.YELLOW, Fore.GREEN, Fore.MAGENTA, Fore.RED, Fore.BLUE]


def coloured_tokens(tokens: list[str]) -> str:
    """
    Display tokens with alternating colours so boundaries are visible.
    
    Each token gets a different colour. The pipe character '|' separates
    them, making it clear where one token ends and the next begins.
    """
    parts = []
    for i, token in enumerate(tokens):
        colour = TOKEN_COLOURS[i % len(TOKEN_COLOURS)]
        # Replace newlines and tabs with visible markers
        display = token.replace("\n", "\\n").replace("\t", "\\t")
        parts.append(f"{colour}{display}{Style.RESET_ALL}")
    return "|".join(parts)


def print_header(text: str):
    """Print a section header."""
    width = 80
    print(f"\n{'=' * width}")
    print(f"  {text}")
    print(f"{'=' * width}")


def print_subheader(text: str):
    """Print a subsection header."""
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print(f"{'─' * 60}")


# ─── Section 1: Token Boundary Visualisation ────────────────────────

def run_boundary_visualisation(client: anthropic.Anthropic):
    """
    Show how each text type gets split into tokens.
    
    Uses tiktoken (GPT-4) for boundary visualisation since the
    Anthropic API only returns counts, not individual tokens.
    Also compares GPT-4 (cl100k) vs GPT-4o (o200k) boundaries.
    """
    print_header("SECTION 1: TOKEN BOUNDARY VISUALISATION")
    print("  (Using tiktoken for boundaries — Anthropic API only returns counts)")
    
    for key, info in TEST_TEXTS.items():
        text = info["text"]
        label = info["label"]
        why = info["why"]
        
        print_subheader(label)
        print(f"  Why this matters: {why}")
        
        # Show the original text (truncated if very long)
        display_text = text[:200] + "..." if len(text) > 200 else text
        print(f"\n  Original ({len(text)} chars):")
        print(f"  {display_text}")
        
        # GPT-4 tokenisation (cl100k_base)
        gpt4_tokens = get_tiktoken_tokens(text, "cl100k_base")
        print(f"\n  GPT-4 tokens (cl100k_base): {len(gpt4_tokens)} tokens")
        print(f"  {coloured_tokens(gpt4_tokens)}")
        
        # GPT-4o tokenisation (o200k_base)
        gpt4o_tokens = get_tiktoken_tokens(text, "o200k_base")
        print(f"\n  GPT-4o tokens (o200k_base): {len(gpt4o_tokens)} tokens")
        print(f"  {coloured_tokens(gpt4o_tokens)}")
        
        # Claude token count (API — no boundaries available)
        result = compare_tokenisation(client, text, label)
        print(f"\n  Claude token count: {result['claude_tokens']}")
        
        # Efficiency comparison
        print(f"\n  Chars per token:")
        print(f"    Claude:  {result['claude_chars_per_token']:.1f}")
        print(f"    GPT-4:   {result['gpt4_chars_per_token']:.1f}")
        print(f"    GPT-4o:  {result['gpt4o_chars_per_token']:.1f}")


# ─── Section 2: Cross-Model Token Count Comparison ──────────────────

def run_count_comparison(client: anthropic.Anthropic):
    """
    Side-by-side token count comparison across all text types.
    Shows which tokeniser is more efficient for each content type.
    """
    print_header("SECTION 2: TOKEN COUNT COMPARISON")
    
    # Header
    print(f"\n  {'Text Type':<30} {'Chars':>6} {'Claude':>7} {'GPT-4':>7} {'GPT-4o':>7} {'Claude Efficiency':>18}")
    print(f"  {'─' * 30} {'─' * 6} {'─' * 7} {'─' * 7} {'─' * 7} {'─' * 18}")
    
    results = []
    for key, info in TEST_TEXTS.items():
        result = compare_tokenisation(client, info["text"], info["label"])
        results.append(result)
        
        # Determine which is most efficient (fewest tokens)
        min_tokens = min(result["claude_tokens"], result["gpt4_tokens"], result["gpt4o_tokens"])
        
        # Format with colour: green for the winner
        def fmt(count, is_winner):
            if is_winner:
                return f"{Fore.GREEN}{count:>7}{Style.RESET_ALL}"
            return f"{count:>7}"
        
        short_label = info["label"][:30]
        
        claude_win = result["claude_tokens"] == min_tokens
        gpt4_win = result["gpt4_tokens"] == min_tokens
        gpt4o_win = result["gpt4o_tokens"] == min_tokens
        
        # Efficiency vs GPT-4: positive = Claude is more efficient
        efficiency = ((result["gpt4_tokens"] - result["claude_tokens"]) / result["gpt4_tokens"] * 100)
        eff_colour = Fore.GREEN if efficiency > 0 else Fore.RED
        eff_str = f"{eff_colour}{efficiency:+.1f}% vs GPT-4{Style.RESET_ALL}"
        
        print(f"  {short_label:<30} {result['char_count']:>6} "
              f"{fmt(result['claude_tokens'], claude_win)} "
              f"{fmt(result['gpt4_tokens'], gpt4_win)} "
              f"{fmt(result['gpt4o_tokens'], gpt4o_win)} "
              f"{eff_str:>18}")
    
    # Summary stats
    total_claude = sum(r["claude_tokens"] for r in results)
    total_gpt4 = sum(r["gpt4_tokens"] for r in results)
    total_gpt4o = sum(r["gpt4o_tokens"] for r in results)
    
    print(f"\n  {'TOTAL':<30} {'':>6} {total_claude:>7} {total_gpt4:>7} {total_gpt4o:>7}")
    print(f"\n  Overall: Claude uses {((total_gpt4 - total_claude) / total_gpt4 * 100):+.1f}% tokens vs GPT-4, "
          f"{((total_gpt4o - total_claude) / total_gpt4o * 100):+.1f}% vs GPT-4o")
    
    return results


# ─── Section 3: Cost Comparison ─────────────────────────────────────

def run_cost_comparison(results: list[dict]):
    """
    Calculate and display the cost of a 10,000-token prompt across models.
    
    Uses the average chars-per-token ratio from actual measurements
    to estimate how many tokens each model would use for the same content.
    """
    print_header("SECTION 3: COST COMPARISON (10,000 TOKEN INPUT)")
    print("  Estimated cost for a 10k token input across models.\n")
    
    # Use average token counts from our test texts to estimate relative efficiency
    total_claude = sum(r["claude_tokens"] for r in results)
    total_gpt4 = sum(r["gpt4_tokens"] for r in results)
    total_gpt4o = sum(r["gpt4o_tokens"] for r in results)
    
    # Calculate cost comparison at 10k tokens
    # For Anthropic models, 10k tokens = 10k tokens (same tokeniser)
    # For OpenAI models, scale by the ratio of their token count to Claude's
    gpt4_ratio = total_gpt4 / total_claude if total_claude > 0 else 1.0
    gpt4o_ratio = total_gpt4o / total_claude if total_claude > 0 else 1.0
    
    target = 10_000
    
    comparison = cost_comparison_table(
        claude_tokens=target,
        gpt4_tokens=int(target * gpt4_ratio),
        gpt4o_tokens=int(target * gpt4o_ratio),
    )
    
    # Header
    print(f"  {'Model':<20} {'Provider':<10} {'Tokens':>8} {'Input Cost':>12} {'Output Cost':>12} {'Context':>10}")
    print(f"  {'─' * 20} {'─' * 10} {'─' * 8} {'─' * 12} {'─' * 12} {'─' * 10}")
    
    for row in comparison:
        print(f"  {row['model']:<20} {row['provider']:<10} {row['tokens']:>8,} "
              f"${row['input_cost']:>10.4f} ${row['output_cost']:>10.4f} {row['context_window']:>10,}")
    
    # Highlight key takeaways
    print(f"\n  Key takeaways:")
    
    cheapest = min(comparison, key=lambda x: x["input_cost"])
    most_expensive = max(comparison, key=lambda x: x["input_cost"])
    ratio = most_expensive["input_cost"] / cheapest["input_cost"] if cheapest["input_cost"] > 0 else 0
    
    print(f"  • Cheapest input: {cheapest['model']} (${cheapest['input_cost']:.4f} for 10k tokens)")
    print(f"  • Most expensive input: {most_expensive['model']} (${most_expensive['input_cost']:.4f} for 10k tokens)")
    print(f"  • Price range: {ratio:.0f}x difference between cheapest and most expensive")
    
    # Anthropic-specific comparison
    anthropic_models = [r for r in comparison if r["provider"] == "Anthropic"]
    if len(anthropic_models) >= 2:
        haiku = next((m for m in anthropic_models if "haiku" in m["model"]), None)
        opus = next((m for m in anthropic_models if "opus" in m["model"]), None)
        if haiku and opus:
            ratio = opus["input_cost"] / haiku["input_cost"]
            print(f"  • Opus is {ratio:.1f}x more expensive than Haiku — "
                  f"this is why model routing (Module 7) matters")


# ─── Section 4: Observations ────────────────────────────────────────

def print_observations():
    """Print analysis and observations about tokenisation patterns."""
    print_header("SECTION 4: OBSERVATIONS")
    
    observations = [
        (
            "Numbers are expensive",
            "Financial data like '$84,521.30' splits into many tokens because each digit "
            "group, comma, decimal point, and dollar sign may be separate tokens. A price "
            "feed with 100 assets costs more tokens than the equivalent length of prose. "
            "For AW Analysis: consider summarising numerical data rather than including raw "
            "numbers when context space is tight."
        ),
        (
            "Code tokenises less efficiently than prose",
            "Indentation, brackets, colons, and operators are often individual tokens. A "
            "100-line Python file uses significantly more tokens than 100 lines of prose. "
            "This is why code-heavy system prompts are expensive and why prompt caching "
            "(Module 1) matters for tool definitions."
        ),
        (
            "Non-English text is 2-3x more expensive",
            "Chinese characters and Japanese text use more tokens per character because the "
            "BPE vocabulary is dominated by English patterns. If AW Analysis serves "
            "multilingual users, factor this into your token budget — a Chinese query uses "
            "more context than the same query in English."
        ),
        (
            "Different tokenisers produce different counts",
            "The same text produces different token counts across Claude, GPT-4, and GPT-4o. "
            "You cannot use tiktoken to estimate Claude's costs — use the Anthropic "
            "count_tokens endpoint. GPT-4o's newer tokeniser (o200k_base, 200k vocabulary) "
            "is generally more efficient than GPT-4's (cl100k_base, 100k vocabulary) "
            "because the larger vocabulary can represent more text as single tokens."
        ),
        (
            "URLs and hashes are token sinks",
            "A single URL or hash can consume 20-50 tokens. If your agent receives tool "
            "results containing URLs, transaction hashes, or long identifiers, these eat "
            "into your context budget disproportionately. Consider truncating or summarising "
            "these in your tool result handlers."
        ),
        (
            "Repetitive text is efficient but wasteful",
            "Repeating the same word is token-efficient (each instance is one token) but "
            "wastes context on redundant information. This is a reminder that token count "
            "isn't the only measure — information density matters too."
        ),
        (
            "Token boundaries explain some model behaviours",
            "When a model struggles with novel compound words, unusual formatting, or "
            "precise arithmetic, it's often because the tokenisation splits the text in "
            "unhelpful ways. Understanding this helps you debug unexpected outputs — if the "
            "model misreads a number, check how it tokenises."
        ),
    ]
    
    for i, (title, body) in enumerate(observations, 1):
        print(f"\n  {i}. {Fore.CYAN}{title}{Style.RESET_ALL}")
        # Word wrap the body at 76 chars with 5-space indent
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


# ─── Main ───────────────────────────────────────────────────────────

def main():
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"{Fore.RED}Error: ANTHROPIC_API_KEY not set.{Style.RESET_ALL}")
        print("Run: export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)
    
    print(f"{Fore.CYAN}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          Exercise 5.1: Tokenisation Explorer                ║")
    print("║          Module 5 — LLM Fundamentals                       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{Style.RESET_ALL}")
    
    client = anthropic.Anthropic()
    
    # Section 1: Visual token boundaries
    run_boundary_visualisation(client)
    
    # Section 2: Count comparison table
    results = run_count_comparison(client)
    
    # Section 3: Cost comparison
    run_cost_comparison(results)
    
    # Section 4: Written observations
    print_observations()
    
    print(f"\n{'=' * 80}")
    print(f"  {Fore.GREEN}Exercise 5.1 complete.{Style.RESET_ALL}")
    print(f"  API calls made: {len(TEST_TEXTS)} (one count_tokens call per text type)")
    print(f"  No generation tokens used — count_tokens is free/cheap.")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()