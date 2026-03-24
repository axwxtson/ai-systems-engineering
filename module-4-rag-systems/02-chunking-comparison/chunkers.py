"""
chunkers.py — Three chunking strategies for comparison.

Strategy 1: Fixed-size (500 chars, 100 char overlap)
Strategy 2: Recursive (800 chars max, split by structure)
Strategy 3: Semantic (split at topic boundaries using embedding similarity)

Each strategy takes a document string and returns a list of chunk strings.
"""

import numpy as np
import voyageai
import time
from config import EMBEDDING_MODEL


# ── Strategy 1: Fixed-Size Chunking ───────────────────────────────────

def chunk_fixed(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split text into fixed-size chunks with overlap.

    Simple and predictable but cuts mid-sentence.
    Every chunk is exactly chunk_size chars (except possibly the last).
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
    return chunks


# ── Strategy 2: Recursive Chunking ────────────────────────────────────

def chunk_recursive(text: str, max_size: int = 800, overlap: int = 150) -> list[str]:
    """Split text respecting document structure.

    Tries separators in order: paragraphs → newlines → sentences → hard split.
    Same implementation as Exercise 4.1.
    """
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

    # Fallback: fixed-size
    return chunk_fixed(text, max_size, overlap)


# ── Strategy 3: Semantic Chunking ─────────────────────────────────────

def chunk_semantic(text: str, similarity_threshold: float = 0.75, min_chunk_size: int = 100) -> list[str]:
    """Split text at topic boundaries using embedding similarity.

    1. Split into sentences
    2. Embed each sentence
    3. Compare consecutive sentence pairs
    4. Split where similarity drops below threshold

    More expensive (requires embedding every sentence) but produces
    topically coherent chunks regardless of formatting.
    """
    # Split into sentences (rough but effective for our documents)
    raw_sentences = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        # Split on sentence-ending punctuation
        parts = paragraph.replace(". ", ".|").replace("? ", "?|").replace("! ", "!|").split("|")
        for part in parts:
            part = part.strip()
            if len(part) > 20:  # Skip very short fragments
                raw_sentences.append(part)

    if len(raw_sentences) <= 2:
        return [text.strip()] if text.strip() else []

    # Embed all sentences
    vo = voyageai.Client()
    # Batch embed — rate limit safe since it's one call
    result = vo.embed(
        texts=raw_sentences,
        model=EMBEDDING_MODEL,
        input_type="document",
    )
    embeddings = result.embeddings

    # Find topic boundaries
    chunks = []
    current_chunk_sentences = [raw_sentences[0]]

    for i in range(1, len(raw_sentences)):
        # Cosine similarity between consecutive sentences
        a = np.array(embeddings[i - 1])
        b = np.array(embeddings[i])
        similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        if similarity < similarity_threshold and len(" ".join(current_chunk_sentences)) >= min_chunk_size:
            # Topic changed and current chunk is big enough — split here
            chunks.append(" ".join(current_chunk_sentences))
            current_chunk_sentences = [raw_sentences[i]]
        else:
            current_chunk_sentences.append(raw_sentences[i])

    # Don't forget the last chunk
    if current_chunk_sentences:
        chunks.append(" ".join(current_chunk_sentences))

    return chunks


# ── Chunking Dispatcher ───────────────────────────────────────────────

STRATEGIES = {
    "fixed": chunk_fixed,
    "recursive": chunk_recursive,
    "semantic": chunk_semantic,
}


def chunk_document(text: str, strategy: str) -> list[str]:
    """Chunk a document using the named strategy."""
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy}. Choose from: {list(STRATEGIES.keys())}")
    return STRATEGIES[strategy](text)