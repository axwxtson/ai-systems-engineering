# Exercise 2.3: Few-Shot Calibration

## What This Is

An empirical experiment measuring how the number of few-shot examples affects sentiment classification accuracy and output consistency. Tests the same 10 financial headlines against 4 prompt variants (0, 1, 3, and 5 examples).

## What It Demonstrates

- **Few-shot example design:** Crafting examples that calibrate confidence, demonstrate edge cases, and anchor output format
- **Empirical prompt evaluation:** Measuring accuracy and JSON validity across prompt variants rather than relying on intuition
- **Example coverage vs. count:** More examples isn't always better — coverage of edge cases matters more than quantity

## Key Finding

3 examples scored worse (80%) than 0 examples (100%). The examples created a pattern-matching bias that hurt performance on edge cases (gold as a safe-haven asset, ambiguous CEO departure). 5 examples recovered to 100% because the set included better coverage of conflicting-signal scenarios.

## Files

```
02-few-shot/
├── README.md
├── main.py             # Test runner — classifies 10 headlines × 4 prompt variants
├── prompts.py          # Base instruction + example bank + build_prompt(n) function
├── results.md          # Analysis of findings
├── results.json        # Raw output data from all 40 classifications
└── requirements.txt    # anthropic
```

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run experiment (40 API calls)
python3 main.py
```

## Connection to AW Analysis

Sentiment classification from headlines is a core feature of the AW Analysis pipeline. This experiment informs how many and which few-shot examples to include in the production sentiment classifier, and demonstrates that example selection must cover all asset classes and include conflicting-signal cases.