# Exercise 4.1: RAG from Scratch with ChromaDB

## What This Is

A minimal but complete Retrieval-Augmented Generation (RAG) system built from scratch. Ingests market research documents, chunks them, embeds with Voyage AI, stores in ChromaDB, and retrieves relevant context for Claude to generate cited answers.

## Architecture

```
INGESTION (offline):  documents/ → load → recursive_chunk → embed (Voyage) → store (ChromaDB)
QUERY (online):       user query → embed → retrieve top-5 → format context → Claude generates answer
```

## Stack

- **Embedding:** Voyage AI (`voyage-3`, 1024 dimensions)
- **Vector DB:** ChromaDB (persistent, cosine similarity)
- **Generation:** Claude Sonnet (`claude-sonnet-4-20250514`)
- **Chunking:** Recursive (paragraphs → sentences → hard split, 800 char max, 150 char overlap)

## Files

| File | Purpose |
|------|---------|
| `generate_docs.py` | Creates 12 mock market research documents |
| `config.py` | Shared settings (chunk size, model, top-k) |
| `ingest.py` | Ingestion pipeline: load → chunk → embed → store |
| `query.py` | Query pipeline: embed → retrieve → generate with citations |

## Setup & Run

```bash
pip install anthropic voyageai chromadb
export ANTHROPIC_API_KEY="sk-ant-..."
export VOYAGE_API_KEY="pa-..."

python3 generate_docs.py   # Create mock documents
python3 ingest.py          # Run ingestion pipeline (40 chunks from 12 docs)
python3 query.py           # Interactive query CLI
```

## Test Results

All 6 acceptance queries passed — correct source retrieved as top result for each:

| Query | Top Source | Similarity | Total Time |
|-------|-----------|------------|------------|
| "What happened to Bitcoin in 2022?" | btc_crash_2022.md | 0.623 | 9.69s |
| "How did the Ethereum Merge affect supply?" | eth_merge_2022.md | 0.602 | 6.12s |
| "What are the risks of DeFi?" | crypto_defi_risks.md | 0.566 | 9.02s |
| "How has NVIDIA benefited from AI?" | nvidia_ai_boom.md | 0.577 | 9.86s |
| "What happened with Japanese interest rates?" | japan_rates_2024.md | 0.525 | 6.75s |
| "How should I allocate portfolio exposure to AI?" | portfolio_construction_ai.md | 0.620 | 9.14s |

## Key Observations

- Retrieval (embed + search) consistently under 1.5s; generation dominates total latency
- Cosine similarity scores in 0.5-0.6 range are normal for Voyage — good semantic matches
- Recursive chunking produced 40 chunks from 12 docs (avg 584 chars/chunk)
- Claude correctly cites sources throughout all answers with no hallucinated claims
- `input_type="query"` vs `"document"` distinction matters — Voyage optimises differently

## Part of Module 4: RAG Systems

Exercise 4.1 of the [AI Systems Engineering](https://github.com/axwxtson/ai-systems-engineering) study programme. Builds the foundation for hybrid search (4.3) and AW Analysis integration (4.4).