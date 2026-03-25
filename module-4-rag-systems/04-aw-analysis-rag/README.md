# Exercise 4.4: RAG for AW Analysis

## What This Is

The production RAG integration for AW Analysis. This exercise brings together everything from Module 3 (agent architecture) and Module 4 (RAG systems) into a single working system.

**What changed from Exercise 3.4:**
- `memory.py` — keyword matching → vector-based semantic search (hybrid + reranking)
- `tools.py` — gained `search_knowledge_base` tool for reference documents
- `prompts.py` — system prompt updated to include RAG tool usage guidelines

**What did NOT change:**
- `agent.py` — the agent loop is identical to Exercise 3.3/3.4
- `main.py` — same CLI structure with auto-save

**This proves the Module 3→4 thesis: RAG is a retrieval upgrade, not an architectural change.**

## Architecture

```
User Query → agent.py (ReAct loop) → Claude decides which tools to call
                                         ↓
                ┌────────────────────────┼────────────────────────┐
                ↓                        ↓                        ↓
        get_stock_price           search_knowledge_base    search_past_analyses
        get_news                        ↓                        ↓
        get_historical_prices     RAGCollection              RAGCollection
        calculate                 "knowledge_base"           "agent_memories"
                                        ↓                        ↓
                                  Hybrid Search              Hybrid Search
                                  (vector + BM25)            (vector + BM25)
                                        ↓                        ↓
                                  Voyage Rerank              Voyage Rerank
                                        ↓                        ↓
                                  Top-5 chunks               Top-5 memories
```

## Files

| File | Purpose | Changed from 3.4? |
|------|---------|-------------------|
| `config.py` | Settings (models, paths, top-k) | New file |
| `rag_pipeline.py` | `RAGCollection` class — hybrid search + rerank | **New** — core RAG infrastructure |
| `memory.py` | Save/load/search memories | **Rewritten** — vector search replaces keywords |
| `tools.py` | All agent tools | **Extended** — 2 new RAG tools added |
| `prompts.py` | System prompt | **Updated** — includes RAG tool instructions |
| `agent.py` | ReAct agent loop | **Unchanged** — proves RAG is just better tools |
| `main.py` | CLI entry point | **Unchanged** |
| `ingest.py` | Knowledge base ingestion pipeline | **New** |
| `knowledge_base/` | Reference documents (market reports) | **New** |

## Setup & Run

```bash
# 1. Install dependencies
pip install anthropic voyageai chromadb rank-bm25 numpy

# 2. Set API keys
export ANTHROPIC_API_KEY="sk-ant-..."
export VOYAGE_API_KEY="pa-..."

# 3. Copy knowledge base documents from Exercise 4.1
cp ../01-rag-from-scratch/documents/*.md knowledge_base/

# 4. Ingest knowledge base (run once)
python3 ingest.py

# 5. Run the agent
python3 main.py
```

## Test Sequence

Run these in order, don't restart between queries:

1. **"Analyse Bitcoin"** → Uses get_stock_price, get_news, get_historical_prices. Auto-saves to memory.

2. **"What happened to Bitcoin in 2022?"** → Should use `search_knowledge_base` to find btc_crash_2022.md. Cites the source.

3. **"Analyse Ethereum"** → Standard analysis with market data tools. Auto-saves.

4. **"What have I analysed so far?"** → Uses `search_past_analyses` to find BTC and ETH analyses.

5. **"How does Bitcoin compare to my earlier analysis?"** → Uses `search_past_analyses` to retrieve the BTC analysis from step 1.

6. **"What was the impact of the FTX collapse?"** → Uses `search_knowledge_base`. Should find relevant context from btc_crash_2022.md despite the query not mentioning "Bitcoin" directly. (This is the semantic search upgrade over keyword matching.)

7. Quit, restart, run: **"What did I analyse last time?"** → Memory persists via JSON + vector re-ingestion on startup.

## Acceptance Criteria

- Agent answers questions requiring historical context (uses knowledge base)
- Memory search is semantic: "cryptocurrency market downturn" finds "Bitcoin price crashed"
- Sources cited in output with [Source: filename]
- Agent loop unchanged from Exercise 3.4
- Memory persists across restarts (JSON + vector re-ingestion)
- Retrieval fast enough for interactive use

## The Key Insight

Compare the code diff between Exercise 3.4 and Exercise 4.4:

```python
# Exercise 3.4 memory.py:
def search_memories(query, limit=5):
    query_words = set(query.lower().split())
    for memory in memories:
        matches = sum(1 for word in query_words if word in memory_text)

# Exercise 4.4 memory.py:
def search_memories(query, limit=5):
    collection = get_memory_collection()
    results = collection.search(query, top_k=limit, use_rerank=True)
```

Same function name. Same parameters. Same return format. The agent calls `search_past_analyses` exactly the same way. It doesn't know the retrieval engine changed underneath. That's the point.

## Part of Module 4: RAG Systems

Exercise 4.4 of the [AI Systems Engineering](https://github.com/axwxtson/ai-systems-engineering) study programme. The capstone exercise that integrates Modules 3 and 4 into the AW Analysis portfolio project.