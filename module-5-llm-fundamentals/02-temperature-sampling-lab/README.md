# Exercise 5.2: Temperature and Sampling Lab

## What This Is

A statistical experiment that measures how temperature and top-p sampling parameters affect Claude's output diversity. Sends the same prompts at different settings, runs 10 trials each, and compares the results quantitatively.

## Why It Matters

Every API call you make includes sampling parameters. Most developers set them by gut feel. This exercise gives you empirical data — you'll see exactly how much diversity each setting introduces, which prompt types are most affected, and why temperature 0 isn't fully deterministic.

For interviews: "I ran 150 API calls and measured output variance statistically" beats "I usually set temperature to 0."

## Setup
```bash
# Install dependencies
pip3 install anthropic python-Levenshtein numpy colorama

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Usage
```bash
PYTHONPATH=$(pwd) python3 main.py
```

Note: `PYTHONPATH=$(pwd)` is needed for Python 3.14's module resolution.

**Important:** Claude's API enforces that only one of `temperature` or `top_p` may be specified per call, not both. The sampling logic handles this automatically — when top_p is set, temperature is omitted (defaults to 1.0).

## What It Tests

**3 prompt types:**

| Prompt Type | Prompt | Expected Behaviour |
|---|---|---|
| Factual Q&A | "What is the capital of Australia?" | Should converge regardless of temperature |
| Creative | "Write a one-sentence tagline for a crypto trading platform" | Should show high variance at high temps |
| Analytical | "List exactly 3 risks of investing in Bitcoin" | Middle ground — consistent themes, varied wording |

**4 temperature settings:** 0, 0.3, 0.7, 1.0 (10 runs each)

**3 top-p settings:** 0.5, 0.9, 1.0 at default temperature (10 runs each, creative prompt only)

## Metrics

| Metric | What It Measures |
|---|---|
| Unique count | How many distinct outputs across 10 runs |
| Unique ratio | Fraction of outputs that are unique |
| Avg edit distance | Character-level difference (Levenshtein) |
| Normalised edit distance | Edit distance / avg output length |
| Jaccard similarity | Word-level overlap between pairs |
| Length CV | Coefficient of variation of output length |

## Acceptance Criteria

- [x] Test at least 4 temperature settings with 10 runs each
- [x] Statistical comparison of output diversity at each setting
- [x] Test with at least 3 prompt types
- [x] Documented recommendations for when to use which setting
- [x] Explanation of why temperature 0 still has some variance
- [x] Total API cost tracked and reported

## Key Findings

**Temperature is not linear — 0.3 is effectively deterministic on short outputs.**
On the creative tagline prompt, temp=0 and temp=0.3 both produced the identical output 10/10 runs. The distribution at 0.3 is still peaky enough that the top token wins every decision. Real diversity only kicks in between 0.4-0.7. The guidance "0-0.3 for factual, 0.7-1.0 for creative" is correct because the middle band is where transition actually happens — not a gradual slope.

**Top-p=0.5 at temp=1.0 collapses to deterministic output.**
Even at maximum temperature, aggressive top-p (covering only 50% of probability mass) produced identical outputs 10/10. For short high-confidence tasks, the top 2-3 tokens cover >50% of probability, so top_p=0.5 is effectively greedy decoding. Top-p acts like a temperature reducer when set aggressively.

**Top-p=0.9 is the sweet spot — 30% reduction in diversity from top-p=1.0 (7 unique vs 10).**
Removes the unlikely tail without eliminating exploration. This is why it's the common production default.

**Length CV is the hidden signal.**
On the analytical prompt, length CV stayed low (0.011 → 0.044) across all temperatures. On the creative prompt, length CV jumped to 0.319 at temp=0.7. When the model has latitude, it produces fundamentally different *structures*, not just different words. Length variance is a stronger indicator of behavioural divergence than edit distance.

**Longer outputs amplify temperature effects.**
Analytical at temp=0.3 got 7/10 unique outputs; factual at temp=0.3 got only 2/10. Same temperature, very different diversity — because the analytical prompt has ~2x as many tokens, each a decision point where drift can occur. Temperature acts per-token, so accumulated variance compounds with output length.

## Understanding Check — Q&A

**Q1: Compare `temp=1.0, top_p=0.9` vs `temp=0.7` with no top-p. Which is more diverse?**

Counter-intuitively, `temp=1.0 + top_p=0.9` is more diverse. Temperature reduction flattens every token's probability toward uniform, reducing the advantage of the top tokens — but all tokens stay in play. Top-p=0.9 keeps the raw distribution intact (top tokens still dominate) but trims the bottom 10% of probability mass. The data shows this: temp=0.7 gave 4/10 unique outputs on the creative prompt, while temp=1.0 with top_p=0.9 gave 7/10 unique. For production, `temp=1.0 + top_p=0.9` gives exploration with a safety rail — full freedom among plausible tokens, never reaching into the unlikely tail.

**Q2: Why does temp=0 show more variance on long structured outputs than short factual ones?**

Each token generation is a decision point, and GPU non-determinism can flip any one of them. Short output = few decision points = low compound probability of drift. Long output = many decision points = higher probability that *at least one* gets nudged by floating-point noise. It's accumulated probability — if any token in the sequence flips, downstream tokens diverge. This is why the analytical prompt showed 2 unique outputs at temp=0 while the factual prompt showed only 1.

**Q3: A colleague wants temp=0.3 for structured JSON extraction "to give the model some flexibility." What's the counter-argument?**

The data shows temp=0.3 produces outputs identical to temp=0 for short tasks — the creative prompt gave the exact same tagline 10/10 runs at both temperatures. So temp=0.3 provides zero flexibility benefit while introducing non-zero risk of format drift on the rare tokens that do flip ("bullish" vs "Bullish" vs "BULLISH" would break parsing). You're paying real risk for a benefit the experiment proves doesn't exist at low temperatures on short outputs. For structured output, temp=0 is correct — not because 0.3 would be dramatically wrong, but because it's strictly dominated by 0.

## Connection to AW Analysis

- Tool use and structured output: temperature 0 (confirmed by data — low temps give no meaningful flexibility on short outputs)
- Market analysis responses: temperature 0-0.3 (consistency matters, 0.3 still near-deterministic)
- User-facing summaries: `temp=1.0, top_p=0.9` for genuine variety with a safety rail
- Never use high temperature for anything that feeds into downstream processing

## Files

sampling.py   — API call logic, prompt definitions, experiment runners
analysis.py   — Diversity metrics, statistical analysis, cost calculation
main.py       — CLI entry point, display formatting (run this)
README.md     — This file

## Cost

150 API calls to Haiku. Total cost: ~$0.03.