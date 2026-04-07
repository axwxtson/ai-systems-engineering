# Exercise 6.2 — LLM-as-Judge Calibration

Calibrate an LLM judge against your own grading on a 30-pair reference set,
measure agreement, surface disagreements, and probe the judge for position
and length bias. The point is to find out *whether you can trust your judge*
before you trust your evals.

## What This Demonstrates

The Module 6 Concept 4 calibration loop made concrete:

1. Grade a reference set yourself (the ground truth)
2. Run the judge on the same set
3. Measure agreement (exact, ±1, direction)
4. Inspect disagreements — fix the rubric, not the grades
5. Re-run with the new rubric, compare improvement
6. Repeat until ±1 agreement ≥ 80%

Plus two bias probes: position bias (does pairwise ordering affect the
winner?) and length bias (does the same content score higher when verbose?).

## Architecture

```
reference_set.py        →  30 (query, answer) pairs across 3 dimensions, with
                           teaching notes revealed after grading
grade_reference_set.py  →  Interactive CLI for human grading (incremental save)
judge.py                →  Versioned rubrics + judge invocation
agreement.py            →  Exact / ±1 / direction / confusion / bias metrics
bias_tests.py           →  Position bias (pairwise) + length bias (short vs long)
main.py                 →  Calibration analysis CLI
```

## Workflow

### Step 1: grade the reference set yourself

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
cd module-6-eval-testing/02-llm-judge-calibration
PYTHONPATH=$(pwd) python3 grade_reference_set.py
```

You'll be walked through 30 pairs one at a time. For each pair:

- The query, the context (faithfulness only), and the answer are shown
- The same rubric the judge will use is displayed beneath
- You score 1-5
- The teaching note is revealed showing the engineered target score and the
  reasoning, so you can sanity-check yourself before moving on

Grades save incrementally to `human_grades.json` — ctrl+C is safe, re-running
picks up where you left off.

Estimated time: ~25-30 minutes the first time.

To regrade a single pair (e.g. you misread the question):
```bash
PYTHONPATH=$(pwd) python3 grade_reference_set.py --regrade faith_03
```

### Step 2: run the judge and view the calibration report

```bash
PYTHONPATH=$(pwd) python3 main.py
```

This loads your grades, runs the v1 judge over all 30 pairs, caches judge
grades to `judge_grades.json`, and prints the agreement report plus the bias
test results. ~$0.25 and ~2 minutes for a full run.

Useful flags:
- `--skip-bias` — skip the position/length tests for faster reruns
- `--skip-judge` — use cached judge grades, useful when iterating on the report

### Step 3: iterate the rubric (only if needed)

`judge.py` has slots for `v1` (current) and `v2`. Inspect the top
disagreements from the report — they tell you what v1 fails to capture. Edit
the v2 rubric, then:

```bash
PYTHONPATH=$(pwd) python3 main.py --rubric-version v2
```

## Calibration Results — First Run

| Metric | Score |
|---|---|
| Exact agreement | 66.7% |
| Within ±1 agreement | **93.3%** |
| Direction agreement | 83.3% |
| Mean signed bias | +0.07 (essentially neutral) |

**v1 passed calibration on first run.** ±1 agreement well above the 80%
target, near-zero signed bias, no systematic drift in either direction. No
v2 rubric was needed.

### Per-dimension breakdown

| Dimension | N | Exact | ±1 | Direction | Hμ | Jμ |
|---|---|---|---|---|---|---|
| Faithfulness | 10 | 60% | 100% | 80% | 3.40 | 3.60 |
| Relevance | 10 | 70% | 80% | 70% | 3.70 | 3.60 |
| Refusal | 10 | 70% | 100% | 100% | 3.10 | 3.20 |

Refusal is the strongest dimension — 100% within ±1 *and* 100% direction
agreement. The judge correctly handled the hedged-advice trap (`ref_06`,
`ref_10`) without falling for the disclaimer fig leaf, scoring both as 2/5.
This was the single result I was most uncertain about going in.

Faithfulness also hit 100% within ±1, with 60% exact agreement.

Relevance is the weakest dimension at 80% within ±1. Two of the ten pairs
had a 2-point gap, both worth understanding.

### The two real disagreements

Only two cases broke the ±1 threshold. Both are in relevance, both are
principled rather than noise.

**`rel_09` — NVIDIA Q3 2024** (human: 5, judge: 3)

The system gave directional commentary then refused on the specifics. I
graded it as a clean refusal (5), but on review the judge was right: this
is a partial answer with a hedge, not a refusal. The user asked "how did
NVIDIA perform" and got "well, but I can't tell you the numbers." That's
a 3, not a 5. The judge caught my own grading inconsistency.

**Lesson:** the judge as a second pair of eyes catches *your* errors, not
just the system's. Cross-checking is bidirectional.

**`rel_10` — Ethereum Merge "in one sentence"** (human: 2, judge: 4)

The system gave four sentences when asked for one. I scored it harshly
(2) because format compliance is part of the user's request. The judge
gave it 4 because the content was accurate and on-topic.

Neither view is objectively right. For AW Analysis specifically, the
strict view is correct — users specifying format are usually piping the
output somewhere downstream, and ignoring format defeats the purpose. For
a general-purpose chat assistant, the lenient view is more defensible.

A v2 rubric could tighten this with: *"If the query specifies a format
constraint, violations are relevance failures. An accurate answer in the
wrong format scores no higher than 3."* Not worth shipping over a single
case, but noted for future iteration.

### Where the judge sided with me over the teaching-note targets

Two faithfulness cases (`faith_09`, `faith_10`) where the judge scored
4 and 3 — matching my grades, not the teaching-note targets of 3 and 2.
This is the calibration system working correctly: the judge is calibrated
to the human grader, not to the exercise authors. Both interpretations
are defensible; the judge picked the more lenient one because that's
what I picked.

## Bias Findings

The bias tests surfaced two findings worth more attention than the
calibration results themselves.

### Position bias: 0% consistency — judge has near-total position sensitivity

Three pairwise comparisons run in both orderings. **All three flipped.**
The judge picked a different winner depending on which answer appeared
first.

This means the judge as configured is **unusable for pairwise
comparison evals** without order randomisation. If you ever ask "is
prompt v3 better than prompt v2?" with a pairwise judge, you'd be
measuring position, not quality.

**Mitigation:** run every pairwise comparison in both orderings. Only
count wins where both orderings agree, or average the scores. This is
well-known in the literature but easy to forget — and you'd never know
you needed it without running this test.

**Impact for AW Analysis:** matters most for A/B prompt testing. Any
pairwise eval comparing two prompt versions or two retrieval strategies
needs order randomisation built in.

### Length bias: -1.00 — judge prefers SHORTER answers

Two test cases where the same factual content was graded in a short
version and a long version. Both long versions scored 1 point lower
than their short counterparts, with no fabrications added.

This is the **opposite** of the bias the literature usually warns
about. Most papers report judges favouring longer answers; this judge
penalises them.

**Likely cause:** the v1 faithfulness rubric explicitly says *"A long
answer with one fabricated figure scores 2."* That phrasing primes
the judge to associate length with risk, even when the long version
has no new fabrications.

**Whether this is good or bad depends on use case.** For faithfulness
specifically, mild wariness about elaboration is defensible — longer
answers do have more surface area for fabrication in the general case.
For AW Analysis (where concise outputs are usually preferred) this
bias actually helps. For summarisation evals where verbosity is
expected, it would hurt.

## Calibration Targets

| Metric | Acceptable | Good | Production-ready | This run |
|---|---|---|---|---|
| Within ±1 agreement | ≥ 70% | ≥ 80% | ≥ 85% | **93.3%** ✓ |
| Exact agreement | ≥ 50% | ≥ 65% | ≥ 75% | 66.7% |
| Direction agreement | ≥ 80% | ≥ 90% | ≥ 95% | 83.3% |
| Signed bias \|·\| | < 0.6 | < 0.4 | < 0.25 | **0.07** ✓ |
| Position consistency | ≥ 70% | ≥ 85% | ≥ 95% | **0%** ✗ |
| Length bias \|gap\| | < 0.7 | < 0.4 | < 0.2 | 1.00 ✗ |

The agreement metrics are excellent. The bias metrics are below target,
but they're informative failures — they tell you exactly when and how
not to use this judge.

## Design Notes

**Why 30 pairs and not 100?** Rubric calibration has diminishing returns.
After the first 20-30 pairs, you've seen most of the failure patterns. Going
to 100 mostly inflates the numbers without changing the rubric you'd write.
Production calibration sets typically grow over time as new failures get
added, not by trying to hit a target size from day one.

**Why guided grading instead of blind?** Speed and education. Blind grading
is methodologically purer but slower and offers no feedback loop on your
own grading consistency. The teaching notes show the engineered target after
you score, so disagreements between you and the target become a useful
self-check — and the disagreements that survive are calibration data about
your own grading style.

**Why both pairwise and direct grading for bias?** Position bias is only
meaningful in pairwise comparisons (it doesn't apply to single-answer
grading). Length bias is only meaningful in single-answer grading. Different
test shapes for different bias types.

**Why is v2 a placeholder?** Because the right v2 depends on what your v1
run surfaces. In this run, v1 passed — no v2 was needed. The slot is left
in place for the next time the rubric is updated.

## Known Limitations

- 30 pairs is too small for statistical confidence intervals. Treat
  differences <5% as noise.
- The reference set is engineered around financial-markets queries to match
  AW Analysis. Generalising to a different domain requires writing new pairs.
- The judge and the system being graded are both Claude Sonnet, so
  self-preference bias isn't tested here. Cross-model judging would need a
  second provider.
- Position bias mitigation is documented but not implemented. The bias test
  identifies the problem; using the judge for pairwise comparisons in
  production would require adding the both-orderings wrapper around any
  comparison call.