"""
retrieval.py — Four retrieval methods for comparison.

Method 1: Dense only (vector similarity via ChromaDB)
Method 2: Sparse only (BM25 keyword matching)
Method 3: Hybrid (dense + sparse, fused with RRF)
Method 4: Hybrid + Rerank (hybrid results reranked with Voyage)

All methods share the same document set and chunking strategy (recursive).
"""

import os
import time
import voyageai
import chromadb
from rank_bm25 import BM25Okapi
from config import (
    EMBEDDING_MODEL,
    RERANK_MODEL,
    TOP_K,
    RETRIEVAL_K,
    CHROMA_PATH,
    DOCS_DIR,
)


# ── Document Loading & Chunking ───────────────────────────────────────

def load_documents(docs_dir: str) -> list[dict]:
    """Load all .md files."""
    documents = []
    for filename in sorted(os.listdir(docs_dir)):
        if not filename.endswith(".md"):
            continue
        with open(os.path.join(docs_dir, filename), "r") as f:
            content = f.read()
        title = filename
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line.strip("# ").strip()
                break
        documents.append({"content": content, "filename": filename, "title": title})
    return documents


def recursive_chunk(text: str, max_size: int = 800, overlap: int = 150) -> list[str]:
    """Same recursive chunking as Exercises 4.1 and 4.2."""
    if len(text) <= max_size:
        return [text.strip()] if text.strip() else []

    for separator in ["\n\n", "\n", ". "]:
        parts = text.split(separator)
        if len(parts) <= 1:
            continue
        chunks = []
        current = ""
        for part in parts:
            addition = part if separator == "\n\n" else part + ("." if separator == ". " else "")
            if current and len(current) + len(separator) + len(addition) > max_size:
                chunks.append(current.strip())
                if overlap > 0 and len(current) > overlap:
                    current = current[-overlap:] + separator + addition
                else:
                    current = addition
            else:
                current = current + separator + addition if current else addition
        if current.strip():
            chunks.append(current.strip())
        if len(chunks) > 1:
            return chunks

    # Fallback
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_size
        chunks.append(text[start:end].strip())
        start = end - overlap
    return [c for c in chunks if c]


# ── Shared Index Setup ────────────────────────────────────────────────

class RetrievalIndex:
    """Holds both vector (ChromaDB) and BM25 indices for the same chunks.

    Built once, queried by all four methods.
    """

    def __init__(self):
        self.chunks = []          # list of chunk dicts
        self.chunk_texts = []     # just the text strings
        self.collection = None    # ChromaDB collection
        self.bm25 = None          # BM25 index
        self.vo = voyageai.Client()
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    def build(self, documents: list[dict]):
        """Chunk documents, build both vector and BM25 indices."""
        print("  Chunking documents...")
        for doc in documents:
            doc_chunks = recursive_chunk(doc["content"])
            for i, text in enumerate(doc_chunks):
                self.chunks.append({
                    "id": f"{doc['filename']}::chunk_{i}",
                    "text": text,
                    "source": doc["filename"],
                    "title": doc["title"],
                    "chunk_index": i,
                })
                self.chunk_texts.append(text)

        print(f"  {len(self.chunks)} chunks total")

        # Build ChromaDB vector index
        print("  Building vector index (ChromaDB)...")
        try:
            self.chroma_client.delete_collection("hybrid_search")
        except Exception:
            pass

        self.collection = self.chroma_client.create_collection(
            name="hybrid_search",
            metadata={"hnsw:space": "cosine"},
        )

        # Embed all chunks
        print("  Embedding chunks...")
        embeddings = []
        batch_size = 128
        for i in range(0, len(self.chunk_texts), batch_size):
            batch = self.chunk_texts[i:i + batch_size]
            result = self.vo.embed(texts=batch, model=EMBEDDING_MODEL, input_type="document")
            embeddings.extend(result.embeddings)

        self.collection.add(
            ids=[c["id"] for c in self.chunks],
            embeddings=embeddings,
            documents=self.chunk_texts,
            metadatas=[
                {"source": c["source"], "title": c["title"], "chunk_index": c["chunk_index"]}
                for c in self.chunks
            ],
        )

        # Build BM25 index
        print("  Building BM25 index...")
        tokenized = [text.lower().split() for text in self.chunk_texts]
        self.bm25 = BM25Okapi(tokenized)

        print("  Indices ready.")

    # ── Method 1: Dense Retrieval ─────────────────────────────────────

    def retrieve_dense(self, query: str, top_k: int = TOP_K) -> list[dict]:
        """Pure vector similarity search."""
        query_embedding = self.vo.embed(
            texts=[query], model=EMBEDDING_MODEL, input_type="query"
        ).embeddings[0]

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        retrieved = []
        for i in range(len(results["documents"][0])):
            retrieved.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "source": results["metadatas"][0][i]["source"],
                "score": 1 - results["distances"][0][i],  # cosine similarity
            })
        return retrieved

    # ── Method 2: Sparse Retrieval (BM25) ─────────────────────────────

    def retrieve_sparse(self, query: str, top_k: int = TOP_K) -> list[dict]:
        """BM25 keyword search."""
        query_tokens = query.lower().split()
        scores = self.bm25.get_scores(query_tokens)

        # Get top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        retrieved = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include docs with some keyword match
                retrieved.append({
                    "id": self.chunks[idx]["id"],
                    "text": self.chunks[idx]["text"],
                    "source": self.chunks[idx]["source"],
                    "score": float(scores[idx]),
                })
        return retrieved

    # ── Method 3: Hybrid (Dense + Sparse + RRF) ──────────────────────

    def retrieve_hybrid(self, query: str, top_k: int = TOP_K) -> list[dict]:
        """Hybrid search: dense + sparse, fused with Reciprocal Rank Fusion."""
        # Get more candidates from each method for better fusion
        dense_results = self.retrieve_dense(query, top_k=RETRIEVAL_K)
        sparse_results = self.retrieve_sparse(query, top_k=RETRIEVAL_K)

        # RRF fusion
        rrf_scores = {}
        rrf_docs = {}
        k = 60  # Standard RRF constant

        for rank, doc in enumerate(dense_results):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
            rrf_docs[doc_id] = doc

        for rank, doc in enumerate(sparse_results):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
            rrf_docs[doc_id] = doc

        # Sort by RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        retrieved = []
        for doc_id in sorted_ids[:top_k]:
            doc = rrf_docs[doc_id]
            doc["score"] = rrf_scores[doc_id]
            retrieved.append(doc)

        return retrieved

    # ── Method 4: Hybrid + Rerank ─────────────────────────────────────

    def retrieve_hybrid_rerank(self, query: str, top_k: int = TOP_K) -> list[dict]:
        """Hybrid search + Voyage reranking.

        1. Hybrid retrieves top-20 candidates
        2. Voyage rerank reorders them
        3. Return top-5
        """
        # Get hybrid candidates (more than we need — reranker will filter)
        candidates = self.retrieve_hybrid(query, top_k=RETRIEVAL_K)

        if not candidates:
            return []

        # Rerank with Voyage
        candidate_texts = [c["text"] for c in candidates]

        reranking = self.vo.rerank(
            query=query,
            documents=candidate_texts,
            model=RERANK_MODEL,
            top_k=top_k,
        )

        # Map reranked results back to our chunk metadata
        retrieved = []
        for result in reranking.results:
            original = candidates[result.index]
            retrieved.append({
                "id": original["id"],
                "text": original["text"],
                "source": original["source"],
                "score": result.relevance_score,
            })

        return retrieved


# ── Retrieval Method Registry ─────────────────────────────────────────

METHODS = {
    "dense": "retrieve_dense",
    "sparse": "retrieve_sparse",
    "hybrid": "retrieve_hybrid",
    "hybrid_rerank": "retrieve_hybrid_rerank",
}


def retrieve(index: RetrievalIndex, query: str, method: str, top_k: int = TOP_K) -> list[dict]:
    """Dispatch to the named retrieval method."""
    method_fn = getattr(index, METHODS[method])
    return method_fn(query, top_k=top_k)