# Exercise 4.3: Hybrid Search with Reranking

## What This Is

A four-way comparison of retrieval methods on the same document set and queries:

1. **Dense** — Vector similarity only (ChromaDB cosine search)
2. **Sparse** — BM25 keyword matching only
3. **Hybrid** — Dense + Sparse fused with Reciprocal Rank Fusion (RRF)
4. **Hybrid + Rerank** — Hybrid results reranked with Voyage rerank-2

## Architecture

```
Same 40 chunks (recursive chunking from 12 documents)
    ├── ChromaDB vector index (for dense retrieval)
    └── BM25 index (for sparse retrieval)

Query ──┬── Dense Search (top-20) ──┐
        │                            ├── RRF Fusion → top-20 → [Rerank] → top-5
        └── BM25 Search (top-20) ───┘
```

## Files

| File | Purpose |
|------|---------|
| `retrieval.py` | `RetrievalIndex` class with all four retrieval methods |
| `evaluate.py` | Runs 10 queries × 4 methods, compares metrics |
| `config.py` | Settings including rerank model |

## Setup & Run

```bash
pip install anthropic voyageai chromadb rank-bm25 numpy
export VOYAGE_API_KEY="pa-..."

python3 evaluate.py
```

## Test Results

| Method | Recall@5 | MRR | Avg Score | Avg Latency | Hits |
|--------|----------|-----|-----------|-------------|------|
| Dense | 1.00 | 1.00 | 0.581 | 0.35s | 10/10 |
| Sparse (BM25) | 1.00 | 0.95 | 12.598 | 0.00s | 10/10 |
| Hybrid (RRF) | 1.00 | 1.00 | 0.033 | 0.30s | 10/10 |
| Hybrid + Rerank | 1.00 | 1.00 | 0.841 | 0.61s | 10/10 |

Head-to-head: Hybrid wins 0, Dense wins 0, Ties 10.

## Key Findings

**All methods achieved perfect recall** — same as Exercise 4.2, the 12-document corpus is too small and distinct to differentiate retrieval methods. Real differences emerge with overlapping documents.

**BM25's MRR was 0.95, not 1.00.** Q1 had MRR=0.50 — BM25 ranked a non-relevant chunk higher because it matched more query keywords. This demonstrates pure keyword matching's weakness: term frequency can mislead.

**Reranker scores are genuine relevance assessments.** Range from 0.613 (multi-topic query) to 0.949 (focused query). The reranker distinguishes "somewhat related" from "directly answers the question" even when all methods find the right document.

**Latency profile:** BM25 ≈ 0.00s, Dense ≈ 0.35s, Hybrid ≈ 0.30s, Hybrid+Rerank ≈ 0.61s. The 0.3s reranking cost is almost always worth it in production.

**Conclusion:** Hybrid + reranking is the right production default. Matches or beats every other method, and the reranker provides genuinely useful relevance scoring even when recall is perfect.

## Part of Module 4: RAG Systems

Exercise 4.3 of the [AI Systems Engineering](https://github.com/axwxtson/ai-systems-engineering) study programme.