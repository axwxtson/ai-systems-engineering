"""
query.py — RAG Query Pipeline

Embeds a user query, retrieves relevant chunks from ChromaDB,
and generates an answer with Claude that cites its sources.

Pipeline: Query → Embed → Retrieve → Generate (with sources)
"""

import time
import voyageai
import chromadb
import anthropic
from config import (
    EMBEDDING_MODEL,
    TOP_K,
    COLLECTION_NAME,
    CHROMA_PATH,
    CLAUDE_MODEL,
)


# ── System Prompt ─────────────────────────────────────────────────────

RAG_SYSTEM_PROMPT = """You are an AI market research analyst. You answer questions based ONLY on the provided source documents.

<rules>
- Base your answer ONLY on the provided context. Do not use prior knowledge.
- If the context doesn't contain enough information to answer, say so explicitly.
- Cite your sources using [Source: filename] after each claim.
- If sources conflict, note the discrepancy.
- Be specific — use numbers, dates, and data points from the sources.
</rules>

<output_format>
Provide a clear, structured answer. After the answer, include a Sources section listing all documents referenced.
</output_format>"""


# ── Step 1: Embed Query ───────────────────────────────────────────────

def embed_query(query: str) -> list[float]:
    """Embed the search query using Voyage AI.

    Uses input_type="query" — Voyage optimises differently for queries
    vs documents. Queries are short and specific; the model adjusts
    its embedding strategy accordingly.
    """
    vo = voyageai.Client()
    result = vo.embed(
        texts=[query],
        model=EMBEDDING_MODEL,
        input_type="query",  # NOT "document" — this is a search query
    )
    return result.embeddings[0]


# ── Step 2: Retrieve from ChromaDB ────────────────────────────────────

def retrieve(query_embedding: list[float], n_results: int = TOP_K) -> dict:
    """Search ChromaDB for the most similar chunks to the query.

    Returns the raw ChromaDB results dict with:
    - documents: the chunk texts
    - metadatas: source info for each chunk
    - distances: cosine distances (lower = more similar)
    """
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(COLLECTION_NAME)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )
    return results


# ── Step 3: Format Context for Claude ─────────────────────────────────

def format_context(results: dict) -> str:
    """Format retrieved chunks into a context block for Claude.

    Each chunk is wrapped in XML tags with its source info.
    This makes it easy for Claude to cite specific sources.
    """
    context_parts = []
    for i in range(len(results["documents"][0])):
        doc_text = results["documents"][0][i]
        metadata = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        similarity = 1 - distance  # cosine distance → cosine similarity

        context_parts.append(
            f'<source file="{metadata["source"]}" '
            f'title="{metadata["title"]}" '
            f'chunk="{metadata["chunk_index"] + 1}/{metadata["total_chunks"]}" '
            f'relevance="{similarity:.3f}">\n'
            f'{doc_text}\n'
            f'</source>'
        )

    return "\n\n".join(context_parts)


# ── Step 4: Generate Answer with Claude ───────────────────────────────

def generate_answer(query: str, context: str) -> dict:
    """Send the query + retrieved context to Claude for answer generation.

    The system prompt instructs Claude to only use the provided context
    and cite sources. This is the "augmented generation" in RAG.
    """
    client = anthropic.Anthropic()

    user_message = f"""<context>
{context}
</context>

<question>
{query}
</question>"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        system=RAG_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return {
        "answer": response.content[0].text,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }


# ── Full Query Pipeline ──────────────────────────────────────────────

def query_rag(query: str, verbose: bool = True) -> dict:
    """Run the full RAG query pipeline.

    Pipeline: Query → Embed → Retrieve → Format → Generate

    Returns:
        dict with 'answer', 'sources', 'timing', and 'tokens'
    """
    timings = {}

    # Step 1: Embed query
    if verbose:
        print(f"\n[1/3] Embedding query...")
    t0 = time.time()
    query_embedding = embed_query(query)
    timings["embed"] = time.time() - t0
    if verbose:
        print(f"  Done ({timings['embed']:.3f}s)")

    # Step 2: Retrieve
    if verbose:
        print(f"[2/3] Retrieving top-{TOP_K} chunks...")
    t0 = time.time()
    results = retrieve(query_embedding)
    timings["retrieve"] = time.time() - t0
    if verbose:
        print(f"  Done ({timings['retrieve']:.3f}s)")
        # Show what was retrieved
        for i in range(len(results["documents"][0])):
            meta = results["metadatas"][0][i]
            dist = results["distances"][0][i]
            sim = 1 - dist
            print(f"    [{sim:.3f}] {meta['source']} (chunk {meta['chunk_index'] + 1}/{meta['total_chunks']})")

    # Step 3: Generate
    if verbose:
        print(f"[3/3] Generating answer with {CLAUDE_MODEL}...")
    context = format_context(results)
    t0 = time.time()
    generation = generate_answer(query, context)
    timings["generate"] = time.time() - t0
    if verbose:
        print(f"  Done ({timings['generate']:.3f}s)")

    # Collect unique sources
    sources = list(set(
        results["metadatas"][0][i]["source"]
        for i in range(len(results["documents"][0]))
    ))

    total_time = sum(timings.values())

    return {
        "query": query,
        "answer": generation["answer"],
        "sources": sources,
        "timing": {**timings, "total": total_time},
        "tokens": {
            "input": generation["input_tokens"],
            "output": generation["output_tokens"],
        },
    }


# ── Interactive CLI ───────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("RAG Query System — Market Research")
    print("Type 'quit' to exit")
    print("=" * 60)

    while True:
        query = input("\nQuery: ").strip()
        if not query:
            continue
        if query.lower() == "quit":
            break

        result = query_rag(query)

        print(f"\n{'─' * 60}")
        print(result["answer"])
        print(f"\n{'─' * 60}")
        print(f"Sources: {', '.join(result['sources'])}")
        print(f"Timing: embed={result['timing']['embed']:.2f}s, "
              f"retrieve={result['timing']['retrieve']:.2f}s, "
              f"generate={result['timing']['generate']:.2f}s, "
              f"total={result['timing']['total']:.2f}s")
        print(f"Tokens: {result['tokens']['input']} in, {result['tokens']['output']} out")


if __name__ == "__main__":
    main()