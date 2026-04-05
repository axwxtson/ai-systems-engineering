# Fine-Tuning Decision Framework

**Purpose:** Given a use case, decide whether to prompt engineer, use RAG, or fine-tune.

**Audience:** Self-reference and interview preparation.

---

## The Core Rule

> **Prompt engineering first, RAG second, fine-tuning last.**
>
> Roughly 80% of use cases are solved by prompt engineering. Another 15% need RAG. Only the remaining 5% justify fine-tuning.

This order reflects cost, iteration speed, and maintenance burden. Always try cheaper, faster solutions first.

---

## The Fundamental Distinction

**Knowledge problem?** → RAG
**Behaviour problem?** → Fine-tuning
**Either?** → Try prompting first

| | Knowledge Problem | Behaviour Problem |
|---|---|---|
| **What** | Model doesn't know facts it should | Model doesn't respond the way you want |
| **Example** | "What's in our internal Q3 report?" | "Always respond in a legal memo format" |
| **Solution** | RAG — inject facts at query time | Fine-tuning — change model weights |
| **Why prompt engineering might fail** | Can't fit all relevant docs in context | System prompt can't enforce consistent style across millions of outputs |

---

## The Decision Tree

```
START: You have a task where base model output isn't good enough
  │
  ├─ Q1: Have you tried prompt engineering?
  │    └─ NO → START WITH PROMPT ENGINEERING
  │          (system prompt, few-shot examples, structured output, CoT)
  │
  ├─ Q2: Does the task require knowledge not in the model's training data?
  │    │  (private docs, recent events, domain-specific facts,
  │    │   user-specific data, frequently updated information)
  │    └─ YES → USE RAG
  │          Cheap to update, provides citations, no retraining
  │
  ├─ Q3: Is the problem about HOW the model responds, not WHAT it knows?
  │    │  (consistent format, specific tone, domain style,
  │    │   reduced verbosity, specialised output structure)
  │    │
  │    ├─ Can prompt engineering achieve it?
  │    │   └─ YES → PROMPT ENGINEERING
  │    │
  │    ├─ Do you have 500+ high-quality examples?
  │    │   └─ NO → Collect examples OR stick with prompt engineering
  │    │
  │    └─ YES to both → FINE-TUNE (LoRA first, full fine-tune only if LoRA underperforms)
  │
  └─ Q4: Cost optimisation — can a smaller model match a larger model on your specific task?
       │
       └─ YES → FINE-TUNE a small model on large model outputs (distillation pattern)
                Valid even if prompt engineering works — purely a cost/latency optimisation
```

---

## Comparison at a Glance

| Dimension | Prompt Engineering | RAG | Fine-Tuning (LoRA) | Fine-Tuning (Full) |
|---|---|---|---|---|
| **What it changes** | Inputs | Inputs | ~1% of weights | All weights |
| **Best for** | Instructions, format, reasoning | Knowledge injection | Style, format, task specialisation | Deep task specialisation |
| **Minimum data** | 0-10 examples | 10+ documents | 500-1,000 examples | 10,000+ examples |
| **Ideal data** | 3-5 few-shot examples | Entire knowledge base | 5,000+ examples | 100,000+ examples |
| **Cost to build** | ~$0 | $100-10k (infra + embedding) | $100-$1k (compute) | $10k-$100k+ (compute) |
| **Cost to update** | Instant, free | Re-embed changed docs | Retrain ($100+) | Retrain ($10k+) |
| **Iteration speed** | Seconds | Minutes (re-embed) | Hours (retrain) | Days (retrain) |
| **Inference cost** | Same as base model | Same + embedding query | Same as base model | Same as base model |
| **Citations** | No | Yes (source tracking) | No | No |
| **Catastrophic forgetting risk** | None | None | Low | High |
| **Maintenance burden** | Low | Medium (pipeline) | Medium (eval, retraining) | High (eval, MLOps) |

---

## Realistic Use Cases

### Use Case 1: "I need the agent to know our company's internal SOPs"

**Classification:** Knowledge problem
**Recommendation:** **RAG**

**Reasoning:** This is private data the model was never trained on, it's a bounded set of documents, and SOPs change over time. RAG handles all three: you embed the SOPs, retrieve the relevant ones per query, and inject citations. Updating an SOP means re-embedding one document.

**Why not fine-tuning:** You'd need to retrain every time an SOP changes, no citations, and the model can still hallucinate SOPs with false confidence.

**Why not prompt engineering alone:** If you have 200 SOPs, you can't fit them all in context. RAG retrieves the 3-5 relevant ones per query.

---

### Use Case 2: "I need the agent to always respond in the format of a legal memo"

**Classification:** Behaviour problem
**Recommendation:** **Prompt engineering** → Fine-tuning if prompting fails

**Reasoning:** Start with a detailed system prompt and 2-3 few-shot examples showing the exact format. For 95% of cases this works. If you need to process thousands of memos per day and the model occasionally drifts from the format, fine-tune on 500+ memo examples — LoRA is sufficient.

**Why not RAG:** No knowledge problem here; the model has all the legal knowledge it needs. This is purely about output format.

**Data requirements if fine-tuning:** 500-1,000 (input, correctly-formatted-output) pairs. Quality over quantity.

---

### Use Case 3: "I need the agent to reference recent market news"

**Classification:** Knowledge problem (with recency)
**Recommendation:** **RAG** (with fresh ingestion pipeline)

**Reasoning:** News is by definition post-training-cutoff. RAG lets you ingest new articles continuously and retrieve them at query time. The knowledge base grows without retraining the model.

**Why not fine-tuning:** Would become stale within hours. Even daily retraining is infeasible and costs thousands.

**Architecture note:** This is exactly the AW Analysis pattern — your ingestion pipeline runs continuously, the agent queries the vector store, and Claude generates grounded answers with citations.

---

### Use Case 4: "I need the agent to write in our company's specific tone across 10,000 articles a month"

**Classification:** Behaviour problem (at scale)
**Recommendation:** **Fine-tuning (LoRA)** after prompt engineering proves insufficient

**Reasoning:** At 10,000 articles a month, minor tone drifts compound into brand inconsistency. A detailed system prompt helps, but for persistent style across thousands of generations, fine-tuning is more reliable. Use your best existing articles as training data.

**Data requirements:** 1,000-5,000 examples of articles in the target tone.

**Why LoRA over full fine-tuning:** LoRA captures stylistic adaptation in ~1% of parameters, preserves general capabilities, costs ~100x less. Full fine-tuning only if LoRA quality is insufficient after tuning.

**Quick sanity check:** Before committing, run a 50-article A/B test between your best prompt and the base model. If the gap is small, prompt engineering is likely fine.

---

### Use Case 5: "I need a cheaper model that matches Claude Sonnet's performance on my classification task"

**Classification:** Cost optimisation
**Recommendation:** **Fine-tune a smaller model** (distillation pattern)

**Reasoning:** Use Sonnet to generate labels on 10,000+ examples. Fine-tune Haiku (or an open-source smaller model) on those labels. The small model learns your specific task from the larger model's outputs — this is distillation at the application level.

**Data requirements:** 5,000-50,000 labelled examples (generated by the larger model, then human-spot-checked).

**When this is worth it:** If you're running >100k inferences/month, the cost savings from Haiku vs Sonnet (18x cheaper on input tokens) pay for the fine-tuning effort quickly.

**When it's not worth it:** Under 10k inferences/month. The engineering time exceeds the savings.

---

### Use Case 6: "I need the agent to extract structured data from unstructured emails"

**Classification:** Behaviour problem (format compliance)
**Recommendation:** **Prompt engineering** — specifically, tool use as a forcing function

**Reasoning:** Define a tool with the exact JSON schema you need. Use `tool_choice` to force the model to use it. You get guaranteed structured output without fine-tuning. Temperature 0 is essential.

**Why not fine-tuning:** Unnecessary complexity. The tool-use pattern solves structured extraction reliably on base models.

**Reference:** Module 1's structured output section — this is the canonical pattern.

---

### Use Case 7: "I need the agent to speak a low-resource language the base model barely handles"

**Classification:** Either — depends on what's missing
**Recommendation:** **Diagnose first, then choose**

**If the problem is "model knows the language but output is stilted":** Fine-tune on quality examples in that language (LoRA, 2,000-10,000 examples).

**If the problem is "model doesn't know domain terms in that language":** RAG with a glossary and example documents in the target language.

**If the problem is "model produces grammatical errors":** This is a base-model capability gap. Fine-tuning can help on narrow tasks, but fundamental fluency requires a different model or significant training data (10,000+ examples).

**Key test:** Run 20 examples, manually classify the failures. If they're knowledge gaps → RAG. If they're stylistic/grammatical → fine-tuning.

---

### Use Case 8: "I need the agent to write code in our internal proprietary framework"

**Classification:** Hybrid — both knowledge AND behaviour
**Recommendation:** **RAG first, then fine-tuning if quality is insufficient**

**Reasoning:** The framework's API documentation, examples, and patterns are knowledge the model doesn't have (RAG territory). But if you want the model to instinctively use framework idioms — naming conventions, patterns, error handling style — that's behavioural (fine-tuning territory).

**Phase 1 (RAG):** Ingest all framework docs and example code. Retrieve relevant patterns per query. This solves 70% of the problem.

**Phase 2 (fine-tuning, if needed):** Collect 1,000+ examples of well-written code in the framework. Fine-tune to internalise patterns. Use LoRA.

**Why this order:** RAG is cheap, instant, and provides attribution. Only escalate to fine-tuning if you can measurably demonstrate that RAG isn't enough.

---

### Use Case 9: "I need to filter offensive content in user posts"

**Classification:** Behaviour problem (narrow, specific)
**Recommendation:** **Fine-tune a small model** (if volume justifies it)

**Reasoning:** Content moderation is high-volume, latency-sensitive, and well-defined. Fine-tune a small open-source model (or Haiku) on labelled examples. Small model + fine-tuning = fast, cheap, reliable for this narrow task.

**Data requirements:** 10,000+ labelled examples covering edge cases.

**Why not prompt engineering:** Works, but 10x-100x more expensive per inference at scale.

**Why not a frontier model:** Overkill for a binary classification task. Pay for capability you don't need.

---

### Use Case 10: "I need the agent to follow multi-step reasoning for financial compliance checks"

**Classification:** Behaviour problem (reasoning quality)
**Recommendation:** **Prompt engineering with chain-of-thought + extended thinking**

**Reasoning:** For reasoning quality, a detailed system prompt with explicit steps, few-shot examples of good reasoning, and extended thinking (Module 1) outperforms most fine-tuning approaches. Fine-tuning doesn't reliably improve reasoning — it mostly improves style and format.

**Why not fine-tuning:** Fine-tuning on reasoning examples sometimes helps, but you typically need thousands of examples and results are inconsistent. Prompt engineering with CoT is higher-ROI.

**Reference:** Module 2's chain-of-thought section.

---

## Common Mistakes

**Mistake 1: Fine-tuning to inject knowledge.**
Fine-tuning changes weights but doesn't reliably teach new facts. The model can hallucinate the fine-tuned "knowledge" with confidence. Use RAG.

**Mistake 2: Prompt engineering when you need RAG.**
If you're stuffing 50 documents into every prompt to answer different questions, you need RAG. You're burning context and paying for irrelevant tokens per query.

**Mistake 3: Fine-tuning without an eval suite.**
You can't tell if fine-tuning helped. Module 6 builds evals — do that *before* attempting fine-tuning so you can measure change.

**Mistake 4: Assuming fine-tuning is a one-time cost.**
Every model version change (Claude 4.6 → Claude 5) means retraining. Your knowledge base changes mean re-curating training data. Ongoing maintenance is real.

**Mistake 5: Skipping LoRA and going to full fine-tuning.**
LoRA captures 90%+ of the benefit at 1% of the cost. Always try LoRA first.

**Mistake 6: Fine-tuning a frontier model when a smaller model would do.**
If your task is narrow (classification, extraction, formatted output), a fine-tuned small model usually outperforms a prompted large model on cost-quality-latency combined.

---

## Cost-Benefit Snapshot

For a hypothetical 100k-inference/month use case:

| Approach | Build Cost | Monthly Inference | Update Cost | Total Year 1 |
|---|---|---|---|---|
| Prompt engineering (Sonnet) | $0 | ~$3,000/month | $0 | **~$36,000** |
| RAG (Sonnet + embedding) | ~$500 | ~$3,100/month | ~$50/update | **~$37,700** |
| LoRA fine-tune (Haiku) | ~$500 | ~$150/month | ~$300/retrain (quarterly) | **~$3,200** |
| Full fine-tune (Haiku) | ~$15,000 | ~$150/month | ~$10,000/retrain (quarterly) | **~$57,000** |

**Read:** For high-volume tasks where quality requirements are well-defined, LoRA fine-tuning of a smaller model is often dramatically cheaper. For low-volume tasks, stick with prompt engineering.

---

## Quick Self-Check Before Fine-Tuning

Answer honestly before starting a fine-tuning project:

1. Have you exhausted prompt engineering? (System prompt, few-shot, CoT, tool use, extended thinking?)
2. Have you built an eval suite to measure improvements?
3. Do you have 500+ high-quality training examples?
4. Do you have a way to regenerate training data when you update the model?
5. Do you have infrastructure for retraining when the base model version changes?
6. Is the quality gap between your current approach and "good enough" actually material?

If you answer "no" to any of 1-5, you're not ready to fine-tune.
If you answer "no" to 6, you don't need to fine-tune.

---

## Connection to AW Analysis

AW Analysis's current architecture is **prompt engineering + RAG**. This is correct because:

- Market data and historical analyses are knowledge problems → RAG handles them
- The knowledge base changes constantly (new reports, updated prices) → RAG handles this
- Citation is essential → RAG provides it
- Analytical style is achievable via system prompts → prompt engineering handles it
- You don't have thousands of labelled examples → fine-tuning isn't viable

**When fine-tuning might become relevant for AW Analysis:**

- **Cost optimisation (Module 7):** Once AW Analysis has high volume, fine-tune Haiku on Sonnet outputs to serve routine queries. Use case pattern #5.
- **Report generation style:** If you produce hundreds of market reports per week and need consistent analytical voice, fine-tune on your best reports. Use case pattern #4.
- **Specialised analysis types:** If you develop a proprietary analytical framework (your own technical indicator suite), fine-tuning could internalise those patterns. Use case pattern #8.

None of these are immediate. Prompt engineering + RAG is the right architecture now.

---

## Interview One-Liners

**"When would you fine-tune vs. use RAG?"**

"RAG for knowledge, fine-tuning for behaviour. If the model needs information it wasn't trained on, or if that information changes, RAG — it's cheap to update, provides citations, and doesn't risk catastrophic forgetting. Fine-tuning for consistent style, format, or specialised task performance that prompt engineering can't achieve. Prompt engineering first always — roughly 80% of cases are solved there, 15% need RAG, only 5% justify fine-tuning."

**"Why not fine-tune everything?"**

"Fine-tuning is expensive to build, slow to update, risks catastrophic forgetting, and doesn't reliably inject knowledge — the model can hallucinate fine-tuned 'facts' with confidence. It's the right tool for persistent behaviour changes at scale, but prompt engineering handles most needs at zero cost and instant iteration speed."

**"What is LoRA and when would you use it?"**

"Low-Rank Adaptation — instead of updating all model weights during fine-tuning, you inject small trainable matrices that capture the task-specific adaptation in about 1% of the original parameter count. It achieves 90%+ of full fine-tuning quality at roughly 1% of the compute cost, reduces catastrophic forgetting because most weights stay frozen, and can fine-tune large models on a single GPU. It's the default choice over full fine-tuning unless there's a specific reason to update all weights."

**"You have a task — how do you decide the approach?"**

"First ask whether it's a knowledge problem or a behaviour problem. Knowledge problems — private docs, recent events, domain facts — go to RAG. Behaviour problems — format, tone, task specialisation — try prompt engineering first, then fine-tuning if prompting can't achieve the consistency you need at scale. For cost optimisation specifically, fine-tuning a smaller model on a larger model's outputs is a valid pattern even when prompt engineering works, because the inference savings compound."

---

*Last updated: March 30, 2026*