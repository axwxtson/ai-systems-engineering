# Exercise 2.2: Prompt Chain vs Single Prompt — Results

## Summary

| Test Case | Chain Sentiment | Chain Confidence | Single Sentiment | Single Confidence | Better Output |
|-----------|----------------|-----------------|-----------------|-------------------|---------------|
| Bitcoin (rich data) | Bullish | 0.85 | Bullish | 0.8 | Tie |
| Nvidia (mixed signals) | Bullish | 0.8 | Neutral | 0.7 | Single prompt |
| Gold (sparse data) | Bullish | 0.65 | Bullish | 0.7 | Single prompt (slight) |

## Test-by-Test Analysis

### Bitcoin — Rich Data, Clear Signals

Both approaches produced comparable quality. The chain extracted 13 data points and used them systematically. The single prompt covered the same ground with slightly more polished formatting (bold sub-headings on bullet points). Both correctly identified bullish sentiment, cited the same key factors (ETF inflows, volume spike, MicroStrategy purchase), and flagged similar risks (overbought RSI, elevated Fear & Greed Index).

When the input data is clean, structured, and has clear directional signals, the chain adds overhead without meaningfully improving quality. There's nothing for the validation gates to catch and nothing for the extraction stage to clean up.

### Nvidia — Mixed Signals, Moderate Data

This is where the approaches diverged. The chain rated Nvidia bullish (0.8 confidence), while the single prompt rated it neutral (0.7 confidence). The single prompt's neutral call is more defensible — the raw data contains genuinely conflicting signals: 122% revenue growth and a new chip announcement pulling bullish, but 3.2% daily decline, insider selling, export restriction risk, and 65x P/E pulling bearish.

The chain's weakness here was **context loss between stages**. Stage 1 extracted clean data points — "$890 price", "122% YoY revenue growth", "$30M insider selling" — but stripped away the tension between them. Stage 2 received neat JSON and over-indexed on the impressive growth numbers. The single prompt saw everything at once and could weigh the conflicting signals holistically, landing on the more appropriate neutral rating.

### Gold — Sparse, Messy Data

Both reached bullish sentiment. The chain set lower confidence (0.65 vs 0.7) and flagged more specific data gaps. However, the single prompt produced richer analysis — it correctly identified falling real yields as reducing the opportunity cost of holding gold (a specific financial insight), and it appropriately flagged the Twitter analyst's $3,000 target as potential retail speculation rather than institutional optimism.

The chain's Stage 1 only extracted 3 data points from the informal text, missing the real yields signal entirely. That gap cascaded through the remaining stages — Stage 2 couldn't analyse what Stage 1 didn't extract, and Stage 3 couldn't report what Stage 2 didn't find.

## Why the Differences Were Small

The differences between chain and single-prompt output were less dramatic than expected. Three reasons:

1. **The data fit in one context window.** Each test input was a few hundred tokens. Claude could easily hold all the information and reason about it in a single call. Chains add the most value when the input is too large or complex for one prompt to handle — dozens of documents, multiple data sources, thousands of tokens of raw data that need reduction before analysis.

2. **The task wasn't complex enough to need decomposition.** "Read market data and write a brief" is within Claude's single-prompt capability. Chains shine when the task genuinely has distinct phases that benefit from specialised prompts — for example, if Stage 1 needed to call external APIs, or Stage 2 needed different model settings (like extended thinking for complex reasoning).

3. **Context loss is a real cost.** Each stage in the chain only sees the previous stage's output, not the original raw data. Nuance, tone, and implicit signals get lost in the extraction step. The single prompt retains everything. This is an inherent trade-off of chaining.

## When Chains Do Add Value

Despite the single prompt winning here, chains become essential when:

- **Volume exceeds one prompt's capacity** — processing 50 news articles, 30 price feeds, and 10 analyst notes can't fit in one call. A chain reduces the data at each stage.
- **Validation gates catch failures** — all gates passed in this test, but with real messy production data, Stage 1 will sometimes return garbage. Catching it early prevents wasting two more API calls and delivering a bad report to the user.
- **Auditability matters** — when a report is wrong, the chain lets you trace exactly where the failure occurred. Was the extraction bad? The analysis flawed? The formatting misleading? A single prompt is a black box.
- **Different stages need different configurations** — Stage 1 might use Haiku (cheap, fast extraction), Stage 2 might use Opus with extended thinking (deep analysis), Stage 3 might use Sonnet (good formatting, moderate cost). This is Module 7 territory but the architecture starts here.

## Takeaway for AW Analysis

The production AW Analysis pipeline will likely need chains — not because of these simple test cases, but because real analysis involves multiple data sources (price feeds, news APIs, historical data, user context) that exceed what a single prompt can handle coherently. The chain architecture built here is the right foundation, even though these small-scale tests didn't fully demonstrate its advantages.

The immediate lesson: don't chain for the sake of chaining. Start with a single prompt. Move to a chain when you hit a specific limitation — context window, quality inconsistency, debugging difficulty, or the need for per-stage model routing.