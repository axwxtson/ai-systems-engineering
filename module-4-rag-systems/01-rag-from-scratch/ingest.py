"""
ingest.py — RAG Ingestion Pipeline

Loads documents from the documents/ folder, chunks them,
embeds chunks using Voyage AI, and stores in ChromaDB.

Run this once (or whenever documents change) before querying.

Pipeline: Document → Chunk → Embed → Store
"""

import os
import time
import voyageai
import chromadb
from config import (
    EMBEDDING_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    COLLECTION_NAME,
    CHROMA_PATH,
)

DOCS_DIR = "documents"


# ── Step 1: Load Documents ─────────────────────────────────────────────

def load_documents(docs_dir: str) -> list[dict]:
    """Load all .md files from the documents directory.

    Returns a list of dicts with 'content', 'filename', and 'title' keys.
    """
    documents = []
    for filename in sorted(os.listdir(docs_dir)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(docs_dir, filename)
        with open(filepath, "r") as f:
            content = f.read()

        # Extract title from first markdown heading, if present
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


# ── Step 2: Chunk Documents ────────────────────────────────────────────

def recursive_chunk(text: str, max_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text using recursive strategy: paragraphs → sentences → hard split.

    Tries to split at natural boundaries. Adds overlap between chunks
    to prevent losing information at boundaries.
    """
    # Base case: text fits in one chunk
    if len(text) <= max_size:
        return [text.strip()] if text.strip() else []

    # Try splitting by paragraphs first, then sentences
    for separator in ["\n\n", "\n", ". "]:
        parts = text.split(separator)
        if len(parts) <= 1:
            continue

        chunks = []
        current = ""

        for part in parts:
            # Re-add the separator (except for paragraph breaks)
            addition = part if separator == "\n\n" else part + ("." if separator == ". " else "")

            # Would adding this part exceed the max size?
            if current and len(current) + len(separator) + len(addition) > max_size:
                chunks.append(current.strip())
                # Start new chunk with overlap from the end of the previous chunk
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

    # Fallback: hard split by characters
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_size
        chunks.append(text[start:end].strip())
        start = end - overlap
    return [c for c in chunks if c]


def chunk_document(doc: dict) -> list[dict]:
    """Chunk a single document. Each chunk keeps metadata about its source.

    This is important for citation — when we retrieve a chunk, we need to
    know which document it came from and where in that document.
    """
    text_chunks = recursive_chunk(doc["content"])
    chunks = []
    for i, chunk_text in enumerate(text_chunks):
        chunks.append({
            "text": chunk_text,
            "source": doc["filename"],
            "title": doc["title"],
            "chunk_index": i,
            "total_chunks": len(text_chunks),
        })
    return chunks


def chunk_all_documents(documents: list[dict]) -> list[dict]:
    """Chunk all documents and return flat list of chunks with metadata."""
    all_chunks = []
    for doc in documents:
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)
    return all_chunks


# ── Step 3: Embed Chunks ──────────────────────────────────────────────

def embed_chunks(chunks: list[dict], batch_size: int = 128) -> list[list[float]]:
    """Embed all chunks using Voyage AI.

    Uses input_type="document" because these are stored documents,
    not search queries. Voyage optimises the embedding differently
    for each type.

    Batches to respect API limits (128 texts per call for Voyage).
    """
    vo = voyageai.Client()
    texts = [chunk["text"] for chunk in chunks]
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"  Embedding batch {i // batch_size + 1} ({len(batch)} chunks)...")
        result = vo.embed(
            texts=batch,
            model=EMBEDDING_MODEL,
            input_type="document",
        )
        all_embeddings.extend(result.embeddings)
        # Brief pause between batches to avoid rate limits
        if i + batch_size < len(texts):
            time.sleep(0.5)

    return all_embeddings


# ── Step 4: Store in ChromaDB ─────────────────────────────────────────

def store_in_chroma(chunks: list[dict], embeddings: list[list[float]]) -> chromadb.Collection:
    """Store chunks and their embeddings in ChromaDB.

    Each chunk gets:
    - An ID (for deduplication)
    - Its embedding vector
    - The raw text (so we can return it in search results)
    - Metadata (source file, title, chunk position)
    """
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Delete existing collection if it exists (clean re-ingestion)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Deleted existing collection '{COLLECTION_NAME}'")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Prepare data for ChromaDB
    ids = [f"{chunk['source']}::chunk_{chunk['chunk_index']}" for chunk in chunks]
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [
        {
            "source": chunk["source"],
            "title": chunk["title"],
            "chunk_index": chunk["chunk_index"],
            "total_chunks": chunk["total_chunks"],
        }
        for chunk in chunks
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    return collection


# ── Main Pipeline ─────────────────────────────────────────────────────

def run_ingestion():
    """Run the full ingestion pipeline: load → chunk → embed → store."""
    print("=" * 60)
    print("RAG Ingestion Pipeline")
    print("=" * 60)

    # Step 1: Load
    print("\n[1/4] Loading documents...")
    documents = load_documents(DOCS_DIR)
    print(f"  Loaded {len(documents)} documents")
    for doc in documents:
        print(f"    - {doc['filename']} ({len(doc['content'])} chars)")

    # Step 2: Chunk
    print("\n[2/4] Chunking documents...")
    chunks = chunk_all_documents(documents)
    print(f"  Created {len(chunks)} chunks from {len(documents)} documents")
    # Show chunk distribution per document
    from collections import Counter
    source_counts = Counter(c["source"] for c in chunks)
    for source, count in sorted(source_counts.items()):
        print(f"    - {source}: {count} chunks")

    # Step 3: Embed
    print(f"\n[3/4] Embedding {len(chunks)} chunks with {EMBEDDING_MODEL}...")
    embeddings = embed_chunks(chunks)
    print(f"  Generated {len(embeddings)} embeddings ({len(embeddings[0])} dimensions each)")

    # Step 4: Store
    print(f"\n[4/4] Storing in ChromaDB at {CHROMA_PATH}...")
    collection = store_in_chroma(chunks, embeddings)
    print(f"  Stored {collection.count()} chunks in collection '{COLLECTION_NAME}'")

    print("\n" + "=" * 60)
    print("Ingestion complete!")
    print(f"  Documents: {len(documents)}")
    print(f"  Chunks: {len(chunks)}")
    print(f"  Avg chunk size: {sum(len(c['text']) for c in chunks) // len(chunks)} chars")
    print("=" * 60)


if __name__ == "__main__":
    run_ingestion()