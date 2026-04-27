# Exercise 8.2 — Observability Spike: Wire the Module 7 Router into Langfuse

**Module 8 · Tool Ecosystem & Workflows**

Wire a simplified Module 7 router into an observability backend so that
every `(query, routing_decision, model, latency, cost, quality_score)`
tuple lands in a real observability system with per-trace drill-down.
The exercise produces a screen-shareable artefact you can show in an
interview — very few candidates have this.

## What this exercise builds

- **A simplified router** (`router.py`) — deterministic policy:
  easy → Haiku, medium → Sonnet, hard → Sonnet. Six test queries
  across easy/medium/hard classes.
- **A backend-agnostic emission layer** (`emit.py` + `backends/`) —
  the same `EmissionBackend` protocol pattern from Module 7's provider
  abstraction, applied at the observability layer.
- **Two backend implementations:**
  - `StdoutBackend` — prints structured JSON events. No external
    dependencies. The default. Works offline.
  - `LangfuseBackend` — pushes events to a Langfuse project via the
    Python SDK v3. Each event becomes a trace with a generation span
    and an optional quality score.
- **A simplified eval harness** (`eval_harness.py`) — three checks
  per output: refusal detection, length check, and optional LLM-as-judge.
  Quality scores flow into the observability events.

## File structure

```
module-8-tool-ecosystem/02-observability-spike/
├── README.md
├── main.py                    # CLI with coloured output
├── router.py                  # simplified Module 7 router with emit hooks
├── emit.py                    # backend-agnostic emission interface
├── eval_harness.py            # simplified eval producing quality scores
├── pricing.py                 # model price table + cost calculator
├── backends/
│   ├── __init__.py            # empty — exists for package resolution
│   ├── base.py                # EmissionBackend protocol + RoutingEvent dataclass
│   ├── stdout_backend.py      # prints JSON events to stdout
│   └── langfuse_backend.py    # Langfuse SDK v3 integration
├── dashboards/                # Langfuse dashboard screenshots
└── requirements.txt
```

## Setup

```bash
# from the 02-observability-spike/ folder
pip3 install -r requirements.txt --break-system-packages

# API key (already set from Module 1)
export ANTHROPIC_API_KEY="sk-ant-..."
```

Note: Python 3.14 requires the `PYTHONPATH=$(pwd)` prefix for cross-module
relative imports.

## Running it

### Default run — stdout backend, deterministic eval only

```bash
PYTHONPATH=$(pwd) python3 main.py
```

### With LLM-as-judge quality scoring

```bash
PYTHONPATH=$(pwd) python3 main.py --judge
```

### With Langfuse backend

```bash
PYTHONPATH=$(pwd) python3 main.py --backend langfuse --judge
```

### Other flags

```bash
PYTHONPATH=$(pwd) python3 main.py --pretty          # pretty-print JSON (stdout only)
PYTHONPATH=$(pwd) python3 main.py --no-eval          # skip all quality evaluation
```

## Actual run results

### Langfuse backend + LLM-as-judge — 6/6 queries routed and emitted

| Query | Class | Model | Latency | Cost | Quality | Judge summary |
|---|---|---|---|---|---|---|
| `q1_price` | easy | Haiku 4.5 | 2534ms | $0.000888 | 1.000 | Correctly acknowledged real-time limitation, provided sources |
| `q2_summary` | medium | Sonnet 4 | 5747ms | $0.003369 | 1.000 | Honest about limitations, actionable alternatives |
| `q3_refusal` | easy | Haiku 4.5 | 2576ms | $0.000975 | 1.000 | Clean refusal with analytical framework offered |
| `q4_synthesis` | hard | Sonnet 4 | 8295ms | $0.004083 | 0.840 | Good structure, minor length overshoot (153 words vs 150 limit) |
| `q5_formatting` | medium | Sonnet 4 | 7865ms | $0.004011 | 0.700 | Table format correct, judge flagged currency/accuracy issues |
| `q6_simple` | easy | Haiku 4.5 | 1864ms | $0.000835 | 1.000 | Accurate RSI definition with appropriate caveats |

**Totals:** $0.014161 across 6 queries. 429 input / 1218 output tokens. Avg quality: 0.923.

### Per-model breakdown

| Model | Calls | Cost | Avg quality |
|---|---|---|---|
| claude-haiku-4-5-20251001 | 3 | $0.002698 | 1.000 |
| claude-sonnet-4-20250514 | 3 | $0.011463 | 0.847 |

Key observations:

- **Haiku 4.5 scored perfect quality on all easy-class queries.** The routing
  policy is validated — cheap model handles the easy class without quality loss.
  This is the Module 7 finding confirmed in a different context.
- **The only quality dips were on Sonnet queries.** q4 lost points on length
  (153 words vs 150 limit — a system prompt calibration issue, not a routing
  problem). q5 lost points because the judge correctly flagged currency confusion
  and implausible YTD figures — a genuine quality issue the judge caught.
- **Langfuse received 6 traces with 12 observations** (one trace span + one
  generation span per query). Cost breakdown by model, per-use-case cost charts,
  and latency metrics all visible in the dashboard.

### Langfuse dashboard screenshots

Saved in `dashboards/`:
- Usage management: 6 traces, 12 observations, cost by model name
- Cost dashboard: per-use-case cost breakdown, per-model cost, P95 cost per trace
- Latency dashboard: P95 latency by use case and by observation level

## Langfuse setup

1. **Create a free account** at https://cloud.langfuse.com (EU) or
   https://us.cloud.langfuse.com (US).

2. **Create a project** — name it something like "AW Analysis - Module 8".

3. **Get your API keys** from Settings → API Keys in the Langfuse dashboard.

4. **Set environment variables** in `~/.zshrc`:

```bash
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_HOST="https://cloud.langfuse.com"
```

5. `source ~/.zshrc` and run with `--backend langfuse`.

## The pattern the exercise is really about

**The emit layer is yours. The backend is swappable.**

Adding a new backend (Helicone, Honeycomb, Braintrust) should be under
30 lines — implement `emit(event)` and `flush()` on the `EmissionBackend`
protocol. The router and eval harness don't change. That's the point.

This is the same lesson as Module 7's provider abstraction: decouple the
calling code from the destination. The justification is testability —
the stdout backend proves the abstraction works without any external
dependency.

## Acceptance criteria

- [x] Running with `--backend stdout` prints structured JSON events for
      every routed call. No external dependencies beyond the Anthropic SDK.
- [x] Running with `--backend langfuse` pushes events to a Langfuse project
      visible at langfuse.com.
- [x] Every event includes: timestamp, model, query, query_class,
      input_tokens, output_tokens, latency_ms, cost_usd, routing_decision,
      and optionally quality_score.
- [x] The backend is swappable at runtime via `--backend stdout|langfuse`.
- [x] The eval harness produces quality scores that flow into the events.
- [x] Exit code is 0 on success.

## Connection to previous modules

- **Module 6 (Evals):** the eval harness reuses the LLM-as-judge pattern
  (Haiku as cheap judge) and the refusal detection from Module 6's
  red-team findings.
- **Module 7 (Orchestration):** the router is a simplified version of the
  Exercise 7.1 routing policy. The `EmissionBackend` protocol mirrors the
  Exercise 7.2 provider abstraction — same pattern, different layer.
- **Module 8 Concept 8 (Observability):** this is the "build the emit
  layer, buy the backend" rule in action. The emit layer is ~35 lines.
  The stdout backend is ~25 lines. The Langfuse backend is ~70 lines.
  Swapping backends doesn't touch the router or the eval harness.

## What to take away

**1. Observability is an engineering pattern, not a product choice.**
The emit/backend split means you're not locked into Langfuse — you're
locked into a pattern that works with any backend. The product choice
is deferred to deployment time.

**2. Quality scores in the observability layer are the killer feature.**
Most observability setups track cost and latency but not quality. Adding
the eval harness output to every event means you can correlate quality
drops with routing changes, model updates, or cost spikes — in the
dashboard, not in a separate analysis step.

**3. The stdout backend is the interview move.** If an interviewer asks
"show me how you'd add observability to this system," you can run
`--backend stdout` and show structured JSON events in the terminal in
under a minute. No accounts, no dashboards, no waiting. Then you say
"and here's the same data in Langfuse" and show the screenshot.