# AW Analysis — Context Patterns for Cursor

Which files to pin with `@`-references for each common task type.
The principle: pin exactly what the model needs, nothing more. Over-pinning
adds noise; under-pinning causes hallucinated imports and wrong patterns.

---

## 1. Adding a new tool to the agent

**Pin:**
- `@file tasks.py` — tool schemas, mock data, test queries
- `@file baseline_agent.py` — tool dispatch loop

**Why these:** The tool schema definition and the dispatch logic are the
only two places that need to change. The agent loop itself doesn't change
when you add a tool — it already handles arbitrary tool calls.

**Do NOT pin:** `main.py` (it doesn't care about individual tools),
`sketches.py` (the framework sketches are strings, not running code).

---

## 2. Modifying the routing policy

**Pin:**
- `@file router.py` — ROUTING_POLICY dict and MODEL_ALIASES
- `@file pricing.py` — MODEL_PRICES (costs change routing economics)
- `@file eval_harness.py` — quality checks that validate routing decisions

**Why these:** A routing change affects which model handles which class,
what it costs, and whether quality is preserved. All three files are needed
to make an informed change.

**Do NOT pin:** `backends/` (observability doesn't change with routing),
`main.py` (CLI doesn't change).

---

## 3. Adding a new observability backend

**Pin:**
- `@file backends/base.py` — the EmissionBackend protocol and RoutingEvent
- `@file backends/langfuse_backend.py` — reference implementation to follow
- `@file main.py` — the `create_backend()` factory function and CLI args

**Why these:** The protocol defines the interface, the Langfuse backend
shows the pattern, and main.py is where the new backend gets wired in.

**Do NOT pin:** `router.py`, `eval_harness.py` (these emit events but don't
know or care which backend receives them — that's the point of the protocol).

---

## 4. Debugging a test failure

**Pin:**
- `@file {the_failing_test_file}` — the test itself
- `@file {the_module_under_test}` — the code being tested
- Paste the error traceback into the chat message

**Why these:** The model needs to see both the test expectation and the
actual code to diagnose the mismatch. The traceback gives it the exact
failure point.

**Use `@codebase` when:** you don't know which module is causing the
failure (e.g., an import error from a transitive dependency). Let Cursor
search for the symbol. Then narrow to `@file` once you've found it.

---

## 5. Writing or updating a README

**Pin:**
- `@file README.md` — the file being edited
- `@file main.py` — for CLI flags and usage examples
- `@file requirements.txt` — for setup instructions

**Why these:** The README documents how to run the exercise, so it needs
to reflect the actual CLI interface and dependencies.

**Do NOT pin:** implementation files (the README describes what they do,
not how they do it — that level of detail should come from you, not the
model).

---

## 6. Extending the eval harness

**Pin:**
- `@file eval_harness.py` — the harness itself
- `@file router.py` — TestQuery definitions and the queries being evaluated
- `@file backends/base.py` — RoutingEvent (the eval harness writes to it)

**Why these:** The eval harness reads from TestQuery, writes to RoutingEvent,
and runs its own checks. All three are needed for a coherent change.

---

## 7. Cross-module comparison or refactoring

**Pin:**
- `@file {module_a_file}` — first module's implementation
- `@file {module_b_file}` — second module's implementation

**Use `@codebase` when:** searching for all usages of a pattern across
modules (e.g., "find every place we use `anthropic.Anthropic()`").

**Why:** Cross-module work is the one case where `@codebase` earns its
keep. For everything else, explicit `@file` references are more precise
and produce better results.

---

## General rules

- **Default to `@file`.** It's the most precise and produces the best results.
- **Use `@folder` for:** understanding a module's structure when you're
  unfamiliar with it. Switch to `@file` once you know which files matter.
- **Use `@codebase` for:** semantic search when you don't know where something
  lives. It's a discovery tool, not a context tool.
- **Use `@docs` for:** pinning external documentation (Anthropic SDK docs,
  Langfuse docs) when the model needs API reference.
- **Never pin more than 4–5 files.** If you need more context than that,
  the task is probably too big for a single prompt — break it down.