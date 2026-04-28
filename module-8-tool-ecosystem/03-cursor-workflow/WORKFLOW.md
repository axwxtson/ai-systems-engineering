# AW Analysis — Cursor Workflow

How to use Cursor effectively against the AW Analysis repo. This isn't a
Cursor tutorial — it's a workflow document written after actually using
Cursor on this codebase, describing what works, what doesn't, and why.

## The mental model

Cursor is a VS Code fork with four AI features: inline edit (⌘K), chat
panel, composer, and agent mode. The feature that matters most is none of
these — it's the `.cursorrules` file at the repo root, which gets
prepended to every conversation. That file is where you encode the
project's architectural constraints so the model stops making the same
mistakes.

The second most important feature is `@`-references in the chat panel.
These control what's in the model's context window. The untrained Cursor
user lets the model search the whole codebase; the trained one pins
exactly the two or three files the model needs.

## When to use each mode

### Inline edit (⌘K) — the default for small changes

Use for: renaming variables, fixing a bug in a single function, adding
a docstring, adjusting a prompt string, updating a model ID.

The workflow: select the code, press ⌘K, type the instruction, review
the diff, accept or reject. This is the tightest feedback loop Cursor
offers.

**AW Analysis example:** Select the `ROUTING_POLICY` dict in
`module-8-tool-ecosystem/02-observability-spike/router.py`, press ⌘K,
type "add a 'critical' class that routes to opus." Review the one-line
diff. Accept.

### Chat panel — for exploration and questions

Use for: understanding unfamiliar code, asking "what would break if I
changed X", drafting an approach before editing, debugging a test failure.

The workflow: open the chat, pin context with `@file` references, ask
the question. Read the answer. If it proposes code, copy it manually
rather than using the "apply" button — this forces you to read every
line.

**AW Analysis example:** Pin `@file module-6-eval-testing/01-eval-suite/judge.py`
and `@file module-7-orchestration/01-model-router/judge.py`, then ask
"these two judges use different rubric structures — what would a unified
rubric interface look like?" Read the answer. Don't apply it yet — think
about whether the abstraction is warranted.

### Composer — for multi-file changes

Use for: adding a new tool to the agent (touches the tool schema, the
executor, the test queries, and the README), adding a new backend to the
observability layer (new file plus updates to the factory function and
the CLI args).

The workflow: write a clear, scoped instruction. Pin the files that need
to change with `@file` references. Let composer propose the diffs. Review
every file's diff individually — this is where most mistakes happen,
because composer changes more than you asked for.

**AW Analysis example:** "Add a new `search_news` tool to the Exercise
8.1 baseline agent. The tool takes a `query` string and returns mock
news results. Update `tasks.py` with the tool schema and mock data,
`baseline_agent.py` to dispatch the tool, and add one new test query
that uses it."

Pin: `@file tasks.py`, `@file baseline_agent.py`, `@file main.py`.

### Agent mode — for larger tasks with caution

Use for: scaffolding a new exercise from scratch, generating boilerplate
for a new module, running and iterating on test failures.

The workflow: give it a clear goal with acceptance criteria. Let it run.
Watch what it does. Stop it if it starts refactoring files you didn't
mention. Review the full diff before committing.

**AW Analysis example:** "Create the skeleton for Exercise 8.3 following
the same file structure as Exercise 8.2: README.md, main.py, and a
requirements.txt. Don't write the implementation — just the structure
and docstrings."

**When NOT to use agent mode:** anything touching the eval harness or
the routing policy. These are precision systems where you want to control
every line. Use inline edit or manual coding for these.

## The five rules

1. **Think before you prompt.** Write the requirement in a sentence before
   opening the prompt box. If you can't articulate what you want in one
   sentence, you're not ready to prompt.

2. **Pin context explicitly.** Use `@file` for the specific files the model
   needs. Use `@folder` sparingly. Use `@codebase` only for semantic search
   when you genuinely don't know where something lives. Never let autosearch
   substitute for deliberate context selection.

3. **Prefer inline edit over composer for small changes.** Composer is
   tempting but produces sprawling diffs. If the change touches one file,
   use inline edit. If it touches two, probably still use inline edit twice.
   Composer is for three-plus files.

4. **Read every diff.** Every single one. If you accept a diff without
   reading it, the commit isn't yours. On interview day you won't be able
   to explain what you changed.

5. **Update `.cursorrules` when Cursor repeats a mistake.** If it keeps
   using `python` instead of `python3`, or keeps importing LangChain, or
   keeps writing American English — add the rule. Don't keep correcting
   the same mistake manually.

## The escalation path when Cursor gets stuck

1. **Rephrase the prompt.** Most failures are prompt failures. Try being
   more specific about what you want and more explicit about what you
   don't want.

2. **Reduce context.** Remove `@`-references that aren't directly relevant.
   More context isn't always better — sometimes it's noise.

3. **Switch to inline edit.** If composer or agent mode is thrashing,
   drop down to inline edit on the specific function that needs to change.

4. **Switch to Claude Code.** If Cursor can't handle it, open the terminal
   and use Claude Code with Opus. This is the escape hatch for genuinely
   complex tasks — the model is better, the context is your full filesystem,
   and you get explicit tool use rather than implicit editor integration.

5. **Write it yourself.** Sometimes the fastest path is manual coding.
   AI-assisted coding is a multiplier, not a requirement. If you've spent
   more than 10 minutes fighting the tool, write the code.

## Cursor vs Claude Code — when to use which

| Situation | Tool | Why |
|---|---|---|
| Quick fix in one file | Cursor inline edit | Fastest feedback loop |
| Multi-file refactor | Cursor composer | Multi-file diffing in editor |
| New feature from scratch | Claude Code | Better agent loop, full filesystem |
| Debugging test failures | Cursor chat | Can pin test + source + error |
| Complex architecture decisions | Claude Projects | Planning, not coding |
| Interview demo | Cursor | Visual, screen-shareable |