# AI Systems Engineering

Structured 8-module learning programme covering LLM API engineering, agent architectures, RAG systems, prompt engineering, evaluation, multi-model orchestration, and tool ecosystem fluency. Every module produces runnable code, documented findings, and interview-ready artefacts.

Built by Alex — CS/Math graduate (Strathclyde), production AI developer.

## What's Here

| Module | Topic | Exercises | Status |
|--------|-------|-----------|--------|
| 1 | LLM API Engineering | Tool use, streaming, prompt caching | ✅ Complete |
| 2 | Advanced Prompt Engineering | CoT, few-shot, prompt chains | ✅ Complete |
| 3 | Agent Architectures | ReAct agent, MCP server, multi-step pipelines | ✅ Complete |
| 4 | RAG Systems | Voyage embeddings, hybrid search, chunking strategies | ✅ Complete |
| 5 | LLM Fundamentals | Tokenisation, temperature sampling, fine-tuning framework | ✅ Complete |
| 6 | Evaluation & Testing | Eval harness, LLM-as-judge, red-teaming | ✅ Complete |
| 7 | Multi-Model Orchestration | Model router, fallback chains with failure injection | ✅ Complete |
| 8 | Tool Ecosystem & Workflows | Framework survey, Langfuse observability, Cursor workflow | ✅ Complete |

## Module Highlights

**Module 1 — LLM API Engineering:** Tool use from scratch, streaming endpoints, prompt caching cost analysis. Built the foundational API patterns everything else extends.

**Module 2 — Advanced Prompt Engineering:** Chain-of-thought, few-shot design, prompt chains vs single prompts. Key finding: single prompt beat chains at small scale due to context loss between stages; example coverage matters more than shot count (3-shot scored worse than 0-shot from pattern-matching bias).

**Module 3 — Agent Architectures:** ReAct agent loop, MCP server, multi-step pipelines with memory. The agent loop pattern from this module is the reference implementation used across all later exercises.

**Module 4 — RAG Systems:** RAG pipeline with Voyage AI embeddings, hybrid search (BM25 + vector + rerank), integrated into AW Analysis. Key finding: all chunking strategies achieved perfect recall because topics were too distinct — corpus difficulty matters as much as pipeline quality.

**Module 5 — LLM Fundamentals:** Tokenisation comparison (Claude vs GPT-4/4o), temperature sampling lab (150-call statistical experiment), fine-tuning decision framework.

**Module 6 — Evaluation & Testing:** Two-layer grader architecture (deterministic + LLM-as-judge), bias testing (v1 rubric showed 0% position consistency and inverted length bias), red-team exercise proving retrieved content is part of the attack surface.

**Module 7 — Multi-Model Orchestration:** Deterministic model router (Haiku/Sonnet/Opus by query class), fallback chains with failure injection. Provider abstraction via Protocol — the same pattern reused in Module 8's observability layer.

**Module 8 — Tool Ecosystem & Workflows:** Framework survey scoring SDK baseline against LangChain/LangGraph/Pydantic AI/LiteLLM on a 6-criterion rubric. Observability spike wiring a router into Langfuse with quality scores in every trace. Cursor workflow with `.cursorrules`, reusable prompts, and context-pinning recipes.

## Key Findings Across Modules

These are the cross-cutting lessons that compound across the programme:

- **Calibrate judges before trusting them** — the Module 6 v1 rubric had 0% position consistency; bias testing is non-optional
- **Primacy/recency validated adversarially** — Module 2's finding that rule position matters was confirmed in Module 6's red-team
- **Retrieved content is part of the attack surface** — Module 6's red-team found planted documents causing system prompt leakage via benign queries
- **Chains are necessary at scale but not for small tasks** — single prompt won every test in Module 2 due to context loss between stages
- **Build the emit layer, buy the backend** — Module 8's observability pattern: own the protocol, swap the vendor at deployment time
- **The rule beats the list** — "I reach for a framework when it owns a layer I don't want to own" is more valuable than "I've used LangChain"

## Portfolio Project

**[AW Analysis](https://github.com/axwxtson/AWAnalysis)** — Cross-asset market intelligence platform covering equities, crypto, forex, and commodities. Built piece by piece alongside this programme, applying each module's patterns as they were learnt. Currently being expanded into a full production system.

## Tech Stack

- Python 3.14, Anthropic SDK (Claude Haiku 4.5 / Sonnet 4 / Opus 4)
- Voyage AI (embeddings), ChromaDB (prototyping), pgvector (production target)
- Langfuse (observability), MCP (Model Context Protocol)
- No heavyweight frameworks — hand-rolled agent loops, routing, and eval harnesses