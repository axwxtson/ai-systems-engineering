# Exercise 2.2: Prompt Chain for Research Reports

## What This Is

A 3-stage prompt chain that takes raw market data and produces a structured research brief, compared against a single-prompt baseline doing the same task. Tests whether decomposing a task into Extract → Analyse → Format stages improves output quality.

## What It Demonstrates

- **Prompt chaining:** Breaking a complex task into sequential API calls with stage-specific system prompts
- **Validation gates:** Programmatic checks between stages that verify JSON structure, required fields, and data completeness before passing output forward
- **Chain vs single-prompt trade-offs:** Empirical comparison showing when chains add value and when they introduce unnecessary context loss
- **Stage-specific prompt design:** Each stage has a focused system prompt optimised for one job (extraction, analysis, or formatting)

## The Three Stages

1. **Extract** — Takes raw, messy market text and outputs structured JSON with data points, entities, and date references
2. **Analyse** — Takes extracted JSON and produces trend assessment, key insights, sentiment rating, and risk factors
3. **Format** — Takes analysis JSON and produces a human-readable research brief

Each stage has a validation gate that checks the output before passing it to the next stage. If a gate fails, the chain aborts early rather than propagating bad data.

## Key Finding

The single prompt produced equal or better output across all three test cases. Chains lost context between stages — nuance and implicit signals from the raw data were stripped during extraction, leading to less holistic analysis. However, the chain architecture becomes essential at production scale when inputs exceed one prompt's capacity, when auditability matters, or when different stages need different model configurations.

## Files

```
03-prompt-chain/
├── README.md
├── main.py             # Chain runner + single-prompt baseline comparison
├── prompts.py          # Stage-specific system prompts (extract, analyse, format) + baseline
├── results.md          # Analysis of chain vs single-prompt quality
└── requirements.txt    # anthropic
```

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run comparison (18 API calls — 3 tests × 3 chain stages + 3 single-prompt)
python3 main.py
```

## Connection to AW Analysis

The chain architecture maps directly to the AW Analysis pipeline: Stage 1 mirrors tool-result processing, Stage 2 mirrors the core analysis agent, Stage 3 mirrors report generation. At production scale with multiple data sources (price feeds, news APIs, historical data), the chain's decomposition and validation gates become necessary even though they weren't advantageous at this test scale.cd 