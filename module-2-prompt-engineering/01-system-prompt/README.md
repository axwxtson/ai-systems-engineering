# Exercise 2.1: System Prompt Architecture

## What This Is

A production system prompt for AW Analysis's market analyser, with a test harness that evaluates prompt quality across diverse input scenarios.

## What It Demonstrates

- **System prompt architecture:** Role, task, data handling, output format, constraints, and edge case sections structured with XML tags
- **Version-controlled prompts:** Prompts stored separately from application code in `prompts.py`, with versioning (V1 → V2)
- **Prompt evaluation:** 8 test scenarios covering standard analysis, vague queries, prompt injection, insufficient data, conflicting data, multi-asset comparison, off-topic requests, and emotional/sentiment-loaded inputs

## Key Concepts

- **XML tags** (`<task>`, `<output_format>`, `<constraints>`, etc.) give Claude clear structural boundaries between instruction sections
- **Section ordering matters:** Role → Task → Data handling → Output format → Constraints → Edge cases — ordered by when Claude needs each during generation
- **Primacy-recency effect:** Most critical instructions go at the beginning and end of the system prompt
- **Negative constraints** ("NEVER provide buy/sell recommendations") are more reliable than vague positive ones ("be professional")

## Files

```
01-system-prompt/
├── README.md
├── main.py             # Test harness — sends diverse queries against the system prompt
├── prompts.py          # System prompt versions (V1, V2)
└── requirements.txt    # anthropic
```

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run evaluation
python3 main.py
```

## Iteration Notes

**V1 → V2 changes:**
- Added `<data_handling>` section between `<task>` and `<output_format>` — instructs Claude on what to do when it has data vs. when it doesn't
- Added format flexibility — conversational responses for non-standard queries, structured format only when enough data exists

## Connection to AW Analysis

This system prompt becomes the actual production prompt for the AW Analysis market interpreter agent. The output format defined here is what downstream code will parse.