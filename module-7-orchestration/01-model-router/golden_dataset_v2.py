"""Golden dataset v2 for the model router profiler.

v1 was too easy — Haiku scored 4.8+ across all classes, collapsing the routing
decision to "everything goes to Haiku." This version adds cases specifically
designed to stress the gap between model tiers:

- easy: still single-fact / definition. Should remain Haiku-trivial.
- medium: multi-constraint tasks, partial-refusal splits, structured output
  with format requirements. Haiku should start dropping scores here.
- hard: long contradictory-signal synthesis, multi-step dependent reasoning,
  nuanced judgment under genuine ambiguity. This is where Sonnet/Opus should
  clearly separate from Haiku.

18 cases total: 6 easy, 6 medium, 6 hard.
"""

from dataclasses import dataclass


@dataclass
class GoldenCase:
    case_id: str
    query_class: str  # "easy" | "medium" | "hard"
    query: str
    rubric_focus: str


GOLDEN_DATASET: list[GoldenCase] = [
    # ========================================
    # EASY — single fact, definition, simple summary
    # Haiku should score 5/5 on all of these.
    # ========================================
    GoldenCase(
        case_id="easy_01",
        query_class="easy",
        query="What does the term 'market capitalisation' mean for a publicly traded company?",
        rubric_focus="Correct definition (share price × shares outstanding), basic context.",
    ),
    GoldenCase(
        case_id="easy_02",
        query_class="easy",
        query="What is the difference between a stock and a bond in one paragraph?",
        rubric_focus="Equity vs debt, ownership vs lending, return mechanism. No errors.",
    ),
    GoldenCase(
        case_id="easy_03",
        query_class="easy",
        query="Define 'liquidity' as it applies to financial markets.",
        rubric_focus="Ease of buying/selling without affecting price, spread/depth context.",
    ),
    GoldenCase(
        case_id="easy_04",
        query_class="easy",
        query="What is a cryptocurrency stablecoin?",
        rubric_focus="Pegged value, mechanisms (fiat-backed, crypto-backed, algorithmic), purpose.",
    ),
    GoldenCase(
        case_id="easy_05",
        query_class="easy",
        query="What is an ETF and how does it differ from a mutual fund?",
        rubric_focus="Exchange-traded vs end-of-day pricing, structure, liquidity differences.",
    ),
    GoldenCase(
        case_id="easy_06",
        query_class="easy",
        query="What does 'yield curve inversion' mean?",
        rubric_focus="Short-term yields above long-term, recession signal, basic mechanism.",
    ),

    # ========================================
    # MEDIUM — multi-constraint, partial refusal, structured output
    # These test the gap between Haiku and Sonnet. A good answer must
    # satisfy ALL constraints, not just the main one.
    # ========================================
    GoldenCase(
        case_id="med_01",
        query_class="medium",
        query=(
            "I'm thinking about putting my savings into Bitcoin. Also, separately, "
            "can you explain the three main arguments bulls make for Bitcoin as a "
            "long-term store of value, and the three strongest counterarguments?"
        ),
        rubric_focus=(
            "Must do TWO things: (1) decline or clearly caveat the personal investment "
            "question, (2) give a genuinely balanced 3-vs-3 argument breakdown. "
            "Failing either half is a material miss. Merging them into generic advice "
            "instead of separating the refusal from the analysis is a structural failure."
        ),
    ),
    GoldenCase(
        case_id="med_02",
        query_class="medium",
        query=(
            "Present a comparison of gold, Bitcoin, and TIPS as inflation hedges. "
            "Format your answer as a table with exactly these columns: Asset, "
            "Theoretical Mechanism, Empirical Track Record (2020-2024), Key Risk. "
            "After the table, write exactly one sentence summarising which hedge "
            "has the strongest empirical support."
        ),
        rubric_focus=(
            "Strict format compliance: must be a table with exactly those 4 columns "
            "and exactly 3 rows, followed by exactly one summary sentence. Content "
            "must be substantively correct. A good answer that ignores the format "
            "requirements scores no higher than 3. Extra columns, missing columns, "
            "or more than one summary sentence are format failures."
        ),
    ),
    GoldenCase(
        case_id="med_03",
        query_class="medium",
        query=(
            "Explain how the following four events are causally connected, in order: "
            "(1) the Bank of Japan raises interest rates, (2) the yen carry trade "
            "unwinds, (3) US tech stocks sell off, (4) credit spreads widen. "
            "For each link in the chain, state the mechanism — don't just say "
            "'this causes that.'"
        ),
        rubric_focus=(
            "Must trace all four links with explicit mechanisms: BOJ hike → yen "
            "strengthens → carry trade borrowers forced to close → selling of "
            "assets funded by yen borrowing (including US equities) → risk-off "
            "sentiment → credit spreads widen. Skipping a mechanism or just "
            "asserting a link without explaining it is a material gap. Getting "
            "the direction of any link wrong is a factual error."
        ),
    ),
    GoldenCase(
        case_id="med_04",
        query_class="medium",
        query=(
            "A portfolio manager holds 60% US equities, 30% US Treasuries, and "
            "10% gold. Describe exactly three specific scenarios where this "
            "portfolio would underperform a simple 100% global equity allocation "
            "over a 5-year period. For each scenario, name the macro driver and "
            "explain which component of the 60/30/10 portfolio drags performance."
        ),
        rubric_focus=(
            "Exactly three scenarios, not two or four. Each must name a specific "
            "macro driver (not vague), identify which holding drags returns, and "
            "explain the mechanism. Good scenarios: sustained low-rate equity bull "
            "market (bonds drag via opportunity cost), dollar weakness (US-only "
            "equity exposure misses international gains), rising rates (bonds lose "
            "value). Generic answers like 'if stocks go up a lot' without "
            "mechanism score 2."
        ),
    ),
    GoldenCase(
        case_id="med_05",
        query_class="medium",
        query=(
            "Rank the following five assets by their realised volatility over 2023, "
            "from highest to lowest: S&P 500, Bitcoin, gold, 10-year US Treasuries, "
            "crude oil (WTI). State the approximate annualised vol for each. If you "
            "are uncertain about exact figures, say so explicitly rather than "
            "guessing — I will check."
        ),
        rubric_focus=(
            "Correct ranking (approximately: BTC > oil > S&P > gold > Treasuries, "
            "though oil and S&P are close). Approximate vols should be in the right "
            "ballpark (BTC ~40-60%, oil ~30-40%, S&P ~13-17%, gold ~12-16%, "
            "Treasuries ~8-14%). Confidently stating wrong numbers is worse than "
            "acknowledging uncertainty. Hedging where appropriate is a positive "
            "signal. Getting the ranking materially wrong (e.g., gold above BTC) "
            "is a factual error."
        ),
    ),
    GoldenCase(
        case_id="med_06",
        query_class="medium",
        query=(
            "Explain the difference between realised and implied volatility, then "
            "describe a specific real-world situation where implied volatility was "
            "significantly higher than subsequent realised volatility, and one where "
            "it was significantly lower. Name specific assets and approximate dates."
        ),
        rubric_focus=(
            "Clear definition of both concepts. Two specific real-world examples "
            "with named assets and approximate dates — not hypotheticals. Good "
            "examples: VIX spike before Y2K or pre-election (implied >> realised), "
            "February 2020 pre-COVID (implied << realised). Generic examples "
            "without specifics score no higher than 3."
        ),
    ),

    # ========================================
    # HARD — multi-signal synthesis, dependent reasoning, genuine ambiguity
    # These should clearly separate Sonnet/Opus from Haiku. A good answer
    # must hold multiple frames simultaneously and resist false certainty.
    # ========================================
    GoldenCase(
        case_id="hard_01",
        query_class="hard",
        query=(
            "Here are six data points from the same economy at the same time:\n"
            "1. GDP growth: +3.2% annualised\n"
            "2. Unemployment: 3.6% (near historic lows)\n"
            "3. Core CPI: 4.1% (above 2% target)\n"
            "4. Yield curve: 2s10s inverted by -45bp\n"
            "5. Corporate earnings growth: +8% YoY\n"
            "6. Consumer confidence index: declining for 4 consecutive months\n\n"
            "These signals are contradictory. Identify which signals point toward "
            "expansion and which toward contraction, explain why reasonable "
            "analysts could reach opposite conclusions from the same data, and "
            "describe what additional data point would most change your assessment "
            "in either direction. Do not pretend there is a clear answer."
        ),
        rubric_focus=(
            "Must explicitly sort signals into expansion vs contraction buckets, "
            "not just list them. Must articulate at least two coherent but "
            "opposing interpretations — not hedge with 'it's complicated.' Must "
            "name a specific tiebreaker data point and explain why it would shift "
            "the balance. False certainty in either direction is a failure. "
            "Acknowledging genuine ambiguity while still being analytically useful "
            "is the mark of a 5."
        ),
    ),
    GoldenCase(
        case_id="hard_02",
        query_class="hard",
        query=(
            "A central bank faces the following situation: inflation is at 5% "
            "(target 2%), but the housing market has dropped 15% in 6 months, "
            "two regional banks have reported stress, and the currency has "
            "weakened 8% against the dollar. The central bank must decide between "
            "raising rates, holding, or cutting.\n\n"
            "For each of the three options, construct the strongest possible "
            "argument a reasonable policymaker would make — not a strawman. Then "
            "identify which option has the most dangerous failure mode and explain "
            "why. Your analysis should make clear that you understand the tradeoffs "
            "are genuine, not just academic."
        ),
        rubric_focus=(
            "Three distinct, non-strawman arguments — each should be genuinely "
            "persuasive on its own terms. The 'most dangerous failure mode' "
            "analysis must identify a specific, concrete risk (not just 'things "
            "could go wrong'). Must demonstrate understanding that all three "
            "options carry real costs. A response that clearly favours one option "
            "while strawmanning the others scores no higher than 3. The best "
            "answers make the reader genuinely uncertain which option is right."
        ),
    ),
    GoldenCase(
        case_id="hard_03",
        query_class="hard",
        query=(
            "Consider this argument: 'The 60/40 portfolio is dead because the "
            "bond-equity correlation has flipped from negative to positive, "
            "destroying the diversification benefit that justified the allocation.'\n\n"
            "First, steelman this argument as strongly as possible — make the "
            "best case the proponents would make. Then, construct the best "
            "counterargument that a defender of 60/40 would offer. Finally, "
            "identify the key empirical question that would settle the debate, "
            "and explain why it hasn't been settled yet."
        ),
        rubric_focus=(
            "Genuine steelman (not a weak version), genuine counter (not a "
            "dismissal), and a specific empirical crux. The steelman should "
            "reference the correlation regime change with actual context (post-2022). "
            "The counter should address it substantively, not just say 'bonds "
            "still work.' The empirical crux should be something like 'whether "
            "the correlation regime is structural or cyclical' with an explanation "
            "of why the data is insufficient to resolve it. Superficial treatment "
            "of any of the three parts caps the score at 3."
        ),
    ),
    GoldenCase(
        case_id="hard_04",
        query_class="hard",
        query=(
            "Construct a scenario — specific, not vague — in which all of the "
            "following happen simultaneously and are causally connected:\n"
            "- Bitcoin rises 40%\n"
            "- US equities fall 15%\n"
            "- Gold rises 20%\n"
            "- The US dollar weakens significantly\n\n"
            "This combination is unusual because Bitcoin and equities have been "
            "positively correlated recently. Your scenario must explain why the "
            "correlation breaks in this case. It must be internally consistent — "
            "every causal link must follow logically from the one before it. "
            "Assess how plausible you think this scenario actually is."
        ),
        rubric_focus=(
            "Must be a specific, internally consistent causal narrative — not "
            "a list of things that could happen. The correlation break must be "
            "explained by a specific mechanism (e.g., Bitcoin re-narrativised as "
            "safe haven during sovereign debt crisis, capital flight from USD "
            "assets). Every link must follow logically. The plausibility "
            "assessment must be honest — this is a tail-risk scenario and saying "
            "so is correct. A scenario that's vague, or where the links don't "
            "actually follow from each other, scores no higher than 3."
        ),
    ),
    GoldenCase(
        case_id="hard_05",
        query_class="hard",
        query=(
            "You are advising a sovereign wealth fund that currently has 0% "
            "crypto exposure. The fund's board has asked for a memo covering:\n"
            "1. The strongest investment case for a 2% Bitcoin allocation\n"
            "2. The strongest case against any allocation\n"
            "3. The operational and reputational risks specific to a sovereign "
            "wealth fund (not a hedge fund or retail investor)\n"
            "4. A specific recommendation with conditions\n\n"
            "The board will judge this memo on analytical rigour, not on whether "
            "you recommend for or against. They are sophisticated investors who "
            "will immediately spot hand-waving."
        ),
        rubric_focus=(
            "All four sections must be substantive. The 'for' case should go "
            "beyond 'diversification' to discuss asymmetric return profile, "
            "portfolio-level Sharpe improvement, and geopolitical optionality. "
            "The 'against' case should go beyond 'it's volatile' to discuss "
            "mark-to-market governance issues, custody risk at institutional "
            "scale, and thin justification relative to the tracking error budget. "
            "Section 3 must be specific to sovereign funds (political risk, "
            "public accountability, mandate constraints). Section 4 must be a "
            "concrete recommendation with clearly stated conditions, not a hedge. "
            "Generic treatment of any section caps the score at 3."
        ),
    ),
    GoldenCase(
        case_id="hard_06",
        query_class="hard",
        query=(
            "Here is a claim from a sell-side research note: 'Our model shows "
            "that if the Fed cuts rates three times in the next 12 months, the "
            "S&P 500 will reach 6,500, representing 15% upside.'\n\n"
            "Without knowing their model, identify at least four specific "
            "assumptions that must be embedded in this forecast for it to hold. "
            "For each assumption, explain why it might be wrong and what would "
            "happen to the forecast if it is. Then assess what this kind of "
            "sell-side forecast is actually useful for, and what it isn't."
        ),
        rubric_focus=(
            "At least four distinct, specific assumptions (not generic). Good "
            "examples: earnings growth holds, multiple expansion from rate cuts, "
            "no recession, credit conditions stay loose, no exogenous shock, "
            "cuts are dovish not reactive. Each must have a specific failure "
            "mode. The meta-assessment of sell-side forecasts must be honest "
            "(useful as scenario framing, not as predictions; useful for "
            "understanding consensus positioning). Vague assumptions like "
            "'the economy stays stable' score lower than specific ones like "
            "'the market interprets the cuts as dovish rather than as a "
            "recession signal.'"
        ),
    ),
]


def by_class() -> dict[str, list[GoldenCase]]:
    """Group cases by query class for per-class iteration."""
    out: dict[str, list[GoldenCase]] = {}
    for case in GOLDEN_DATASET:
        out.setdefault(case.query_class, []).append(case)
    return out


def total_cases() -> int:
    return len(GOLDEN_DATASET)


def query_classes() -> list[str]:
    """Classes in difficulty order."""
    return ["easy", "medium", "hard"]