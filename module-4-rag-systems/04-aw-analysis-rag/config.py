# config.py — Settings for AW Analysis RAG integration

EMBEDDING_MODEL = "voyage-3"
RERANK_MODEL = "rerank-2"
EMBEDDING_DIMENSIONS = 1024
TOP_K = 5
RETRIEVAL_K = 20  # Retrieve top-20, rerank to top-5
CHROMA_PATH = "./chroma_db"
CLAUDE_MODEL = "claude-sonnet-4-20250514"
MEMORY_FILE = "agent_memory.json"
KNOWLEDGE_DIR = "knowledge_base"

# pgvector settings (for production — uncomment and configure when ready)
# PGVECTOR_HOST = "localhost"
# PGVECTOR_PORT = 5432
# PGVECTOR_DB = "aw_analysis"
# PGVECTOR_USER = "postgres"
# PGVECTOR_PASSWORD = "your-password"