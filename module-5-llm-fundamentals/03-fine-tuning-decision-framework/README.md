# Exercise 5.3: Fine-Tuning Decision Framework

## What This Is

A decision framework document: given a use case, decide whether to prompt engineer, use RAG, or fine-tune. Covers 10 realistic use cases with clear recommendations and reasoning.

## Why It Matters

"When would you fine-tune vs. use RAG vs. prompt engineer?" is one of the most common Applied AI interview questions. A vague "it depends" answer doesn't land. This framework gives you a structured way to reason about the decision and specific examples to anchor your answers.

For interviews: instead of reciting general rules, you can say "I'd treat that as a knowledge problem, so RAG — specifically because [citing the relevant use case pattern]."

## How to Use It

**For interview preparation:**
- Read through once to internalise the decision tree
- Review the 10 use cases — each corresponds to a common interview question framing
- Memorise the "Interview One-Liners" section for verbal fluency

**As a real reference:**
- When you encounter a new AI use case in your work, identify which of the 10 patterns it matches
- Use the decision tree for novel cases that don't match a pattern directly
- Check yourself against "Common Mistakes" before starting a fine-tuning project

## Contents

**framework.md** (the main deliverable)
- The core rule (80/15/5 split)
- Decision tree
- Comparison table (prompt vs RAG vs LoRA vs full fine-tune)
- 10 realistic use cases with recommendations
- Common mistakes
- Cost-benefit snapshot
- Self-check before fine-tuning
- Connection to AW Analysis
- Interview one-liners

## Acceptance Criteria

- [x] Decision tree covering at least 8 realistic use cases (this has 10)
- [x] Each path has a clear recommendation with justification
- [x] Includes cost estimates, data requirements, and maintenance burden
- [x] Addresses hybrid approaches (RAG + fine-tuning)
- [x] Can be used as a quick reference in interviews
- [x] Includes text-based flowchart

## Key Takeaways

1. **Prompt engineering first, RAG second, fine-tuning last.** 80/15/5 split in practice.
2. **Knowledge problem → RAG. Behaviour problem → fine-tuning.** Diagnose before choosing.
3. **LoRA over full fine-tuning** by default — 90% of the benefit at 1% of the cost.
4. **Fine-tuning doesn't reliably inject knowledge.** Use RAG for facts.
5. **Cost optimisation is a valid reason to fine-tune** even when prompt engineering works — distill a large model's behaviour into a small one for high-volume tasks.

## Files

```
framework.md  — The decision framework (the main deliverable)
README.md     — This file
```

This is a documentation-only exercise. No code to run.