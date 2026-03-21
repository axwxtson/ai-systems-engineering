import json
import os
from datetime import datetime

MEMORY_FILE = "agent_memory.json"


def save_analysis(query: str, response: str, metadata: dict):
    """Save a completed analysis to long-term memory."""
    memories = load_all_memories()

    memories.append({
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "response": response,
        "metadata": metadata
    })

    with open(MEMORY_FILE, "w") as f:
        json.dump(memories, f, indent=2)


def load_all_memories() -> list:
    """Load all saved memories."""
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)


def search_memories(query: str, limit: int = 5) -> list:
    """
    Search memories by keyword matching.

    Scores each memory by how many query words appear in its
    query + response text. Returns top matches.

    In production, this becomes vector search (Module 4 RAG).
    """
    memories = load_all_memories()
    scored = []

    query_words = set(query.lower().split())
    for memory in memories:
        memory_text = f"{memory['query']} {memory['response']}".lower()
        matches = sum(1 for word in query_words if word in memory_text)
        if matches > 0:
            scored.append((matches, memory))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [memory for _, memory in scored[:limit]]