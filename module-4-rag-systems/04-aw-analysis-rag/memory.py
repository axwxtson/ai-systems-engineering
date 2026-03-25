"""
memory.py — Vector-based memory for AW Analysis agent.

This replaces Exercise 3.4's keyword-matching search_memories with
embedding-based semantic search. The interface is identical — save_analysis,
load_all_memories, search_memories — so the agent doesn't know anything changed.

Memories are stored in two places:
  1. agent_memory.json — flat file for persistence and the 'history' command
  2. ChromaDB "agent_memories" collection — for vector search

The JSON file is the source of truth. On startup, if the ChromaDB collection
is empty but the JSON file has data, we re-ingest from the JSON file.
"""

import os
import json
from datetime import datetime
from config import MEMORY_FILE
from rag_pipeline import RAGCollection


# ── Singleton Collection ──────────────────────────────────────────────

_memory_collection = None


def get_memory_collection() -> RAGCollection:
    """Get or create the memory RAG collection.

    Lazy initialisation — only created when first needed.
    If the JSON file has memories but ChromaDB is empty, re-ingest them.
    """
    global _memory_collection
    if _memory_collection is None:
        _memory_collection = RAGCollection("agent_memories")

        # Sync: if JSON has memories but ChromaDB is empty, re-ingest
        json_memories = _load_json_memories()
        if len(json_memories) > 0 and _memory_collection.collection.count() == 0:
            print("  [Memory] Re-ingesting memories from JSON into vector store...")
            _ingest_memories_to_vector(json_memories)

    return _memory_collection


# ── JSON File Operations (source of truth) ────────────────────────────

def _load_json_memories() -> list:
    """Load all memories from JSON file."""
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)


def _save_json_memories(memories: list):
    """Save all memories to JSON file."""
    with open(MEMORY_FILE, "w") as f:
        json.dump(memories, f, indent=2)


def _ingest_memories_to_vector(memories: list):
    """Ingest a list of memories into the vector store."""
    collection = get_memory_collection()

    texts = []
    ids = []
    metadatas = []

    for i, memory in enumerate(memories):
        # The searchable text combines query and response
        text = f"Query: {memory['query']}\n\nAnalysis: {memory['response']}"
        texts.append(text)
        ids.append(f"memory_{memory['timestamp']}")
        metadatas.append({
            "query": memory["query"],
            "timestamp": memory["timestamp"],
            "tool_calls": memory.get("metadata", {}).get("tool_calls", 0),
        })

    if texts:
        collection.add_documents(texts=texts, ids=ids, metadatas=metadatas)


# ── Public Interface (same as Exercise 3.4) ───────────────────────────

def save_analysis(query: str, response: str, metadata: dict):
    """Save a completed analysis to both JSON and vector store.

    Called by main.py after each successful analysis.
    This is the ONLY function that writes to memory.
    """
    timestamp = datetime.now().isoformat()

    # 1. Save to JSON (source of truth)
    memories = _load_json_memories()
    memory_entry = {
        "timestamp": timestamp,
        "query": query,
        "response": response,
        "metadata": metadata,
    }
    memories.append(memory_entry)
    _save_json_memories(memories)

    # 2. Add to vector store
    collection = get_memory_collection()
    text = f"Query: {query}\n\nAnalysis: {response}"
    collection.add_documents(
        texts=[text],
        ids=[f"memory_{timestamp}"],
        metadatas=[{
            "query": query,
            "timestamp": timestamp,
            "tool_calls": metadata.get("tool_calls", 0),
        }],
    )


def load_all_memories() -> list:
    """Load all memories. Used by the 'history' command."""
    return _load_json_memories()


def search_memories(query: str, limit: int = 5) -> list:
    """Search memories using vector-based semantic search.

    THIS IS THE FUNCTION THAT CHANGED FROM EXERCISE 3.4.

    Exercise 3.4 (keyword matching):
        query_words = set(query.lower().split())
        matches = sum(1 for word in query_words if word in memory_text)

    Exercise 4.4 (vector search):
        query_embedding = embed(query)
        results = hybrid_search(query_embedding) + rerank

    Same interface. Same return format. Dramatically better retrieval.
    "cryptocurrency market downturn" now finds "Bitcoin price crashed".
    """
    collection = get_memory_collection()
    results = collection.search(query, top_k=limit, use_rerank=True)

    # Format results to match what the agent expects
    # (same structure as Exercise 3.4's search_memories return)
    formatted = []
    for result in results:
        formatted.append({
            "query": result["metadata"].get("query", ""),
            "timestamp": result["metadata"].get("timestamp", ""),
            "response": result["text"],  # Contains "Query: ...\n\nAnalysis: ..."
            "relevance_score": result["score"],
        })
    return formatted