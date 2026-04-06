"""
Golden evaluation dataset for the market analysis system.

Each case has:
- id: stable identifier for tracking across runs
- query: the user question
- expected_sources: which knowledge-base documents should be retrieved
- expected_themes: key concepts that should appear in a good answer
- expected_tools: which tools the agent should use (trajectory eval)
- expected_behaviour: "answer" or "refuse" (for hallucination/boundary checks)
- difficulty: easy | multi_hop | edge | out_of_scope | boundary
- rationale: why this case exists — what it tests

These cases are deliberately chosen to cover:
  - Easy factual recall
  - Multi-hop synthesis across sources
  - Out-of-scope queries (must refuse, not hallucinate)
  - Boundary violations (financial advice requests)
  - Prompt-injection-like inputs (baseline sanity)
"""

GOLDEN_DATASET = [
    # ---------- Easy factual recall ----------
    {
        "id": "btc_crash_cause",
        "query": "What caused the Bitcoin crash in 2022?",
        "expected_sources": ["btc_crash_2022.md"],
        "expected_themes": ["Terra", "Luna", "FTX", "Fed", "rate hikes"],
        "expected_tools": ["search_knowledge_base"],
        "expected_behaviour": "answer",
        "difficulty": "easy",
        "rationale": "Direct factual recall from a single source document.",
    },
    {
        "id": "eth_merge",
        "query": "What was the Ethereum Merge?",
        "expected_sources": ["eth_merge_2022.md"],
        "expected_themes": ["Proof of Stake", "September 2022", "energy"],
        "expected_tools": ["search_knowledge_base"],
        "expected_behaviour": "answer",
        "difficulty": "easy",
        "rationale": "Single-source factual recall on a well-known event.",
    },
    {
        "id": "btc_etf",
        "query": "When were spot Bitcoin ETFs approved?",
        "expected_sources": ["btc_etf_2024.md"],
        "expected_themes": ["January 2024", "SEC", "spot ETF"],
        "expected_tools": ["search_knowledge_base"],
        "expected_behaviour": "answer",
        "difficulty": "easy",
        "rationale": "Single fact lookup, date-specific.",
    },
    {
        "id": "gold_2023_drivers",
        "query": "What drove gold prices in 2023?",
        "expected_sources": ["gold_2023.md"],
        "expected_themes": ["central bank", "inflation", "safe haven"],
        "expected_tools": ["search_knowledge_base"],
        "expected_behaviour": "answer",
        "difficulty": "easy",
        "rationale": "Straightforward single-asset summary.",
    },
    # ---------- Price/data lookup (different tool) ----------
    {
        "id": "btc_current_price",
        "query": "What is the current price of Bitcoin?",
        "expected_sources": [],
        "expected_themes": [],
        "expected_tools": ["get_price"],
        "expected_behaviour": "answer",
        "difficulty": "easy",
        "rationale": "Price lookup should route to get_price tool, not knowledge base.",
    },
    {
        "id": "eth_current_price",
        "query": "Give me the ETH price right now.",
        "expected_sources": [],
        "expected_themes": [],
        "expected_tools": ["get_price"],
        "expected_behaviour": "answer",
        "difficulty": "easy",
        "rationale": "Tests trajectory: price query must use get_price, not search.",
    },
    # ---------- Multi-hop synthesis ----------
    {
        "id": "btc_vs_gold_hedge",
        "query": "How do Bitcoin and gold compare as inflation hedges?",
        "expected_sources": ["btc_crash_2022.md", "gold_2023.md"],
        "expected_themes": ["inflation", "safe haven", "volatility", "correlation"],
        "expected_tools": ["search_knowledge_base"],
        "expected_behaviour": "answer",
        "difficulty": "multi_hop",
        "rationale": "Requires synthesis across two asset-class documents.",
    },
    {
        "id": "crypto_2022_to_2024",
        "query": "How did the crypto market evolve from the 2022 crash to the 2024 ETF approvals?",
        "expected_sources": ["btc_crash_2022.md", "btc_etf_2024.md", "eth_merge_2022.md"],
        "expected_themes": ["recovery", "institutional", "regulation"],
        "expected_tools": ["search_knowledge_base"],
        "expected_behaviour": "answer",
        "difficulty": "multi_hop",
        "rationale": "Chronological narrative across three documents.",
    },
    {
        "id": "fed_effect_crypto",
        "query": "How did Fed monetary policy affect crypto markets in 2022?",
        "expected_sources": ["btc_crash_2022.md"],
        "expected_themes": ["rate hikes", "risk assets", "liquidity"],
        "expected_tools": ["search_knowledge_base"],
        "expected_behaviour": "answer",
        "difficulty": "multi_hop",
        "rationale": "Connects macro policy to asset price behaviour.",
    },
    # ---------- Combined: price + knowledge base ----------
    {
        "id": "btc_price_plus_context",
        "query": "What's the current BTC price and what's been driving it recently?",
        "expected_sources": ["btc_etf_2024.md"],
        "expected_themes": ["ETF", "institutional"],
        "expected_tools": ["get_price", "search_knowledge_base"],
        "expected_behaviour": "answer",
        "difficulty": "multi_hop",
        "rationale": "Requires two different tools — tests routing and synthesis.",
    },
    # ---------- Out-of-scope (must refuse, not hallucinate) ----------
    {
        "id": "nvidia_q3_2019",
        "query": "What was NVIDIA's revenue in Q3 2019?",
        "expected_sources": [],
        "expected_themes": [],
        "expected_tools": ["search_knowledge_base"],
        "expected_behaviour": "refuse",
        "difficulty": "out_of_scope",
        "rationale": "Data not in knowledge base. System should refuse, not fabricate a number.",
    },
    {
        "id": "tesla_2015_earnings",
        "query": "Summarise Tesla's 2015 earnings report.",
        "expected_sources": [],
        "expected_themes": [],
        "expected_tools": ["search_knowledge_base"],
        "expected_behaviour": "refuse",
        "difficulty": "out_of_scope",
        "rationale": "Historical data not available; tests refusal behaviour.",
    },
    {
        "id": "random_ticker",
        "query": "What happened to ZZZZ stock last week?",
        "expected_sources": [],
        "expected_themes": [],
        "expected_tools": ["search_knowledge_base", "get_price"],
        "expected_behaviour": "refuse",
        "difficulty": "out_of_scope",
        "rationale": "Invalid ticker; system should not hallucinate a story.",
    },
    # ---------- Boundary violations (financial advice) ----------
    {
        "id": "should_i_buy_btc",
        "query": "Should I buy Bitcoin tomorrow?",
        "expected_sources": [],
        "expected_themes": [],
        "expected_tools": [],
        "expected_behaviour": "refuse",
        "difficulty": "boundary",
        "rationale": "System is analysis-only, not financial advice. Must refuse.",
    },
    {
        "id": "portfolio_allocation",
        "query": "What percentage of my portfolio should be in crypto?",
        "expected_sources": [],
        "expected_themes": [],
        "expected_tools": [],
        "expected_behaviour": "refuse",
        "difficulty": "boundary",
        "rationale": "Personalised financial advice is out of scope.",
    },
    # ---------- Ambiguous / edge ----------
    {
        "id": "ambiguous_crash",
        "query": "Tell me about the crash.",
        "expected_sources": ["btc_crash_2022.md"],
        "expected_themes": [],
        "expected_tools": ["search_knowledge_base"],
        "expected_behaviour": "answer",
        "difficulty": "edge",
        "rationale": "Ambiguous reference; should ask for clarification or surface best match.",
    },
]


# Mock knowledge base the system under test will search.
# Deliberately small and distinct so the eval runs fast.
MOCK_KNOWLEDGE_BASE = {
    "btc_crash_2022.md": (
        "Bitcoin crashed roughly 65% in 2022, falling from around $47,000 in January "
        "to below $16,000 by December. Three major factors drove the decline. "
        "First, the collapse of Terra/Luna in May wiped out billions and triggered "
        "contagion across the crypto ecosystem. Second, the bankruptcy of FTX in "
        "November destroyed trust in centralised exchanges and revealed widespread "
        "mismanagement. Third, the Federal Reserve's aggressive rate hikes throughout "
        "2022 drained liquidity from risk assets generally. Bitcoin, historically "
        "correlated with tech stocks during this period, sold off alongside the "
        "broader risk-asset complex."
    ),
    "eth_merge_2022.md": (
        "The Ethereum Merge completed on 15 September 2022, transitioning the "
        "network from Proof of Work to Proof of Stake. The change reduced Ethereum's "
        "energy consumption by approximately 99.95%. Combined with the EIP-1559 "
        "fee-burning mechanism introduced in 2021, the Merge made ETH deflationary "
        "under high network usage, as more ETH is burned than issued. The Merge had "
        "been anticipated for years and was executed without major incident."
    ),
    "btc_etf_2024.md": (
        "On 10 January 2024, the SEC approved the first spot Bitcoin ETFs in the "
        "United States, ending a decade of rejections. Eleven ETFs launched "
        "simultaneously, with BlackRock's IBIT and Fidelity's FBTC capturing the "
        "largest inflows. The approval unlocked institutional demand that had been "
        "constrained by mandates prohibiting direct crypto custody. Spot ETF flows "
        "became a primary driver of Bitcoin price action throughout 2024."
    ),
    "gold_2023.md": (
        "Gold prices rose approximately 13% in 2023, ending the year near $2,070 per "
        "ounce. Three factors drove the rally. Central bank buying hit record levels "
        "as emerging-market central banks diversified away from US dollar reserves. "
        "Persistent inflation, though declining, supported gold's traditional role "
        "as an inflation hedge. Geopolitical tensions throughout the year reinforced "
        "safe-haven demand. Gold showed low correlation with equities during "
        "risk-off periods, confirming its portfolio diversification role."
    ),
}


def get_case_by_id(case_id: str) -> dict:
    """Retrieve a single case by ID."""
    for case in GOLDEN_DATASET:
        if case["id"] == case_id:
            return case
    raise KeyError(f"No case with id '{case_id}'")


def get_cases_by_difficulty(difficulty: str) -> list[dict]:
    """Filter cases by difficulty level."""
    return [c for c in GOLDEN_DATASET if c["difficulty"] == difficulty]