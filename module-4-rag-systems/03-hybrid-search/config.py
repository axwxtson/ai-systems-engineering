# config.py — Shared settings for hybrid search comparison

EMBEDDING_MODEL = "voyage-3"
RERANK_MODEL = "rerank-2"
EMBEDDING_DIMENSIONS = 1024
TOP_K = 5
RETRIEVAL_K = 20  # Retrieve top-20 before reranking to top-5
CHROMA_PATH = "./chroma_db"
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Reuse documents from Exercise 4.1
DOCS_DIR = "../01-rag-from-scratch/documents"