# Framework Survey — Comparison Report

A comparison of the AW Analysis mini-agent task implemented five ways: one runnable hand-rolled Anthropic SDK baseline, and four annotated framework sketches (LangChain, LangGraph, Pydantic AI, LiteLLM).

**Important caveat:** the rubric scores below reflect the AW Analysis use case — Python, single provider, agent-heavy, Anthropic-specific features matter. Under different constraints (multi-provider, TypeScript frontend, heavy integration surface) some of these scores would flip.

## Rubric criteria

- **lines_of_code** — How much code does it take to express the task? Lower is better; score 5 = <40 LoC, 4 = 40-50, 3 = 50-65, 2 = 65-80, 1 = 80+.
- **dependencies** — How many transitive dependencies does the import footprint add? Lower is better; score 5 = <15 deps, 4 = 15-25, 3 = 25-45, 2 = 45-70, 1 = 70+.
- **debuggability** — When something goes wrong, how hard is it to find out why? Score 5 = you can read the entire control flow top to bottom in one file; 1 = you have to read library internals.
- **feature_access** — How easy is it to use Anthropic-specific features — prompt caching, extended thinking, cache-aware token counts, beta headers? Score 5 = trivial; 1 = effectively impossible.
- **abstraction_tax** — How much does the framework's abstraction get in the way when you need behaviour it didn't anticipate? Score 5 = no tax; 1 = heavy tax. (Note: internally stored inverted — low tax score in source maps to high display score.)
- **typing_quality** — How well-typed is the code end-to-end? Score 5 = every boundary is a typed object; 1 = dict soup with optional keys.

## Scores

| Implementation | lines_of_code | dependencies | debuggability | feature_access | abstraction_tax | typing_quality | Total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SDK Baseline (hand-rolled) | 1 | 5 | 5 | 5 | 5 | 3 | 24 |
| LangChain | 4 | 1 | 2 | 2 | 2 | 3 | 14 |
| LangGraph | 3 | 2 | 4 | 3 | 3 | 4 | 19 |
| Pydantic AI | 5 | 5 | 3 | 3 | 4 | 5 | 25 |
| LiteLLM | 5 | 3 | 4 | 3 | 4 | 3 | 22 |

## Ranked by total

1. **Pydantic AI** — total 25/30
2. **SDK Baseline (hand-rolled)** — total 24/30
3. **LiteLLM** — total 22/30
4. **LangGraph** — total 19/30
5. **LangChain** — total 14/30

## When to reach for each

**SDK Baseline (hand-rolled, 95 LoC)** — The right default for single-provider Python systems where you want every Anthropic feature accessible, you need to debug the loop, and you already understand the agent pattern. This is the AW Analysis choice.

**LangChain** (Layers 1, 3, 4 (provider abstraction + retrieval + agents)) — You need the long tail of integrations or you're prototyping fast and abstraction tax doesn't matter yet.

**LangGraph** (Layer 4 (agent orchestration, as an explicit state machine)) — Complex agent workflows with explicit state: checkpointing, human-in-the-loop, multi-agent supervisors, or resume-from-failure.

**Pydantic AI** (Layers 2, 4 (structured output + agent orchestration, type-first)) — Python-only greenfield where you want typed agent ergonomics without LangChain's surface area.

**LiteLLM** (Layer 1 only (provider abstraction across ~100 backends)) — You have a real multi-provider requirement — customer choice, geographic availability, or pricing leverage across backends.

## Notes on the scoring

The baseline does not sweep every criterion. It loses on `typing_quality` because the raw Anthropic SDK returns content blocks that aren't fully typed at every boundary — you end up using `getattr(block, 'type', None)` in the loop. Pydantic AI scores highest on typing because typing is its raison d'être. LangGraph scores well on debuggability because the state machine is explicit even though it's still inside a framework. LiteLLM scores well on debuggability because it owns so little of the stack that the control flow is yours.

The criterion that most favours the baseline is `feature_access`. Every framework on this list exposes Anthropic-specific features through escape hatches because the abstractions are provider-agnostic. For AW Analysis, where prompt caching and extended thinking are not optional, this criterion is weighted most heavily in practice even though the rubric gives every criterion equal weight.
