"""
ingest.py — Ingest knowledge base documents for AW Analysis.

Loads documents from knowledge_base/, chunks them, embeds with Voyage,
stores in the "knowledge_base" RAG collection.

Run this once, or whenever you add new documents to the knowledge_base/ folder.
The knowledge base is separate from agent memory — it holds reference documents
(market reports, research notes) while memory holds past agent analyses.
"""

import os
from config import KNOWLEDGE_DIR
from rag_pipeline import RAGCollection, recursive_chunk


def load_documents(docs_dir: str) -> list[dict]:
    """Load all .md files from the knowledge base directory."""
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


def run_ingestion():
    """Ingest all knowledge base documents."""
    print("=" * 60)
    print("AW Analysis — Knowledge Base Ingestion")
    print("=" * 60)

    # Load documents
    print(f"\n[1/3] Loading documents from {KNOWLEDGE_DIR}/...")
    documents = load_documents(KNOWLEDGE_DIR)
    print(f"  Loaded {len(documents)} documents")

    if not documents:
        print("  No documents found! Add .md files to knowledge_base/")
        return

    # Chunk
    print("\n[2/3] Chunking documents...")
    all_texts = []
    all_ids = []
    all_metadatas = []

    for doc in documents:
        chunks = recursive_chunk(doc["content"])
        for i, chunk_text in enumerate(chunks):
            all_texts.append(chunk_text)
            all_ids.append(f"{doc['filename']}::chunk_{i}")
            all_metadatas.append({
                "source": doc["filename"],
                "title": doc["title"],
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

    print(f"  {len(all_texts)} chunks from {len(documents)} documents")

    # Embed and store
    print("\n[3/3] Embedding and storing...")
    collection = RAGCollection("knowledge_base")
    collection.clear()  # Clean re-ingestion
    collection.add_documents(texts=all_texts, ids=all_ids, metadatas=all_metadatas)
    print(f"  Stored {collection.collection.count()} chunks")

    print(f"\n{'=' * 60}")
    print("Ingestion complete!")
    print("=" * 60)


if __name__ == "__main__":
    run_ingestion()