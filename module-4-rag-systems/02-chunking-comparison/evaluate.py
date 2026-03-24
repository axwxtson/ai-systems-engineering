"""
evaluate.py — Compare three chunking strategies on the same documents and queries.

For each strategy:
1. Chunk all documents
2. Embed chunks with Voyage
3. Store in a separate ChromaDB collection
4. Run 10 test queries
5. Score retrieval quality

Output: Side-by-side comparison with relevance scores.

NOTE: Semantic chunking calls the Voyage embed API once per document
(to embed sentences), so it uses more API calls than the other strategies.
With the free tier rate limit (3 RPM), the script includes pauses.
"""

import os
import time
import json
import voyageai
import chromadb
from config import EMBEDDING_MODEL, TOP_K, CHROMA_PATH, DOCS_DIR
from chunkers import chunk_document, STRATEGIES


# ── Test Queries with Expected Sources ────────────────────────────────

EVAL_QUERIES = [
    {
        "query": "What caused Bitcoin to crash in 2022?",
        "relevant_sources": ["btc_crash_2022.md"],
        "description": "Specific causal question — should find crash analysis",
    },
    {
        "query": "How did the Ethereum Merge change the network's energy consumption?",
        "relevant_sources": ["eth_merge_2022.md"],
        "description": "Specific technical detail about the Merge",
    },
    {
        "query": "What are the main risks of investing in DeFi protocols?",
        "relevant_sources": ["crypto_defi_risks.md"],
        "description": "Broad risk assessment question",
    },
    {
        "query": "NVIDIA H100 GPU market share AI",
        "relevant_sources": ["nvidia_ai_boom.md"],
        "description": "Keyword-heavy query — tests if chunks preserve specific terms",
    },
    {
        "query": "central bank gold purchases 2023",
        "relevant_sources": ["gold_2023.md"],
        "description": "Specific data point — tests chunk boundary handling",
    },
    {
        "query": "What was the market reaction to the Bank of Japan ending negative rates?",
        "relevant_sources": ["japan_rates_2024.md"],
        "description": "Multi-part answer — price reaction + carry trade implications",
    },
    {
        "query": "How did spot Bitcoin ETFs perform after SEC approval?",
        "relevant_sources": ["btc_etf_2024.md"],
        "description": "Specific event with flow data and price impact",
    },
    {
        "query": "oil supply disruption Red Sea shipping",
        "relevant_sources": ["oil_geopolitics_2024.md"],
        "description": "Geopolitical event — tests if chunk captures the full context",
    },
    {
        "query": "How should a conservative investor allocate to AI stocks?",
        "relevant_sources": ["portfolio_construction_ai.md"],
        "description": "Requires specific portfolio model from within a longer doc",
    },
    {
        "query": "Canadian energy sector pipeline capacity and dividends",
        "relevant_sources": ["tsx_energy_2024.md"],
        "description": "Multi-topic query from a single document — tests chunk coverage",
    },
]


# ── Document Loading ──────────────────────────────────────────────────

def load_documents(docs_dir: str) -> list[dict]:
    """Load all .md files from the documents directory."""
    documents = []
    for filename in sorted(os.listdir(docs_dir)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(docs_dir, filename)
        with open(filepath, "r") as f:
            content = f.read()

        title = filename
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line.strip("# ").strip()
                break

        documents.append({
            "content": content,
            "filename": filename,
            "title": title,
        })
    return documents


# ── Ingestion for a Single Strategy ───────────────────────────────────

def ingest_strategy(
    documents: list[dict],
    strategy_name: str,
    vo: voyageai.Client,
    chroma_client: chromadb.PersistentClient,
) -> dict:
    """Chunk all documents with one strategy, embed, store in ChromaDB.

    Returns stats about the chunking.
    """
    collection_name = f"chunks_{strategy_name}"

    # Clean slate
    try:
        chroma_client.delete_collection(collection_name)
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    all_chunks = []
    chunk_texts = []

    for doc in documents:
        chunks = chunk_document(doc["content"], strategy_name)
        for i, chunk_text in enumerate(chunks):
            chunk_id = f"{doc['filename']}::chunk_{i}"
            all_chunks.append({
                "id": chunk_id,
                "text": chunk_text,
                "source": doc["filename"],
                "title": doc["title"],
                "chunk_index": i,
                "total_chunks": len(chunks),
            })
            chunk_texts.append(chunk_text)

    # Embed all chunks (batch)
    print(f"    Embedding {len(chunk_texts)} chunks...")
    embeddings = []
    batch_size = 128
    for i in range(0, len(chunk_texts), batch_size):
        batch = chunk_texts[i:i + batch_size]
        result = vo.embed(texts=batch, model=EMBEDDING_MODEL, input_type="document")
        embeddings.extend(result.embeddings)
        if i + batch_size < len(chunk_texts):
            time.sleep(1)  # Rate limit safety

    # Store in ChromaDB
    collection.add(
        ids=[c["id"] for c in all_chunks],
        embeddings=embeddings,
        documents=[c["text"] for c in all_chunks],
        metadatas=[
            {
                "source": c["source"],
                "title": c["title"],
                "chunk_index": c["chunk_index"],
                "total_chunks": c["total_chunks"],
            }
            for c in all_chunks
        ],
    )

    # Compute stats
    chunk_sizes = [len(c["text"]) for c in all_chunks]
    stats = {
        "strategy": strategy_name,
        "total_chunks": len(all_chunks),
        "avg_chunk_size": sum(chunk_sizes) // len(chunk_sizes),
        "min_chunk_size": min(chunk_sizes),
        "max_chunk_size": max(chunk_sizes),
        "chunks_per_doc": {
            doc["filename"]: sum(1 for c in all_chunks if c["source"] == doc["filename"])
            for doc in documents
        },
    }

    return stats


# ── Query a Strategy's Collection ─────────────────────────────────────

def query_strategy(
    query: str,
    strategy_name: str,
    vo: voyageai.Client,
    chroma_client: chromadb.PersistentClient,
    top_k: int = TOP_K,
) -> dict:
    """Embed query and retrieve from a strategy's collection."""
    collection_name = f"chunks_{strategy_name}"
    collection = chroma_client.get_collection(collection_name)

    # Embed query
    query_embedding = vo.embed(
        texts=[query],
        model=EMBEDDING_MODEL,
        input_type="query",
    ).embeddings[0]

    # Retrieve
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    # Extract sources and scores
    retrieved = []
    for i in range(len(results["documents"][0])):
        retrieved.append({
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "similarity": 1 - results["distances"][0][i],
            "chunk_index": results["metadatas"][0][i]["chunk_index"],
        })

    return {
        "query": query,
        "retrieved": retrieved,
        "sources": [r["source"] for r in retrieved],
        "top_similarity": retrieved[0]["similarity"] if retrieved else 0,
    }


# ── Evaluation Metrics ────────────────────────────────────────────────

def recall_at_k(relevant_sources: list[str], retrieved_sources: list[str], k: int = 5) -> float:
    """What fraction of relevant sources appear in top-k results?"""
    relevant = set(relevant_sources)
    retrieved = set(retrieved_sources[:k])
    hits = relevant.intersection(retrieved)
    return len(hits) / len(relevant) if relevant else 0.0


def reciprocal_rank(relevant_sources: list[str], retrieved_sources: list[str]) -> float:
    """Reciprocal of the rank of the first relevant result."""
    relevant = set(relevant_sources)
    for rank, source in enumerate(retrieved_sources):
        if source in relevant:
            return 1.0 / (rank + 1)
    return 0.0


# ── Main Evaluation ───────────────────────────────────────────────────

def run_evaluation():
    print("=" * 70)
    print("Exercise 4.2: Chunking Strategy Comparison")
    print("=" * 70)

    # Load documents
    print(f"\nLoading documents from {DOCS_DIR}...")
    documents = load_documents(DOCS_DIR)
    print(f"  Loaded {len(documents)} documents")

    # Setup
    vo = voyageai.Client()
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    # ── Phase 1: Ingest with each strategy ────────────────────────────

    all_stats = {}
    for strategy_name in STRATEGIES:
        print(f"\n[Ingesting] Strategy: {strategy_name}")
        stats = ingest_strategy(documents, strategy_name, vo, chroma_client)
        all_stats[strategy_name] = stats
        print(f"    Total chunks: {stats['total_chunks']}")
        print(f"    Avg size: {stats['avg_chunk_size']} chars")
        print(f"    Range: {stats['min_chunk_size']}–{stats['max_chunk_size']} chars")

        # Pause between strategies for rate limit
        if strategy_name != list(STRATEGIES.keys())[-1]:
            print("    (pausing 20s for rate limit...)")
            time.sleep(20)

    # ── Phase 2: Query each strategy ──────────────────────────────────

    print(f"\n{'=' * 70}")
    print(f"Running {len(EVAL_QUERIES)} queries against each strategy...")
    print(f"{'=' * 70}")

    results_by_strategy = {name: [] for name in STRATEGIES}

    for i, test in enumerate(EVAL_QUERIES):
        print(f"\n  Query {i + 1}/10: \"{test['query'][:60]}...\"")

        for strategy_name in STRATEGIES:
            # Rate limit: pause between embed calls
            if strategy_name != list(STRATEGIES.keys())[0]:
                time.sleep(1)

            result = query_strategy(test["query"], strategy_name, vo, chroma_client)

            # Score
            r_at_k = recall_at_k(test["relevant_sources"], result["sources"])
            mrr = reciprocal_rank(test["relevant_sources"], result["sources"])

            result["recall_at_5"] = r_at_k
            result["mrr"] = mrr
            result["expected_sources"] = test["relevant_sources"]
            results_by_strategy[strategy_name].append(result)

            hit = "✅" if r_at_k == 1.0 else "❌"
            print(f"    {strategy_name:12s} | recall@5={r_at_k:.2f} | MRR={mrr:.2f} | "
                  f"top_sim={result['top_similarity']:.3f} | {hit}")

        # Pause between queries for rate limit
        if i < len(EVAL_QUERIES) - 1:
            print("    (pausing 20s for rate limit...)")
            time.sleep(20)

    # ── Phase 3: Aggregate Results ────────────────────────────────────

    print(f"\n{'=' * 70}")
    print("RESULTS SUMMARY")
    print(f"{'=' * 70}")

    print(f"\n{'Strategy':<12} | {'Chunks':>6} | {'Avg Size':>8} | "
          f"{'Recall@5':>8} | {'MRR':>6} | {'Avg Top Sim':>11}")
    print("-" * 70)

    for strategy_name in STRATEGIES:
        stats = all_stats[strategy_name]
        results = results_by_strategy[strategy_name]

        avg_recall = sum(r["recall_at_5"] for r in results) / len(results)
        avg_mrr = sum(r["mrr"] for r in results) / len(results)
        avg_sim = sum(r["top_similarity"] for r in results) / len(results)

        print(f"{strategy_name:<12} | {stats['total_chunks']:>6} | "
              f"{stats['avg_chunk_size']:>6} ch | "
              f"{avg_recall:>8.2f} | {avg_mrr:>6.2f} | {avg_sim:>11.3f}")

    # ── Phase 4: Per-Query Breakdown ──────────────────────────────────

    print(f"\n{'=' * 70}")
    print("PER-QUERY BREAKDOWN")
    print(f"{'=' * 70}")

    for i, test in enumerate(EVAL_QUERIES):
        print(f"\n  Q{i + 1}: \"{test['query'][:70]}\"")
        print(f"       Expected: {test['relevant_sources']}")

        for strategy_name in STRATEGIES:
            result = results_by_strategy[strategy_name][i]
            top_source = result["retrieved"][0]["source"] if result["retrieved"] else "none"
            hit = "✅" if result["recall_at_5"] == 1.0 else "❌"
            print(f"       {strategy_name:12s}: top={top_source:<30s} sim={result['top_similarity']:.3f} {hit}")

    # ── Phase 5: Analysis ─────────────────────────────────────────────

    print(f"\n{'=' * 70}")
    print("ANALYSIS")
    print(f"{'=' * 70}")

    # Find which strategy won the most queries
    wins = {name: 0 for name in STRATEGIES}
    for i in range(len(EVAL_QUERIES)):
        best_strategy = None
        best_sim = -1
        for strategy_name in STRATEGIES:
            result = results_by_strategy[strategy_name][i]
            if result["recall_at_5"] == 1.0 and result["top_similarity"] > best_sim:
                best_sim = result["top_similarity"]
                best_strategy = strategy_name
        if best_strategy:
            wins[best_strategy] += 1

    print("\nQueries won (highest similarity among strategies with recall=1.0):")
    for name, count in wins.items():
        print(f"  {name}: {count}/10")

    # Save full results to JSON
    output = {
        "stats": all_stats,
        "results": {
            name: [
                {
                    "query": r["query"],
                    "recall_at_5": r["recall_at_5"],
                    "mrr": r["mrr"],
                    "top_similarity": r["top_similarity"],
                    "top_source": r["retrieved"][0]["source"] if r["retrieved"] else None,
                    "expected_sources": r["expected_sources"],
                }
                for r in results
            ]
            for name, results in results_by_strategy.items()
        },
    }

    with open("results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nFull results saved to results.json")


if __name__ == "__main__":
    run_evaluation()