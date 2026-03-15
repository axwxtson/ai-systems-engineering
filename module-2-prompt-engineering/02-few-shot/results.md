# Exercise 2.3: Few-Shot Calibration — Results

## Summary

| Examples | Accuracy | Valid JSON |
|----------|----------|------------|
| 0        | 100%     | 100%       |
| 1        | 100%     | 100%       |
| 3        | 80%      | 100%       |
| 5        | 100%     | 100%       |

## Key Findings

### More examples does not mean better accuracy

I expected a linear improvement — 0 examples worst, 5 examples best. The actual results contradicted this. With 0 and 1 examples, Claude achieved 100% accuracy using its own judgement. At 3 examples, accuracy dropped to 80% as Claude over-anchored on the provided examples instead of reasoning independently.

### The two misclassifications at 3 examples

**Gold headline** — "Gold surges 4% as global recession fears mount and investors flee to safe havens"
- Expected: bullish (gold benefits from fear/recession)
- Got: bearish
- Why: The 3-example set included a bearish example about bank layoffs with negative economic language. Claude pattern-matched "recession fears" to the negative tone of that example, rather than recognising that gold is a safe-haven asset that rises during fear. With 0 examples, Claude applied its own financial knowledge and got this right.

**CEO headline** — "Tech CEO steps down to pursue personal interests, board names interim replacement"
- Expected: bearish
- Got: neutral
- Why: This headline is genuinely ambiguous — the language is soft ("pursue personal interests", "interim replacement" implies continuity). The examples may have shifted Claude's threshold for what counts as bearish, causing it to classify this as neutral.

### Example coverage matters more than example count

5 examples recovered to 100% accuracy not because of the higher count, but because the set included better coverage — specifically the oil headline with conflicting signals ("prices rise on supply concerns but demand outlook weakens"). This taught Claude that surface-level negative language doesn't always determine sentiment, which helped it correctly handle the gold headline.

### JSON validity was never a problem

100% valid JSON across all runs. The `<output_format>` specification with explicit field definitions and the `<constraints>` section were sufficient to guarantee structured output, even with 0 examples. For tasks where Claude already understands the format, few-shot examples add structure consistency but aren't required for it.

### Confidence patterns

Confidence scores were relatively stable across all runs. 5 examples produced the highest average confidence, suggesting more examples give Claude more certainty in its classifications. However, confidence was not correlated with accuracy — the 3-example run had confident but wrong answers.

## Takeaway for Production

The right question isn't "how many examples?" it's "do my examples cover the range of inputs, including edge cases?" A small set of examples that misses important patterns (like asset-specific sentiment or conflicting signals) can actively hurt performance compared to no examples at all.

For AW Analysis: if using few-shot for sentiment classification, ensure examples cover all asset classes (equities, crypto, forex, commodities) and include at least one conflicting-signals case. Test empirically rather than assuming more is better.