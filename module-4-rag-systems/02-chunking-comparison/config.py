# config.py — Shared settings for chunking comparison

EMBEDDING_MODEL = "voyage-3"
EMBEDDING_DIMENSIONS = 1024
TOP_K = 5
CHROMA_PATH = "./chroma_db"
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# We use the same documents from Exercise 4.1
DOCS_DIR = "../01-rag-from-scratch/documents"