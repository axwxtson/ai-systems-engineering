# Exercise 4.2: Chunking Strategy Comparison

## What This Is

A controlled comparison of three chunking strategies using the same 12 documents and 10 queries. Each strategy gets its own ChromaDB collection. Results scored by recall@5, MRR, and top similarity.

## Three Strategies

| Strategy | How It Works | Chunks | Avg Size |
|----------|-------------|--------|----------|
| **Fixed** | Split every 500 chars with 100 char overlap | 52 | 445 chars |
| **Recursive** | Split by paragraphs → sentences → hard split (800 max) | 40 | 584 chars |
| **Semantic** | Embed sentences, split where topic similarity drops | 111 | 165 chars |

## Architecture

```
Same 12 documents (from Exercise 4.1)
    ├── Fixed chunking    → embed → ChromaDB collection "chunks_fixed"
    ├── Recursive chunking → embed → ChromaDB collection "chunks_recursive"
    └── Semantic chunking  → embed → ChromaDB collection "chunks_semantic"

10 test queries → run against all 3 collections → compare recall, MRR, similarity
```

## Files

| File | Purpose |
|------|---------|
| `chunkers.py` | Three chunking implementations: `chunk_fixed`, `chunk_recursive`, `chunk_semantic` |
| `evaluate.py` | Ingests with all strategies, runs 10 queries, scores and compares |
| `config.py` | Shared settings (uses documents from Exercise 4.1) |

## Setup & Run

```bash
pip install anthropic voyageai chromadb numpy
export VOYAGE_API_KEY="pa-..."

python3 evaluate.py
```

## Test Results

All three strategies achieved perfect recall@5 (1.00) and MRR (1.00) across all 10 queries:

| Strategy | Chunks | Avg Size | Recall@5 | MRR | Avg Top Sim | Queries Won |
|----------|--------|----------|----------|-----|-------------|-------------|
| Fixed | 52 | 445 ch | 1.00 | 1.00 | 0.583 | 3/10 |
| Recursive | 40 | 584 ch | 1.00 | 1.00 | 0.581 | 1/10 |
| Semantic | 111 | 165 ch | 1.00 | 1.00 | 0.615 | 6/10 |

## Key Findings

**All strategies achieved perfect recall.** With only 12 documents on distinct topics, the retrieval task was too easy to differentiate strategies — even bad chunks from the right document score higher than good chunks from the wrong document.

**Semantic chunking had the highest similarity scores** (0.615 avg vs 0.583 and 0.581). Smaller, topically focused chunks produce more precise embeddings. However, at 165 chars average, each chunk provides very little context for generation — a trade-off the similarity metric doesn't capture.

**The real lesson: eval difficulty matters.** This comparison would show meaningful differences with a larger corpus of overlapping topics (e.g. multiple Bitcoin analyses, several Fed reports from different quarters). With 12 distinct topics, chunking strategy is irrelevant to retrieval accuracy.

**Recursive remains the right default** — it balances retrieval precision with context richness for generation. Semantic chunking wins on similarity but loses on context per chunk. Fixed chunking has no advantages over recursive.

## Part of Module 4: RAG Systems

Exercise 4.2 of the [AI Systems Engineering](https://github.com/axwxtson/ai-systems-engineering) study programme.