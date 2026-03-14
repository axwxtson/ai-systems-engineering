# Prompt Caching Cost Analysis — Results

## Test Setup

- **Model:** claude-sonnet-4-20250514
- **System prompt:** ~1,084 tokens (market analyst with detailed analysis frameworks)
- **Query:** "Give me a brief analysis of the current gold market."
- **Max output tokens:** 512
- **Runs:** 10 without caching, 10 with caching
- **Cache type:** ephemeral - temporary cache type of 5 mins. Only cache type Anthropic currently offers
      

## Raw Results

### Without Caching

| Run | Input Tokens | Output Tokens |
|-----|-------------|---------------|
| 1-10 | 1,101 each | 464-512 |
| **Total** | **11,010** | **~5,055** |

### With Caching

| Run | Input Tokens | Cache Creation | Cache Read | Output Tokens |
|-----|-------------|----------------|------------|---------------|
| 1 | 17 | 1,084 | 0 | 512 |
| 2-10 | 17 each | 0 | 1,084 each | 484-512 |
| **Total** | **170** | **1,084** | **9,756** | **~5,060** |

## Cost Comparison

Sonnet pricing: $3.00 per million input tokens, $0.30 per million cache read tokens, $3.75 per million cache write tokens.

### Without Caching
- Input cost: 11,010 tokens × $3.00/M = **$0.03303**

### With Caching
- Regular input cost: 170 tokens × $3.00/M = $0.00051
- Cache creation cost: 1,084 tokens × $3.75/M = $0.00407
- Cache read cost: 9,756 tokens × $0.30/M = $0.00293
- **Total: $0.00751**

### Savings
- **77% reduction in input costs** ($0.03303 → $0.00751)
- At higher volumes (100 calls, 1000 calls), savings approach 90% because the one-time cache creation cost is amortised across more reads

## When Caching Makes Sense

- **Use caching when:** You have a stable system prompt that gets re-used across many requests in a short time window (< 5 minutes). Burst usage patterns like a user doing multiple analysis queries in a session, running eval suites, or batch-style sequential calls.
- **No point when:** Calls are infrequent (hours apart — cache expires in ~5 minutes), the system prompt changes frequently between calls, or the system prompt is short (under 1024 tokens — caching won't activate).

## Cache Breakpoint Placement

The `cache_control` marker goes on the system prompt because it's the largest stable prefix shared across all requests. The user message changes each time, so it can't be cached. In a more complex setup with tool definitions, you'd place the cache breakpoint after tools as well, since those are also stable across requests.