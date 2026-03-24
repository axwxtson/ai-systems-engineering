"""
evaluate.py — Compare four retrieval methods on the same queries.

Methods: dense, sparse (BM25), hybrid (RRF), hybrid + rerank
Metrics: recall@5, MRR, average similarity/score

Uses the same 10 test queries as Exercise 4.2 plus builds the shared index.
"""

import time
import json
from retrieval import RetrievalIndex, METHODS, retrieve, load_documents
from config import DOCS_DIR, TOP_K


# ── Test Queries (same as 4.2) ────────────────────────────────────────

EVAL_QUERIES = [
    {
        "query": "What caused Bitcoin to crash in 2022?",
        "relevant_sources": ["btc_crash_2022.md"],
    },
    {
        "query": "How did the Ethereum Merge change the network's energy consumption?",
        "relevant_sources": ["eth_merge_2022.md"],
    },
    {
        "query": "What are the main risks of investing in DeFi protocols?",
        "relevant_sources": ["crypto_defi_risks.md"],
    },
    {
        "query": "NVIDIA H100 GPU market share AI",
        "relevant_sources": ["nvidia_ai_boom.md"],
    },
    {
        "query": "central bank gold purchases 2023",
        "relevant_sources": ["gold_2023.md"],
    },
    {
        "query": "What was the market reaction to the Bank of Japan ending negative rates?",
        "relevant_sources": ["japan_rates_2024.md"],
    },
    {
        "query": "How did spot Bitcoin ETFs perform after SEC approval?",
        "relevant_sources": ["btc_etf_2024.md"],
    },
    {
        "query": "oil supply disruption Red Sea shipping",
        "relevant_sources": ["oil_geopolitics_2024.md"],
    },
    {
        "query": "How should a conservative investor allocate to AI stocks?",
        "relevant_sources": ["portfolio_construction_ai.md"],
    },
    {
        "query": "Canadian energy sector pipeline capacity and dividends",
        "relevant_sources": ["tsx_energy_2024.md"],
    },
]


# ── Metrics ───────────────────────────────────────────────────────────

def recall_at_k(relevant: list[str], retrieved: list[dict], k: int = 5) -> float:
    relevant_set = set(relevant)
    retrieved_sources = [r["source"] for r in retrieved[:k]]
    hits = relevant_set.intersection(set(retrieved_sources))
    return len(hits) / len(relevant_set) if relevant_set else 0.0


def mrr(relevant: list[str], retrieved: list[dict]) -> float:
    relevant_set = set(relevant)
    for rank, r in enumerate(retrieved):
        if r["source"] in relevant_set:
            return 1.0 / (rank + 1)
    return 0.0


# ── Main ──────────────────────────────────────────────────────────────

def run_evaluation():
    print("=" * 70)
    print("Exercise 4.3: Hybrid Search with Reranking")
    print("=" * 70)

    # Load and index
    print("\n[1/2] Building index...")
    documents = load_documents(DOCS_DIR)
    index = RetrievalIndex()
    index.build(documents)

    # Run queries
    print(f"\n[2/2] Running {len(EVAL_QUERIES)} queries × {len(METHODS)} methods...")
    print(f"{'=' * 70}")

    results_by_method = {name: [] for name in METHODS}

    for i, test in enumerate(EVAL_QUERIES):
        print(f"\n  Q{i + 1}: \"{test['query'][:60]}\"")

        for method_name in METHODS:
            # Rate limit pause for methods that call Voyage
            if method_name in ("dense", "hybrid", "hybrid_rerank"):
                time.sleep(1)

            t0 = time.time()
            retrieved = retrieve(index, test["query"], method_name)
            elapsed = time.time() - t0

            r = recall_at_k(test["relevant_sources"], retrieved)
            m = mrr(test["relevant_sources"], retrieved)
            top_score = retrieved[0]["score"] if retrieved else 0
            top_source = retrieved[0]["source"] if retrieved else "none"

            hit = "✅" if r == 1.0 else "❌"
            print(f"    {method_name:16s} | recall={r:.2f} | MRR={m:.2f} | "
                  f"score={top_score:.3f} | {elapsed:.2f}s | {hit}")

            results_by_method[method_name].append({
                "query": test["query"],
                "recall_at_5": r,
                "mrr": m,
                "top_score": top_score,
                "top_source": top_source,
                "expected": test["relevant_sources"],
                "latency": elapsed,
            })

        # Rate limit pause
        if i < len(EVAL_QUERIES) - 1:
            print("    (pausing 20s for rate limit...)")
            time.sleep(20)

    # ── Summary ───────────────────────────────────────────────────────

    print(f"\n{'=' * 70}")
    print("RESULTS SUMMARY")
    print(f"{'=' * 70}")

    print(f"\n{'Method':<16} | {'Recall@5':>8} | {'MRR':>6} | "
          f"{'Avg Score':>9} | {'Avg Latency':>11} | {'Hits':>4}")
    print("-" * 70)

    for method_name in METHODS:
        results = results_by_method[method_name]
        avg_recall = sum(r["recall_at_5"] for r in results) / len(results)
        avg_mrr = sum(r["mrr"] for r in results) / len(results)
        avg_score = sum(r["top_score"] for r in results) / len(results)
        avg_latency = sum(r["latency"] for r in results) / len(results)
        hits = sum(1 for r in results if r["recall_at_5"] == 1.0)

        print(f"{method_name:<16} | {avg_recall:>8.2f} | {avg_mrr:>6.2f} | "
              f"{avg_score:>9.3f} | {avg_latency:>9.2f}s | {hits:>4}/10")

    # ── Head-to-Head: Hybrid vs Dense ─────────────────────────────────

    print(f"\n{'=' * 70}")
    print("HEAD-TO-HEAD: Where hybrid beats dense")
    print(f"{'=' * 70}")

    hybrid_wins = 0
    dense_wins = 0
    ties = 0

    for i, test in enumerate(EVAL_QUERIES):
        dense_r = results_by_method["dense"][i]["recall_at_5"]
        hybrid_r = results_by_method["hybrid"][i]["recall_at_5"]

        if hybrid_r > dense_r:
            hybrid_wins += 1
            print(f"  Q{i + 1}: HYBRID wins — \"{test['query'][:50]}\"")
        elif dense_r > hybrid_r:
            dense_wins += 1
            print(f"  Q{i + 1}: DENSE wins — \"{test['query'][:50]}\"")
        else:
            ties += 1

    print(f"\n  Hybrid wins: {hybrid_wins} | Dense wins: {dense_wins} | Ties: {ties}")

    # ── Save Results ──────────────────────────────────────────────────

    output = {
        "summary": {
            method: {
                "avg_recall": sum(r["recall_at_5"] for r in results) / len(results),
                "avg_mrr": sum(r["mrr"] for r in results) / len(results),
                "hits": sum(1 for r in results if r["recall_at_5"] == 1.0),
            }
            for method, results in results_by_method.items()
        },
        "per_query": results_by_method,
    }

    with open("results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nFull results saved to results.json")


if __name__ == "__main__":
    run_evaluation()