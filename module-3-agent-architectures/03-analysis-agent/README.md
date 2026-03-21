# Exercise 3.3: Multi-Step Analysis Agent (AW Analysis Core)

## What This Is

The core analysis agent for AW Analysis — a production-grade ReAct agent with planning, ToolExecutor retry logic, structured output, and cost tracking. Handles single lookups, deep analysis, multi-asset comparisons, and error cases.

## What It Demonstrates

- **Hybrid planning**: Reactive for simple queries, explicit PLAN for complex ones
- **ToolExecutor**: Production wrapper with retries, logging, timing
- **Structured output**: Consistent analysis format (position, trend, sentiment, summary)
- **Parallel tool calls**: Independent data fetches batched in single steps
- **Cost tracking**: Per-query token and dollar estimates
- **Graceful degradation**: Partial results on max steps, clean error handling

## How to Run

\`\`\`bash
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
python3 main.py
\`\`\`

## File Structure

- `agent.py` — ReAct agent loop with ToolExecutor and cost tracking
- `tools.py` — Tool definitions, mock data (8 assets), ToolExecutor class
- `prompts.py` — System prompt with planning instructions and output format
- `main.py` — CLI entry point
```
