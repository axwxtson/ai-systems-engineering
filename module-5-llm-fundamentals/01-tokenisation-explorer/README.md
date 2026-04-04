# Exercise 5.1: Tokenisation Explorer

## What This Is

A tool that visualises how different tokenisers split text, compares token counts across models, and calculates cost implications. Part of Module 5: LLM Fundamentals.

## Why It Matters

Tokenisation directly affects:
- **API costs** — you pay per token, and different content types have very different token efficiencies
- **Context budgets** — your 200k token window is eaten by system prompts, tool definitions, RAG chunks, and conversation history
- **Model behaviour** — novel words or numbers that split across token boundaries can confuse the model

Understanding tokenisation converts "it costs roughly X" into precise cost modelling for production systems.

## Setup

```bash
# Install dependencies
pip3 install anthropic tiktoken colorama

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Usage

```bash
python3 main.py
```

## What It Tests

8 text types, each chosen for a specific reason:

| Text Type | Why |
|---|---|
| English prose | Baseline — standard market report content |
| Python code | Punctuation-heavy, tests efficiency on code |
| Financial numbers | Digits, decimals, percentages — common in AW Analysis |
| Multilingual | Japanese, German, French, Chinese — tests non-English cost |
| Special chars & emoji | Unusual characters, alerts, symbols |
| JSON data | Structured format common in tool use responses |
| Repetitive text | Tests consistency of single-token treatment |
| URLs and hashes | Technical identifiers — worst-case tokenisation |

## Expected Output

The tool produces 4 sections:

1. **Token Boundary Visualisation** — Colour-coded token boundaries using tiktoken (GPT-4 and GPT-4o). Claude's token boundaries aren't available via API, so we show counts only.

2. **Token Count Comparison** — Side-by-side counts across Claude, GPT-4, and GPT-4o for all text types. Green highlights the most efficient tokeniser for each.

3. **Cost Comparison** — Estimated cost for a 10k token input across Claude Opus, Sonnet, Haiku, GPT-4o, GPT-4o-mini, and GPT-4-turbo.

4. **Observations** — Written analysis of patterns: numbers are expensive, code is less efficient than prose, non-English costs more, etc.

## Acceptance Criteria

- [x] Visual output showing token boundaries for 5+ text types
- [x] Token count comparison between Claude and GPT-4 tokenisers
- [x] Cost comparison for a 10k token prompt across models
- [x] Coloured terminal output for token boundary visibility
- [x] Written observations about tokenisation patterns

## Key Findings

**Which tokeniser is most efficient overall?**
GPT-4 and GPT-4o are more efficient than Claude across all text types. GPT-4o's larger vocabulary (200k vs 100k) gives it a slight edge on multilingual text, but the two OpenAI tokenisers were nearly identical on English content.

**Which text type has the worst token efficiency?**
Special characters and emoji — Claude averaged 1.7 chars/token, GPT-4 managed 2.3. The hex hash in the URLs test was similarly bad. Both cases involve character sequences where BPE can't find stable merge patterns because the adjacent pairs are effectively random.

**How much more expensive is non-English text?**
Claude got 2.2 chars/token on multilingual text vs 3.2 on English prose — roughly 45% less efficient. Chinese characters were the most expensive, with GPT-4 splitting individual characters into multiple byte-level tokens.

**What surprised you?**
Claude consistently uses ~24% more tokens than GPT-4 for the same text. The "roughly 4 chars per token" rule of thumb doesn't hold for Claude — it's closer to 3.2 for English prose and drops below 2.0 for financial data and special characters. This means context window and cost estimates based on the 4:1 rule undercount by ~20%.

## Understanding Check — Q&A

**Q1: Hex hashes split into individual characters despite hex chars (0-9, a-f) being common. Why can't BPE handle them efficiently?**

BPE merges are learned from training corpus frequency — "th" appears billions of times and gets merged, but hex pairs like "7f" are essentially random adjacent pairings that rarely recur in natural text. The individual characters are common, but the *pairs* aren't stable enough to justify merge operations during vocabulary construction. Forcing merges would waste vocabulary slots on patterns that almost never recur.

**Q2: Repetitive text showed the biggest efficiency gap — Claude used 34 tokens vs GPT-4's 24 for 24 common English words. What explains the extra 10 tokens?**

GPT-4 treats each "space + word" as a single token (` Bitcoin` = 1 token), achieving perfect 1:1 word-to-token ratio. Claude's tokeniser likely separates some whitespace into standalone tokens — where GPT-4 sees ` Bitcoin` as one token, Claude sees `" "` + `"Bitcoin"` as two. For 24 words, ~10 split spaces produce 34 tokens. Whitespace handling is one of the biggest practical differences between tokeniser implementations. We can't confirm this directly since the Anthropic API only returns counts, not boundaries.

**Q3: Opus is 18.8x more expensive than Haiku per token, but they use the same tokeniser. What does this tell you about where cost savings come from?**

The tokeniser is shared across the Claude model family — identical token counts for identical input. The 18.8x cost difference is pure model selection. This is the entire basis for model routing (Module 7): if Haiku can handle the task, sending it to Opus wastes 18.8x the cost for no benefit. The real optimisation lever is routing, not tokenisation.


## Connection to AW Analysis

- Your market data tool results contain numbers, prices, and percentages — these tokenise poorly. When optimising token usage, consider summarising numerical data.
- System prompts and tool definitions are cached (Module 1), so their token count matters less per-request. But RAG chunks and conversation history are dynamic — optimise those.
- If you add multilingual support, budget 2-3x more tokens for non-English content.

## Files

```
tokeniser.py       — Core tokenisation logic and test texts
cost_calculator.py — Model pricing and cost comparison
main.py            — CLI entry point (run this)
README.md          — This file
```