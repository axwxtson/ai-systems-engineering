"""
rag_pipeline.py — Shared RAG infrastructure for AW Analysis.

This is the retrieval engine that powers both tools:
  - search_knowledge_base (documents)
  - search_past_analyses (memory)

Each tool has its own ChromaDB collection and BM25 index,
but they share the same embed/retrieve/rerank logic.

In production, swap ChromaDB for pgvector — the interface stays the same.
"""

import os
import time
import json
import voyageai
import chromadb
import numpy as np
from rank_bm25 import BM25Okapi
from config import (
    EMBEDDING_MODEL,
    RERANK_MODEL,
    TOP_K,
    RETRIEVAL_K,
    CHROMA_PATH,
)


# ── Chunking (reused from Exercise 4.1) ──────────────────────────────

def recursive_chunk(text: str, max_size: int = 800, overlap: int = 150) -> list[str]:
    """Split text respecting document structure."""
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


# ── RAG Collection ────────────────────────────────────────────────────

class RAGCollection:
    """A searchable collection of embedded documents.

    Wraps ChromaDB + BM25 into one object with hybrid search + reranking.
    Both the knowledge base tool and the memory tool create one of these.

    In production, replace the ChromaDB calls with pgvector SQL queries.
    The interface (add_documents, search) stays identical.
    """

    def __init__(self, name: str):
        self.name = name
        self.vo = voyageai.Client()
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

        # Get or create the collection
        try:
            self.collection = self.chroma_client.get_collection(name)
        except Exception:
            self.collection = self.chroma_client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )

        # BM25 index (rebuilt from stored documents)
        self._rebuild_bm25()

    def _rebuild_bm25(self):
        """Rebuild BM25 index from stored documents."""
        count = self.collection.count()
        if count == 0:
            self.bm25 = None
            self.bm25_ids = []
            self.bm25_docs = []
            return

        # Fetch all documents from ChromaDB
        all_data = self.collection.get(include=["documents"])
        self.bm25_ids = all_data["ids"]
        self.bm25_docs = all_data["documents"]
        tokenized = [doc.lower().split() for doc in self.bm25_docs]
        self.bm25 = BM25Okapi(tokenized)

    def add_documents(
        self,
        texts: list[str],
        ids: list[str],
        metadatas: list[dict],
    ):
        """Add documents to the collection (embed + store + update BM25).

        Call this during ingestion (knowledge base) or after each analysis (memory).
        """
        # Embed
        embeddings = []
        batch_size = 128
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            result = self.vo.embed(texts=batch, model=EMBEDDING_MODEL, input_type="document")
            embeddings.extend(result.embeddings)

        # Store in ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        # Rebuild BM25 with the new documents included
        self._rebuild_bm25()

    def search(self, query: str, top_k: int = TOP_K, use_rerank: bool = True) -> list[dict]:
        """Hybrid search with optional reranking.

        1. Dense search (vector similarity)
        2. Sparse search (BM25)
        3. RRF fusion
        4. Voyage reranking (optional)

        Returns list of dicts with 'text', 'metadata', and 'score'.
        """
        if self.collection.count() == 0:
            return []

        # ── Dense retrieval ───────────────────────────────────────────
        query_embedding = self.vo.embed(
            texts=[query], model=EMBEDDING_MODEL, input_type="query"
        ).embeddings[0]

        dense_results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(RETRIEVAL_K, self.collection.count()),
        )

        # Build dense ranked list
        dense_ranked = []
        for i in range(len(dense_results["ids"][0])):
            dense_ranked.append({
                "id": dense_results["ids"][0][i],
                "text": dense_results["documents"][0][i],
                "metadata": dense_results["metadatas"][0][i],
                "score": 1 - dense_results["distances"][0][i],
            })

        # ── Sparse retrieval (BM25) ──────────────────────────────────
        sparse_ranked = []
        if self.bm25 is not None:
            query_tokens = query.lower().split()
            bm25_scores = self.bm25.get_scores(query_tokens)
            top_indices = sorted(
                range(len(bm25_scores)),
                key=lambda i: bm25_scores[i],
                reverse=True
            )[:RETRIEVAL_K]

            for idx in top_indices:
                if bm25_scores[idx] > 0:
                    sparse_ranked.append({
                        "id": self.bm25_ids[idx],
                        "text": self.bm25_docs[idx],
                        "score": float(bm25_scores[idx]),
                    })

        # ── RRF Fusion ────────────────────────────────────────────────
        rrf_scores = {}
        rrf_docs = {}
        k = 60

        for rank, doc in enumerate(dense_ranked):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
            rrf_docs[doc_id] = doc

        for rank, doc in enumerate(sparse_ranked):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
            if doc_id not in rrf_docs:
                # Sparse-only result — need to fetch metadata from dense results or ChromaDB
                rrf_docs[doc_id] = doc
                # Fetch metadata if not already present
                if "metadata" not in doc:
                    try:
                        fetched = self.collection.get(ids=[doc_id], include=["metadatas"])
                        doc["metadata"] = fetched["metadatas"][0] if fetched["metadatas"] else {}
                    except Exception:
                        doc["metadata"] = {}

        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        candidates = []
        for doc_id in sorted_ids[:RETRIEVAL_K]:
            doc = rrf_docs[doc_id]
            doc["score"] = rrf_scores[doc_id]
            candidates.append(doc)

        # ── Reranking (optional) ──────────────────────────────────────
        if use_rerank and len(candidates) > 0:
            try:
                candidate_texts = [c["text"] for c in candidates]
                reranking = self.vo.rerank(
                    query=query,
                    documents=candidate_texts,
                    model=RERANK_MODEL,
                    top_k=min(top_k, len(candidates)),
                )

                reranked = []
                for result in reranking.results:
                    original = candidates[result.index]
                    reranked.append({
                        "text": original["text"],
                        "metadata": original.get("metadata", {}),
                        "score": result.relevance_score,
                    })
                return reranked
            except Exception as e:
                # Reranking failed — fall back to RRF order
                pass

        # Return top-k from RRF (no reranking or reranking failed)
        return [
            {
                "text": c["text"],
                "metadata": c.get("metadata", {}),
                "score": c["score"],
            }
            for c in candidates[:top_k]
        ]

    def clear(self):
        """Delete and recreate the collection."""
        try:
            self.chroma_client.delete_collection(self.name)
        except Exception:
            pass
        self.collection = self.chroma_client.create_collection(
            name=self.name,
            metadata={"hnsw:space": "cosine"},
        )
        self.bm25 = None
        self.bm25_ids = []
        self.bm25_docs = []