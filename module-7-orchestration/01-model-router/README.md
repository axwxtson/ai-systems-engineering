# Exercise 7.1 — Model Router for AW Analysis

An eval-driven model router for the AW Analysis market analyst task. Profiles
every candidate model on a per-class golden dataset, derives a routing policy
from the measurements, re-runs the eval with the policy in place, and reports
baseline-vs-routed quality and cost.

Every routing decision is grounded in measurement, not intuition.

---

## What this does

1. **Profile run.** For every query in the golden dataset and every candidate
   model (Haiku 4.5, Sonnet 4.6, Opus 4.6), runs the call, records token
   usage, latency, and cost, and grades the answer with a calibrated
   LLM-as-judge (Module 6 pattern).

2. **Per-class profile table.** Aggregates into mean quality, mean cost, p50
   and p95 latency, broken down per query class.

3. **Policy derivation.** Applies a deterministic decision rule: *for each
   class, pick the cheapest model whose mean quality meets the quality floor
   (4.0/5).* No manual tuning.

4. **Routed re-run.** Re-runs the same dataset through the derived router.
   Fresh calls, fresh judge scores — independent of the profile numbers.

5. **Comparison report.** Per-class baseline-vs-routed quality delta and total
   cost delta. Flags any per-class quality drop > 0.5 as a regression. Exit
   code 1 if any regressions are found.

6. **JSON dump.** All raw records, stats, policy, and comparison written to
   `results.json`.

---

## File structure

```
01-model-router/
├── README.md
├── main.py               # CLI orchestration with coloured output
├── router.py             # routing policy derivation + lookup
├── profiler.py           # runs each (model, query) pair
├── judge.py              # calibrated LLM-as-judge
├── golden_dataset.py     # v1: 15 cases × 3 classes (kept for reference)
├── golden_dataset_v2.py  # v2: 18 cases × 3 classes (harder, used by default)
├── pricing.py            # model price table + cost calculator
└── requirements.txt
```

---

## Setup

```bash
cd module-7-orchestration/01-model-router
pip3 install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Run

```bash
PYTHONPATH=$(pwd) python3 main.py
```

`PYTHONPATH=$(pwd)` is required on Python 3.14 for cross-module imports.

A full run takes ~20 minutes and costs ~$1.30 in API credits (54 profile calls
+ 18 routed calls + ~72 judge calls).

---

## Iteration history

This exercise went through two iterations — both the dataset and the policy
rule changed based on what the measurements revealed.

### Iteration 1: v1 dataset + relative-to-best rule

**Dataset:** 15 cases (5 easy, 5 medium, 5 hard). Single-fact definitions,
comparisons, and open-ended analytical questions.

**Policy rule (v1):** For each class, pick the cheapest model whose mean
quality is within ±0.3 of the best model's mean quality.

**Result:** Haiku scored 4.8+ on all three classes. The policy routed
everything to Haiku with 76% cost saving. The routing infrastructure worked
but the result was meaningless — the dataset was too easy to surface real
quality gaps between model tiers.

**Lesson:** Same finding as Module 4 (all retrieval strategies scored
near-perfect because the corpus topics were too distinct). Evaluation
difficulty matters as much as pipeline quality. If every model aces every
case, the eval can't differentiate and the routing decision is trivially
"use the cheapest."

### Iteration 2a: v2 dataset + relative-to-best rule

**Dataset (v2):** 18 cases (6 easy, 6 medium, 6 hard). Medium cases added
multi-constraint tasks: partial refusal + analysis splits, strict table
formatting requirements, explicit causal chain mechanisms, factual recall
with honesty traps. Hard cases added contradictory-signal synthesis,
steelman/counter/crux structures, and multi-frame reasoning under ambiguity.

**Result with v1 rule:** Haiku dropped to 3.50 on medium (the harder cases
worked). But the relative-to-best rule produced a counterintuitive policy:
easy → Haiku, medium → **Opus**, hard → Haiku. Medium went to Opus because
Opus scored 5.0, Sonnet scored 4.5, and 4.5 was outside the 0.3 tolerance —
so Sonnet was excluded even though 4.5 is a perfectly shippable score.
Meanwhile hard → Haiku because Haiku's 4.83 was within 0.17 of Sonnet's 5.0.

The result: cost *increased* 132% over baseline because a third of queries
routed to Opus.

**Lesson:** A relative-to-best rule chases the top score. It asks "which
model is closest to perfect?" when the real production question is "which
model is good enough?" When the best model happens to score high and the
second-best is merely good, the rule excludes the good option and forces you
to pay for the best.

### Iteration 2b: v2 dataset + quality floor rule (final)

**Policy rule (v2):** For each class, filter to models whose mean quality
meets an absolute floor (4.0/5), then pick the cheapest. If nothing meets
the floor, pick the highest-quality model regardless of cost.

**Profile results:**

| Class  | Haiku    | Sonnet   | Opus     |
|--------|----------|----------|----------|
| easy   | 5.00 ★   | 5.00 ★   | 5.00 ★   |
| medium | 3.83     | 4.83 ★   | 4.67     |
| hard   | 4.83     | 5.00 ★   | 5.00 ★   |

**Derived policy:** easy → Haiku, medium → Sonnet, hard → Haiku.

Haiku excluded from medium (3.83 < 4.0 floor). Sonnet chosen over Opus for
medium because both clear the floor and Sonnet is cheaper. Haiku chosen for
hard because 4.83 clears the floor and it's the cheapest option.

**Routed re-run results:**

| Class  | Baseline Q | Routed Q | ΔQ    | Cost saving |
|--------|------------|----------|-------|-------------|
| easy   | 5.00       | 4.83     | -0.17 | -71.7%      |
| medium | 4.83       | 4.67     | -0.17 | -3.8%       |
| hard   | 5.00       | 4.83     | -0.17 | -68.2%      |
| **Total** |         |          |       | **-47.2%**  |

No per-class regressions. 47.2% total cost saving. Policy shippable.

---

## Key findings

**1. More expensive doesn't mean better on every query.** Opus scored 4.67
on medium while Sonnet scored 4.83. `med_05` (volatility ranking with honesty
trap) scored 3/5 on Opus. Without per-case measurement you'd assume
Opus ≥ Sonnet always. You'd be wrong on this distribution.

**2. The policy rule matters as much as the measurements.** The same profile
data produced two very different policies depending on whether the rule was
relative-to-best or absolute-floor. Relative chased perfection and routed
medium to Opus (+132% cost). Absolute asked "good enough?" and routed medium
to Sonnet (-3.8% cost). The measurements were identical; the decision logic
changed the outcome entirely.

**3. Dataset difficulty is a design decision, not a detail.** v1 produced a
meaningless result (everything routes to Haiku) because the queries were too
easy. v2 added multi-constraint, format-strict, and honesty-trap cases that
surfaced real model-tier gaps. The infrastructure was correct in both runs —
the quality of the routing decision was entirely determined by whether the
eval was hard enough to differentiate.

**4. hard → Haiku is the decision to watch.** Haiku scored 4.83 on hard in
both the profile and the routed re-run, but `hard_05` dropped to 4/5 both
times. With n=6, one case is the difference between 4.83 and 5.00. In
production with higher volume, monitor whether hard-class Haiku quality
holds or drifts below the floor.

---

## How the policy is derived

The decision rule is in `router.py`:

```python
for each query class:
    above_floor = [model for model with mean_quality >= 4.0]
    if above_floor:
        chosen = cheapest model in above_floor
    else:
        chosen = highest-quality model (safety net)
```

The floor is the policy knob. At 4.0 it means "good — minor omissions but
substantively correct." Raising it to 4.5 would push hard → Sonnet (Haiku's
4.83 would still clear, but any further drop wouldn't). Lowering it to 3.5
would let Haiku handle medium (not recommended based on the profile).

---

## What this exercise is not

- **Not a cascade.** Routing-first: one classification, one call. Cascades
  come in 7.2.
- **Not a fallback chain.** No retry logic or error handling. Failures
  recorded and excluded. Fallback chains come in 7.2.
- **Not classifier-based.** Query classes are hand-labelled in the golden
  dataset. In production you'd wire a Haiku classifier on the front of
  `router.route()`.

The point of 7.1 is the measurement and policy derivation loop. 7.2 layers
fallback handling on top.

---

## Connection to Module 6

The judge reuses the calibrated rubric pattern from Module 6 Exercise 6.2.
The "trust per-case, not aggregate" lesson from 6.1 and 6.3 lands here as
the per-class table — quality is never reported as a single average. The
Module 4 lesson (evaluation difficulty matters) was re-learned when v1's
dataset failed to differentiate.

---

## Known limitations

- **Small n.** 6 cases per class is enough to demonstrate the loop but too
  small for statistical confidence. Production routing: 50-100 per class.
- **Single sample per (model, case).** A rigorous version would run each pair
  3-5 times and take the median.
- **Judge cost not in comparison.** The cost comparison covers system calls
  only, not eval overhead.
- **No TTFT.** Latency is wall-clock TTLT only. Interactive UX needs TTFT
  via streaming.