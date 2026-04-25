# Exercise 8.1 — Framework Survey: The Same Agent, Five Ways

**Module 8 · Tool Ecosystem & Workflows**

A reading-and-comparison exercise. Take one well-specified task — a simple
AW Analysis-style agent with two tools (`get_price`, `search_knowledge_base`)
— and produce five implementations of it: one hand-rolled Anthropic SDK
baseline that actually runs, and four annotated sketches in LangChain,
LangGraph, Pydantic AI, and LiteLLM. Score each against a fixed rubric.
Produce a comparison report suitable for showing in an interview.

The point is not to become fluent in every framework. The point is to be
able to read framework code, place each tool on the layer map, and
articulate a defensible rule for when you'd reach for each.

## What this exercise builds

- **A runnable SDK baseline** (`baseline_agent.py`) using the agent loop
  pattern from Module 3 — explicit, single-file, no framework layers.
- **Four annotated framework sketches** (`sketches.py`) — stored as Python
  strings, not separate modules. Each sketch is rendered to the terminal
  with paragraph-level commentary on what the framework owns and where
  the trade-offs live. **The sketches are pseudocode for reading, not
  running.** You do NOT need to `pip install langchain` to complete the
  exercise.
- **A six-criterion rubric** (`rubric.py`) — lines of code, dependencies,
  debuggability, feature access for Anthropic-specific features, abstraction
  tax, typing quality.
- **A comparison report** (`comparison.py`) — per-criterion table plus a
  "when to reach for it" paragraph per implementation, printed to stdout
  and written to `comparison_report.md`.
- **Five test queries** (`tasks.py`) — easy, medium, and hard cases
  covering single-tool, multi-tool, refusal, and multi-hop patterns.

## File structure

```
module-8-tool-ecosystem/01-framework-survey/
├── README.md                  # this file
├── main.py                    # CLI orchestration with coloured output
├── baseline_agent.py          # runnable hand-rolled SDK agent
├── sketches.py                # annotated framework sketches (strings)
├── rubric.py                  # 6-criterion scoring rubric
├── comparison.py              # comparison table + markdown report builder
├── tasks.py                   # shared task spec + 5 test queries + mock tools
├── requirements.txt
└── comparison_report.md       # generated on first successful run
```

## Setup

```bash
# from the 01-framework-survey/ folder
pip3 install -r requirements.txt

# API key (already set from Module 1, check with: echo $ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY="sk-ant-..."
```

Note: Python 3.14 requires the `PYTHONPATH=$(pwd)` prefix for cross-module
relative imports. This is the same pattern used in Modules 5–7.

## Running it

**Full run** — baseline agent + all sketches + comparison report:

```bash
PYTHONPATH=$(pwd) python3 main.py
```

**Sketches only** — no API calls, useful for offline reading:

```bash
PYTHONPATH=$(pwd) python3 main.py --only-sketches
```

**Skip baseline** — score and compare without live API calls:

```bash
PYTHONPATH=$(pwd) python3 main.py --no-baseline
```

## Actual run results

Baseline LoC (non-blank, non-comment): 95

### Baseline agent — 5/5 queries passed

| Query | Difficulty | Steps | Tool calls | Tokens (in/out) | Result |
|---|---|---|---|---|---|
| `q1_price_only` | easy | 2 | 1 (`get_price`) | 1436/94 | Returned BTC price with 24h change |
| `q2_kb_only` | easy | 2 | 1 (`search_knowledge_base`) | 1461/181 | Summarised ETH ETF approval |
| `q3_multi_tool` | medium | 2 | 2 (`get_price` + `search_knowledge_base`) | 1619/244 | Combined price and ETF context |
| `q4_refusal` | medium | 1 | 0 | 670/97 | Correctly refused investment advice |
| `q5_multi_hop` | hard | 2 | 3 (2× `get_price` + `search_knowledge_base`) | 1744/327 | Synthesised AAPL/TSLA comparison with earnings |

Key observations from the baseline run:

- **Parallel tool calling works.** q3 and q5 both issued multiple tool calls
  in a single step (step count = 2 despite 2–3 tool calls), confirming Sonnet
  batches tool calls when it can. This is an Anthropic-specific feature that
  framework abstractions sometimes obscure.
- **Refusal handled cleanly.** q4 produced zero tool calls and a clean refusal
  — the system prompt's "analysis not advisory" rule triggered correctly
  without needing an explicit refusal tool.
- **Token efficiency is visible.** The simplest query (q1) used 1436 input
  tokens; the hardest (q5) used 1744. The difference is modest because the
  system prompt and tool schemas dominate the input — the user query itself
  is a small fraction.

### Comparison table (scored for AW Analysis use case)

| Implementation | lines | deps | debug | feature | abstr | typing | Total |
|---|---|---|---|---|---|---|---|
| SDK Baseline (hand-rolled) | 1 | 5 | 5 | 5 | 5 | 3 | **24** |
| LangChain | 4 | 1 | 2 | 2 | 2 | 3 | **14** |
| LangGraph | 3 | 2 | 4 | 3 | 3 | 4 | **19** |
| Pydantic AI | 5 | 5 | 3 | 3 | 4 | 5 | **25** |
| LiteLLM | 5 | 3 | 4 | 3 | 4 | 3 | **22** |

**Ranked:** Pydantic AI (25) → SDK Baseline (24) → LiteLLM (22) → LangGraph (19) → LangChain (14)

Pydantic AI edges the baseline by 1 point — winning on `lines_of_code` and
`typing_quality`, losing on `debuggability` and `feature_access`. The baseline
wins on the dimensions that matter when you're the sole developer and need
full visibility into the agent loop. Pydantic AI wins on the dimensions that
matter when you're onboarding others or enforcing contracts at boundaries.

LangChain's score (14/30) reflects the AW Analysis context — single provider,
two tools, no integration breadth needed. If the task required 15 integrations
across providers and vector stores, the dependency and abstraction-tax scores
would flip because you'd be comparing against writing all those integrations
yourself.

## The rubric

Six criteria, each scored 1–5 (higher is better):

| Criterion | What it measures |
|---|---|
| **lines_of_code** | How much code to express the task. 5 = <40 LoC. |
| **dependencies** | Transitive dependency count. 5 = <15 deps. |
| **debuggability** | Can you read the control flow top to bottom? 5 = yes. |
| **feature_access** | How easy to reach Anthropic-specific features (prompt caching, extended thinking, cache-aware tokens)? 5 = trivial. |
| **abstraction_tax** | How much does the framework's abstraction get in the way? 5 = no tax (inverted internally). |
| **typing_quality** | How well-typed end-to-end? 5 = every boundary is a typed object. |

Total out of 30.

**Important caveat on the ranking.** The scores reflect the AW Analysis
use case: Python, single provider, agent-heavy, Anthropic-specific features
matter. Under different constraints some scores would flip. A multi-provider
requirement makes LiteLLM's `feature_access` score much more tolerable. A
complex multi-agent workflow makes LangGraph's `debuggability` score much
more important. The rubric is a tool for committing to a defensible
judgement, not an objective ranking.

## Acceptance criteria

- [x] Baseline agent runs against all 5 test queries without errors.
- [x] Each of the 4 framework sketches is at least 40 lines of annotated
      pseudocode with inline comments.
- [x] The rubric produces a consistent per-implementation score across
      all 6 criteria.
- [x] Running `PYTHONPATH=$(pwd) python3 main.py` prints the baseline
      results, renders each sketch, and prints the final comparison table.
- [x] `comparison_report.md` is written to disk on successful run.
- [x] Exit code is `0` on successful baseline, `1` on baseline failure.

## What to take away

Three things this exercise is secretly teaching you:

**1. Ecosystem fluency is a reading skill.** You can read a framework in
an hour and place it on the layer map. Writing ten LangChain apps doesn't
teach you that; reading ten LangChain codebases does. The sketches are the
reading material.

**2. The rule beats the list.** "I've used LangChain, LlamaIndex, Pydantic
AI" is a list. "I reach for a framework when it owns a layer I don't want
to own" is a rule. The comparison report is the artefact that proves you
have a rule.

**3. Calibration, not advocacy.** The baseline is YOUR code, so there's a
temptation to inflate its scores. Resist it. The baseline loses on
`typing_quality` because the raw SDK returns content blocks that aren't
fully typed at every boundary. The baseline loses on `dependencies` only
narrowly because the Anthropic SDK itself brings a handful of deps. Be
honest about the trade-offs and the comparison becomes useful.

## Connection to previous modules

- **Module 1 (API):** the baseline's tool-use loop and JSON schema handling
  come straight from Module 1. The sketches wrap this same loop in
  different abstractions.
- **Module 3 (Agents):** the baseline is the Module 3 ReAct loop, lightly
  polished. LangGraph's sketch is what you'd build if you formalised the
  Module 3 loop as an explicit state machine — that comparison is the
  most instructive one in the exercise.
- **Module 6 (Evals):** the 5 test queries include a refusal case that
  echoes the Module 6 refusal scoring — same assistant, same rule.
- **Module 7 (Orchestration):** LiteLLM's Router is structurally very close
  to the Exercise 7.2 fallback chain. Comparing them side by side is
  probably the strongest calibration point in the whole module — you'll
  see that your hand-rolled design sits in well-trodden territory.

## Follow-up suggestions

If you want to extend the exercise:

- **Add a fifth sketch** for Instructor, DSPy, or Haystack. Each one owns
  a different slice of the stack and is worth the reading.
- **Swap the baseline model.** Run the baseline against Haiku and Opus
  and see whether the tool-use and refusal patterns change. This is a
  cheap regression test that reuses everything you built.
- **Convert one sketch to running code.** Pick the one you're most
  curious about (Pydantic AI is the closest to the baseline in spirit)
  and actually run it against the same 5 test queries. Diff the outputs.
  That's the next level of fluency.