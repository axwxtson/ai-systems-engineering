# Exercise 6.1 — Eval Suite for Market Analysis

End-to-end evaluation harness for a market analysis agent. Runs unit evals,
trajectory evals, and LLM-as-judge graders over a golden dataset of 16 cases
and produces an aggregated report with per-metric and per-difficulty breakdowns.

## What This Demonstrates

The three-layer eval pattern from Module 6 Concept 2:

- **Unit evals** — deterministic assertions (refusal cases must be flagged as refused)
- **Trajectory evals** — did the agent call the expected tools in a sensible way?
- **End-to-end evals** — LLM-as-judge on faithfulness, relevance, refusal correctness

The golden dataset covers five difficulty tiers: `easy`, `multi_hop`, `edge`,
`out_of_scope`, and `boundary`. Out-of-scope and boundary cases test the system's
ability to refuse rather than hallucinate.

## Architecture

```
golden_dataset.py   →  16 curated eval cases + mock KB (4 documents, 3 mock prices)
analyser.py         →  System under test (simplified AW Analysis agent)
judges.py           →  LLM-as-judge graders (faithfulness, relevance, refusal)
eval_runner.py      →  Orchestrates evals, aggregates results
main.py             →  CLI with coloured output + regression reporting
```

## Running

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
cd module-6-eval-testing/01-eval-suite
PYTHONPATH=$(pwd) python3 main.py

# Verbose mode: prints each tool call as the agent runs
PYTHONPATH=$(pwd) python3 main.py --verbose
```

Expect ~90 seconds for a full run (16 cases × 1 system call + ~2-3 judge calls each).

## Output Format

Per-case progress line:
```
[ 1/16] OK    btc_crash_cause                U:PASS T:PASS F:5/5 R:5/5 X:  -  (5.2s)
```

- **U** = unit eval
- **T** = trajectory eval
- **F** = faithfulness (LLM-judge)
- **R** = relevance (LLM-judge)
- **X** = refusal correctness (only for refuse-cases)

Then an aggregate section: pass rates, mean LLM-judge scores, per-difficulty
breakdown, and a regressions list showing every case that failed any check.

## Exit Codes

- `0` — all cases passed, no regressions
- `1` — at least one regression or execution error

This makes the suite directly drop-in to CI.

## Run Results & Lessons Learned

First full run: 16 cases, 90.5s total, ~$0.20 estimated cost.

| Metric | Score |
|---|---|
| Unit pass rate | 75.0% |
| Trajectory pass rate | 93.8% |
| Mean faithfulness | 4.69/5 |
| Mean relevance | 4.81/5 |
| Mean refusal correctness | 5.00/5 |

Aggregate looked fine. Per-case review caught five real issues — and three of
them were eval-harness problems, not system problems. **This is the central
Module 6 lesson: aggregate scores hide real problems, and a failing eval is
ambiguous between system fault, spec fault, and eval fault.**

### Failure 1: Brittle deterministic refusal detection

`should_i_buy_btc` and `portfolio_allocation` produced textbook correct
refusals. The LLM-judge gave them 5/5 on refusal correctness. The unit eval
flagged them as FAIL.

Root cause: `_detect_refusal()` does substring matching against a fixed phrase
list. The list contains `"cannot give financial advice"` but the model
produced `"can't provide personalized financial advice"`. Substring miss.

**Lesson:** deterministic checks are cheap but fragile; LLM-judges are
expensive but semantically robust. The harness should treat disagreement
between unit and judge as its own signal, not just trust the unit check.

### Failure 2: Retrieval weakness surfaced as a system failure

`btc_vs_gold_hedge` ("How do Bitcoin and gold compare as inflation hedges?")
failed because the naive keyword KB search couldn't link "inflation hedges"
to the BTC crash document (which talks about Terra/Luna, FTX, Fed rates —
no exact word overlap with "inflation" or "hedges"). The agent only retrieved
the gold document and correctly refused to do a one-sided comparison.

**Lesson:** the eval is working correctly. It's surfacing the weakest link
in the stack — retrieval — which is exactly what it should do. Same finding
as Module 4: keyword matching collapses on semantic queries. In real AW
Analysis with vector search, this case passes.

### Failure 3: Spec disagreements

Two cases (`random_ticker`, `ambiguous_crash`) failed because the golden
dataset spec was wrong, not because the system misbehaved.

- `random_ticker`: spec expected the agent to try `get_price` after KB search
  failed. The agent reasonably stopped after KB returned nothing. Either
  behaviour is defensible.
- `ambiguous_crash`: spec expected an answer. The agent asked for
  clarification, which is *good* behaviour on ambiguous input. LLM-judges
  scored it 5/5 on faithfulness and relevance.

**Lesson:** golden datasets are living documents. When an eval fails, the
spec is one of the things that might be wrong.

### What didn't fail

- All six easy cases passed cleanly (100% across the board)
- All three judge graders worked correctly and agreed with each other
- Faithfulness 5/5 on every refusal case (no hallucinated facts even when
  refusing) — confirms the system prompt's grounding instructions hold

## Metric Thresholds

The "OVERALL: PASS" line uses these thresholds:

- Unit pass rate ≥ 90%
- Trajectory pass rate ≥ 80%
- Mean faithfulness ≥ 4.0 / 5
- Mean relevance ≥ 4.0 / 5

Tune these in `main.py > print_footer()` for your use case.

## Extending the Suite

- Add cases to `golden_dataset.py > GOLDEN_DATASET`
- Add judges to `judges.py` (mirror the pattern of `check_faithfulness`)
- Add evals to `eval_runner.py > run_single_case` (extend `CaseResult` first)

## Design Notes

**Why temperature=0 for the judge?** Judges need to be reproducible. Same
input should produce the same score across runs. Temperature 0 approximates
that (Module 5 finding: 0.3 was also effectively deterministic, 0 is safer).

**Why separate judges per dimension?** Composite "quality" scores are noisy.
A judge that grades faithfulness and relevance in one call tends to confound
them. Single-dimension judges with concrete rubrics give cleaner signal.

**Why a heuristic refusal detector at all?** It's cheap and runs
deterministically. The first run proved it's also fragile — see Failure 1
above. Exercise 6.2 will calibrate the LLM-judge against human judgment to
work out which signal to trust when the two disagree.

## Known Limitations

- Naive keyword KB search fails on semantic queries (Failure 2 above). A real
  system would use vector search from Module 4.
- Refusal detection uses substring matching against a fixed phrase list and
  misses paraphrases. Cross-checking against the LLM-judge is the workaround
  until 6.2.
- Faithfulness grader returns a neutral score (3) when no context is
  retrieved. This is a deliberate choice — refusals shouldn't be penalised
  for having no context to be unfaithful to.
- 16 cases is too small for statistical significance. Per-case inspection is
  the only honest way to read the results at this scale.