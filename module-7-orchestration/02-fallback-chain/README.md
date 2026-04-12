# Exercise 7.2 — Fallback Chain

A resilience-focused fallback chain for multi-model LLM systems. Handles
rate limits, server errors, timeouts, refusals, malformed outputs, and
client errors — each with the correct retry-vs-fall-over behaviour. Every
decision is deterministic, every failure mode is provably handled by a
verification suite that runs in milliseconds without touching the API.

This is the layer that stops a Sonnet outage, a rate-limit spike, or a
single bad model call from becoming a user-visible failure.

---

## What this does

A `FallbackChain` is an ordered list of `Link`s, each bundling one provider
+ model + timeout config. On `chain.execute(request)`:

1. Try link 0. If it succeeds, return.
2. If it fails, classify the failure:
   - **Retryable** (rate limit, 5xx, malformed output): retry with
     exponential backoff + jitter, bounded by the per-failure-type retry
     budget. Respect `Retry-After` when present.
   - **Non-retryable, fall-over** (timeout, refusal, unknown error): skip
     retries, go straight to the next link.
   - **Fatal** (ClientError / 4xx): propagate immediately. Don't retry,
     don't fall over — this is the caller's bug.
3. If a link exhausts retries without success, move to the next link.
4. If every link fails, return a `ChainResult` with `exhausted=True` and
   the full attempt trace.

Every attempt (including retries) is recorded in a `LinkAttempt`, and the
aggregate metrics module produces per-link success rate, fallback rate,
retry count, and latency contribution across many executions.

---

## File structure

```
02-fallback-chain/
├── README.md
├── providers.py       # LLMProvider protocol, AnthropicProvider, MockProvider
├── failures.py        # typed failure hierarchy, classification, backoff
├── chain.py           # FallbackChain, Link, LinkAttempt, ChainResult
├── observability.py   # per-link metrics aggregation
├── main.py            # happy-path CLI (real API)
├── injector.py        # 12 failure scenarios via MockProvider
├── verify.py          # verification suite that asserts each scenario
└── requirements.txt
```

---

## Setup

```bash
cd module-7-orchestration/02-fallback-chain
pip3 install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Run

Two entry points, for different purposes:

**Happy path — real API:**
```bash
PYTHONPATH=$(pwd) python3 main.py
```
Runs 5 simple queries through a Haiku → Sonnet → Opus chain against the
real Anthropic API. On a clean API day, all requests satisfy on link 0
(Haiku). Produces `results.json` with traces and metrics.
Cost: ~$0.005. Time: ~10 seconds.

**Verification suite — mocked, deterministic:**
```bash
PYTHONPATH=$(pwd) python3 verify.py
```
Runs 12 failure scenarios through `MockProvider` and asserts the chain
responds correctly to each one. No API calls. No spend. No non-determinism.
Exit code 1 if any scenario fails.
Cost: $0. Time: <1 second.

---

## Design decisions

### Why a provider abstraction layer

The chain never calls the Anthropic SDK directly. It calls
`provider.complete(request)` and catches exceptions from our own typed
hierarchy. That indirection buys three things:

1. **Testability.** `MockProvider` can script exact failure sequences by
   handler (routes by request content) or by list (pops next response).
   The verification suite exercises every failure mode deterministically
   with zero API cost.
2. **Swap-ability.** A second provider (OpenAI, a local model, a new
   Anthropic beta) is one new class implementing the `LLMProvider` protocol.
   No changes to the chain or anything downstream.
3. **Unified failure surface.** The `AnthropicProvider` is responsible for
   translating SDK exceptions into our typed hierarchy at the provider
   boundary. The chain then reasons about failures uniformly — no
   `isinstance(exc, anthropic.SomeError)` anywhere upstream.

This is the Concept 7 (provider abstraction) pattern from the Module 7
reference. The cost is a thin translation layer; the benefit is that the
verification suite exists at all.

### Why a typed failure hierarchy

Every failure has a policy: retry, fall over, or raise. That policy depends
on the *kind* of failure, not its exception message. A single classification
table (`_CLASSIFICATION` in `failures.py`) maps every known failure type to
a `FailurePolicy(action, max_retries)`. The chain calls `classify(exc)`
once per attempt and acts on the result.

Adding a new failure mode is a two-line change: define the class, add one
row to the classification dict. Adding a new mode without this layer would
mean adding `isinstance` checks in every place the chain makes a decision.

| Failure             | Action        | Max retries |
|---------------------|---------------|-------------|
| RateLimitError      | Retry         | 2           |
| ServerError         | Retry         | 2           |
| MalformedOutputError| Retry         | 1           |
| TimeoutError_       | Fall over     | —           |
| RefusalError        | Fall over     | —           |
| UnknownProviderError| Fall over     | —           |
| ClientError         | Raise         | —           |
| *(unknown type)*    | Fall over     | —           |

The unknown-type default is fall over without retry. Safer than retrying
mystery errors; safer than crashing the request.

### Why timeouts don't retry

Retrying a timeout on the same model is rarely useful. If the model
didn't respond within its budget, it's either genuinely unavailable or
the request is too expensive for it to handle in that window. The more
useful action is to fall over to a faster or different model.

Rate limits and 5xx errors are different — those are transient server
states, and a short backoff + retry usually works.

### Why ClientError propagates instead of falling over

A 400 response is almost always a caller bug: malformed schema, invalid
field, missing required param. Falling over to the next link would mask
the bug — the caller would see "everything worked eventually" while every
first-link attempt silently 400s. The chain raises ClientError straight
through so the bug gets fixed.

### Why exponential backoff with jitter

Without jitter, many clients hitting a rate limit at the same moment all
retry at the same moment, producing a second rate-limit spike. Jitter
(±25% random spread on the wait) desynchronises retries so the server's
rate limiter can cool down naturally.

The cap (30s default) exists because exponential growth is fast. 2^10
seconds is 17 minutes — any wait that long is effectively a request
failure anyway, so the cap prevents the retry logic from inadvertently
making failures take longer than the original request.

### Why per-link observability matters

The single most important production metric for a fallback chain is the
per-link fallback rate. A Haiku link that normally satisfies 85% of
requests, suddenly falling over on 40%, is an incident — the cost model
has collapsed because 40% of your "cheap" requests are now paying for
Sonnet or Opus on top of Haiku.

Without per-link metrics, this degrades silently and only becomes visible
when the bill arrives. `observability.py` computes it per aggregation
window and the CLI reports it at the end of every run.

---

## Findings from the verification suite

The 12 scenarios in `injector.py` cover every category of failure the
chain was designed to handle. Every scenario passes. Worth calling out:

### 1. Retry bounds behave exactly as specified

- `rate_limit_recovered` hits the limit twice, succeeds on the second
  retry. 3 total attempts on link 0, no fall-over.
- `rate_limit_exhausts` hits the limit indefinitely. Chain retries twice
  (max_retries=2 for RateLimitError), then falls over after 3 attempts.
- `malformed_retry` fails once, recovers on the single allowed retry.
  2 total attempts on link 0.
- `malformed_exhausts` fails always. Chain retries once
  (max_retries=1 for MalformedOutputError), falls over after 2 attempts.

The retry budget is enforced exactly per the classification table. Every
attempt — including retries — is recorded and counted.

### 2. Non-retryable errors fall over immediately

- `timeout_fall_over` and `refusal_fall_over` both record exactly one
  attempt on link 0 before moving to link 1. No retries fire.
- This matters for latency: a timeout that triggered two retries would
  add 2× the timeout budget to user-facing latency before the chain
  even reached link 1. The immediate fall-over semantics keep latency
  bounded even in failure cases.

### 3. Compound failures recover on deeper links

- `cascading_recovery` exercises all three error-handling paths in one
  run: link 0 rate-limits indefinitely (retries exhaust), link 1 times
  out (immediate fall-over), link 2 succeeds. The chain correctly
  sequences through all three, records all 5 attempts, and returns Opus's
  response. This is the "every link has a problem today" scenario and
  the chain degrades gracefully.

### 4. Chain exhaustion is observable, not silent

- `chain_exhausts` returns a `ChainResult` with `exhausted=True`, the
  full attempt trace (3 attempts across 3 links), and `final_model=None`.
  Callers must handle this case explicitly — there's no way to accidentally
  treat an exhausted chain as a successful response because `response` is
  `None`.
- In production this is the outcome that should page someone: all three
  models failed on the same request, which is either a catastrophic
  provider incident or a malformed request that no model can handle.

### 5. ClientError propagates; does not mask bugs

- `client_error_propagates` asserts the chain raises `ClientError` on the
  first attempt without trying link 1 or link 2. Verified via the
  provider's call log: exactly one call, to link 0.
- This is the rule that makes the chain safe to wire into a production
  system. Bugs surface loudly instead of being silently absorbed.

### 6. Retry-After is honoured

- `retry_after_honoured` injects a `Retry-After=0.05s` hint on the first
  rate-limit error. The verification checks that the retry attempt's
  `backoff_waited` field is non-zero, confirming the chain consulted the
  hint rather than using pure exponential backoff.
- In production, respecting `Retry-After` is the difference between
  cooperating with the server's rate limiter and aggravating it. The
  standard retry logic would wait ~1 second; the server asked for 0.05
  and got 0.05.

---

## Running the real-API path

`main.py` runs 5 simple queries against a Haiku → Sonnet → Opus chain
using the live Anthropic API. On a clean API day the expected outcome is:

- 5/5 requests satisfied by link 0 (Haiku)
- 0 retries, 0 fallbacks, 0 exhaustions
- Mean end-to-end latency around 1-2 seconds per request
- Per-link metrics show link 0 100% success rate, links 1 and 2 never reached

This isn't where the exercise earns its keep — `verify.py` does that. But
running against the real API is the sanity check that the provider
translation layer actually works end-to-end with a real SDK response, a
real token count, a real latency measurement.

---

## What this exercise is not

- **Not a cascade.** This is a resilience fallback: links fire on failures,
  not on quality signals. A cascade would add a "is the output good enough?"
  check between links. That composes naturally on top of this chain — you'd
  add a structural check in the link success path that can raise
  `MalformedOutputError` to force escalation — but it's a separate concern
  and adds the cost of extra calls on every request.

- **Not a router.** 7.1 is the router. The cleanest production architecture
  uses both: the router picks the primary model per query class, and each
  routed request runs through a fallback chain where the primary is the
  routed choice and the fallbacks are models in adjacent tiers. Wiring 7.1
  and 7.2 together is a 20-line change in a real integration but is
  deliberately out of scope here — each exercise stands alone.

- **Not async.** Synchronous execution keeps the retry and backoff logic
  readable. For high-throughput production systems you'd add async (each
  `execute` call is independent, so async parallelism is straightforward)
  but nothing in the failure-handling semantics depends on it.

---

## Connection to Module 6

The verification suite is a direct application of the Module 6 lesson:
**evaluation isn't separate from engineering, it is engineering**. The
chain's correctness is proven by the same kind of deterministic test
harness Module 6 built for quality evaluation — except here the output
being graded is chain behaviour, not model output quality.

The "aggregate hides problems, trust per-case" lesson from Module 6 lands
here as: `observability.py` reports per-link metrics, not chain-level
averages. A chain with 95% overall success rate can have a link 0 failing
40% of the time, and that's the metric you alert on, not the aggregate.

---

## Known limitations

- **Timeouts are nominal, not enforced.** Each `Link` has a
  `timeout_seconds` field but the chain doesn't wrap the provider call in
  `asyncio.wait_for` or a thread timeout. A production version would — the
  current version relies on the SDK's own timeout handling.
- **Observability is in-process only.** Metrics are aggregated from the
  attempt list at the end of a batch. Real production systems stream per-
  attempt logs to a metrics backend (Honeycomb, Datadog, OpenTelemetry).
  The structure is ready for that — every `LinkAttempt` is a dataclass you
  can serialise and emit — but the emit path isn't wired in.
- **No circuit breaker.** If link 0 is failing consistently, the chain
  still tries it first on every request (wasting latency) rather than
  temporarily routing past it. A circuit breaker would detect sustained
  failure and skip the failing link for a cool-down window. Reasonable
  next addition but not in scope for this exercise.
- **Retry jitter uses Python's default `random`.** For production you'd
  seed with `random.SystemRandom` or equivalent. Jitter correctness
  doesn't depend on cryptographic-quality randomness but thread safety in
  async contexts might.

These are all things you'd discuss when explaining the chain in an
interview.