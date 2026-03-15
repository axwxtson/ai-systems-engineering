"""
Few-shot calibration experiment.
Four versions of the same prompt with 0, 1, 3, and 5 examples.
"""

BASE_INSTRUCTION = """You are a market sentiment classifier for AW Analysis.
Given a financial headline, classify the sentiment as bullish, bearish, or neutral.

<output_format>
Return a JSON object with exactly these fields:
- headline: the original headline text
- sentiment: exactly one of "bullish", "bearish", or "neutral" (lowercase)
- confidence: a float between 0.0 and 1.0
- reasoning: one sentence explaining the classification
</output_format>"""

EXAMPLES = [
    {
        "input": "Apple reports record Q4 revenue, beating analyst estimates by 12%",
        "output": '{"headline": "Apple reports record Q4 revenue, beating analyst estimates by 12%", "sentiment": "bullish", "confidence": 0.95, "reasoning": "Record revenue with significant earnings beat indicates strong business performance."}'
    },
    {
        "input": "Fed signals potential rate cuts in September amid cooling inflation",
        "output": '{"headline": "Fed signals potential rate cuts in September amid cooling inflation", "sentiment": "bullish", "confidence": 0.75, "reasoning": "Rate cut signals are generally positive for equities, though uncertainty language lowers confidence."}'
    },
    {
        "input": "Major bank announces 10,000 layoffs as loan defaults rise sharply",
        "output": '{"headline": "Major bank announces 10,000 layoffs as loan defaults rise sharply", "sentiment": "bearish", "confidence": 0.9, "reasoning": "Large-scale layoffs combined with rising defaults indicate deteriorating financial conditions."}'
    },
    {
        "input": "Tesla stock trades sideways as market awaits Thursday earnings call",
        "output": '{"headline": "Tesla stock trades sideways as market awaits Thursday earnings call", "sentiment": "neutral", "confidence": 0.85, "reasoning": "Sideways trading with no directional catalyst until the upcoming earnings call."}'
    },
    {
        "input": "Oil prices rise 3% on supply concerns but demand outlook weakens",
        "output": '{"headline": "Oil prices rise 3% on supply concerns but demand outlook weakens", "sentiment": "neutral", "confidence": 0.6, "reasoning": "Conflicting signals with supply-side bullish but demand-side bearish creating mixed outlook."}'
    },
]

CONSTRAINTS = """
<constraints>
- Always return valid JSON and nothing else — no markdown fences, no commentary
- Sentiment must be exactly "bullish", "bearish", or "neutral"
- Confidence reflects how clear the signal is, not how confident you are
- Reasoning must be exactly one sentence
- If the headline is ambiguous, lower the confidence and explain why
</constraints>"""


def build_prompt(num_examples: int) -> str:
    """Build a system prompt with the specified number of examples."""
    prompt = BASE_INSTRUCTION

    if num_examples > 0:
        prompt += "\n\n<examples>"
        for ex in EXAMPLES[:num_examples]:
            prompt += f"\nInput: \"{ex['input']}\""
            prompt += f"\nOutput: {ex['output']}\n"
        prompt += "</examples>"

    prompt += "\n" + CONSTRAINTS
    return prompt