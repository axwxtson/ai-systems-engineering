# Exercise 1.4: Prompt Caching Cost Analysis

Measures the cost impact of Anthropic's prompt caching on repeated API calls 
with the same system prompt.

## Run it
```bash
pip install anthropic
export ANTHROPIC_API_KEY="your-key"
python3 main.py
```

## Results

See results.md for full analysis. Key finding: 77% input cost reduction 
with caching, approaching 90% at higher volumes.

## Key concepts demonstrated

- cache_control ephemeral breakpoints
- Cache creation vs cache read token accounting
- Cost modelling for production LLM systems