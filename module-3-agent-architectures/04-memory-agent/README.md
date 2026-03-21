# Exercise 3.4: Agent with Memory

## What This Is

The AW Analysis agent from Exercise 3.3, extended with persistent long-term memory. Past analyses are auto-saved to a JSON file and exposed as a searchable tool. The agent can recall, summarise, and compare against its own previous work.

## What It Demonstrates

- **Long-term memory**: Analyses persist across sessions via JSON file
- **Memory as a tool**: `search_past_analyses` is just another tool Claude can call
- **Auto-save**: Every completed analysis saved with timestamp and metadata
- **Keyword search**: Memories retrieved by word matching (upgrades to vector search in Module 4)
- **Context management**: Response previews truncated to 500 chars to avoid flooding context

## How to Run

\`\`\`bash
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
python3 main.py
\`\`\`

## File Structure

- `memory.py` — save_analysis, load_all_memories, search_memories
- `tools.py` — Exercise 3.3 tools + search_past_analyses
- `agent.py` — Identical to Exercise 3.3 (agent loop doesn't change)
- `prompts.py` — System prompt with memory tool added
- `main.py` — Persistent CLI loop with auto-save and history command

## Connection to AW Analysis

This is the complete analysis engine with memory. In production, memory.py upgrades from JSON file to PostgreSQL, and keyword search upgrades to vector search with embeddings (Module 4 RAG). The architecture stays the same.
```
