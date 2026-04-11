"""Golden dataset for the model router profiler.

15 queries across 3 difficulty classes — easy, medium, hard — chosen to
exercise the kind of work AW Analysis would actually see in production.

Difficulty is defined operationally:
- easy:   single-fact retrieval, definitions, simple summaries. No reasoning chain.
- medium: comparisons, multi-step but bounded, two-factor synthesis.
- hard:   open-ended analysis, multi-factor reasoning, judgment calls, no clean
          ground truth.

The queries below are self-contained — they do not require live data lookups.
The system under test is a single Claude call with a market analyst system
prompt. We are measuring model quality on the *reasoning*, not on data access.
"""

from dataclasses import dataclass


@dataclass
class GoldenCase:
    case_id: str
    query_class: str  # "easy" | "medium" | "hard"
    query: str
    # Free-text rubric guidance for the judge — what a good answer should cover.
    rubric_focus: str


GOLDEN_DATASET: list[GoldenCase] = [
    # ========================================
    # EASY — single fact, definition, simple summary
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
    # ========================================
    # MEDIUM — comparison, bounded multi-step, two-factor
    # ========================================
    GoldenCase(
        case_id="med_01",
        query_class="medium",
        query=(
            "Compare gold and Bitcoin as inflation hedges. Cover the theoretical argument "
            "for each and the empirical track record over the past decade."
        ),
        rubric_focus="Both theoretical case and empirical record. Acknowledges weakness in BTC's hedge claim during 2022.",
    ),
    GoldenCase(
        case_id="med_02",
        query_class="medium",
        query=(
            "Explain how a central bank rate cut typically affects (a) equity markets and "
            "(b) the value of the domestic currency. Use mechanisms, not just direction."
        ),
        rubric_focus="Discount rate / cost of capital for equities, interest rate differential for FX. Direction AND mechanism for both.",
    ),
    GoldenCase(
        case_id="med_03",
        query_class="medium",
        query=(
            "What are the main differences between Proof-of-Work and Proof-of-Stake consensus "
            "mechanisms in terms of security, energy use, and capital requirements?"
        ),
        rubric_focus="All three dimensions covered correctly. PoW: hash power, energy. PoS: stake-based, slashing, capital efficient.",
    ),
    GoldenCase(
        case_id="med_04",
        query_class="medium",
        query=(
            "If the US dollar strengthens against the euro by 5%, what are the likely effects "
            "on (a) US multinational corporate earnings and (b) European exporters to the US?"
        ),
        rubric_focus="USD strength hurts US multinational earnings (translation), helps European exporters (cheaper goods abroad).",
    ),
    GoldenCase(
        case_id="med_05",
        query_class="medium",
        query=(
            "Compare the typical risk profile and return expectations of investment-grade "
            "corporate bonds versus high-yield ('junk') bonds."
        ),
        rubric_focus="Default risk, yield spread, correlation with equities for HY, sensitivity to rates for IG.",
    ),
    # ========================================
    # HARD — open-ended, multi-factor, judgment calls
    # ========================================
    GoldenCase(
        case_id="hard_01",
        query_class="hard",
        query=(
            "A central bank announces an unexpected 50 basis point rate hike while signalling "
            "more cuts may follow if inflation falls. Walk through the likely first-day market "
            "reaction across equities, bonds, FX, and gold, and explain the tensions in your "
            "reasoning where the signals point in different directions."
        ),
        rubric_focus="Multi-asset reasoning, acknowledgement that the dovish forward guidance complicates the hawkish surprise, no false certainty.",
    ),
    GoldenCase(
        case_id="hard_02",
        query_class="hard",
        query=(
            "Analyse the macro and structural factors that could plausibly explain a sustained "
            "decoupling between Bitcoin and US tech stocks after years of high correlation. "
            "Be honest about which factors are speculative versus well-supported."
        ),
        rubric_focus="Multiple factors, distinguishes speculative from supported, acknowledges historical correlation strength.",
    ),
    GoldenCase(
        case_id="hard_03",
        query_class="hard",
        query=(
            "An equity index has rallied 18% over the past quarter while earnings forecasts "
            "have been revised downward and the yield curve is inverted. Synthesise what these "
            "signals together suggest about market positioning and what scenarios resolve the "
            "tension."
        ),
        rubric_focus="Multi-factor synthesis, discusses multiple expansion vs earnings, recession probability, possible resolutions.",
    ),
    GoldenCase(
        case_id="hard_04",
        query_class="hard",
        query=(
            "Assess the trade-offs an institutional investor faces when considering increasing "
            "crypto allocation from 0% to 5% of a multi-asset portfolio. Cover diversification "
            "math, custody and operational risk, regulatory uncertainty, and reputational risk."
        ),
        rubric_focus="All four dimensions, realistic about the practical (operational, reputational) constraints, not just diversification theory.",
    ),
    GoldenCase(
        case_id="hard_05",
        query_class="hard",
        query=(
            "Explain why measuring 'real' returns on commodity investments is harder than for "
            "equities, and how this affects the case for commodities as a long-term portfolio "
            "component. Acknowledge where reasonable investors disagree."
        ),
        rubric_focus="Roll yield, no income stream, contango/backwardation, contested empirical case for long-term commodity exposure.",
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