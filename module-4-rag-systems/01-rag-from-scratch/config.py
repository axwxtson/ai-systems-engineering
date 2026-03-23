# config.py — Shared settings for RAG pipeline

EMBEDDING_MODEL = "voyage-3"
EMBEDDING_DIMENSIONS = 1024
CHUNK_SIZE = 800          # characters per chunk
CHUNK_OVERLAP = 150       # overlap between chunks
TOP_K = 5                 # number of chunks to retrieve
COLLECTION_NAME = "market_reports"
CHROMA_PATH = "./chroma_db"
CLAUDE_MODEL = "claude-sonnet-4-20250514"