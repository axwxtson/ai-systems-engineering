# AW Analysis — Reusable Cursor Prompts

Tested prompts for common development tasks in the AW Analysis repo.
Each has a template with `{placeholder}` slots and a filled-in example.

---

## 1. Add a new tool to the agent

**When:** Extending the agent's capabilities with a new data source or action.

**Template:**
```
Add a new tool called `{tool_name}` to the agent. It takes {parameters}
and returns {return_shape}. Add the JSON schema to the tools list in
tasks.py, add mock data for testing, add the dispatch case in
execute_tool(), and add one test query that exercises it.
Do not modify any existing tools or test queries.
```

**Example:**
```
Add a new tool called `get_market_sentiment` to the agent. It takes a
`ticker` string and returns {"ticker": str, "sentiment": str, "score": float}.
Add the JSON schema to the tools list in tasks.py, add mock data for
testing, add the dispatch case in execute_tool(), and add one test query
that exercises it.
Do not modify any existing tools or test queries.
```

**Pin:** `@file tasks.py`, `@file baseline_agent.py`

---

## 2. Add a new eval case

**When:** Extending the test coverage of the eval harness.

**Template:**
```
Add a new test case to the eval harness for the following scenario:
{scenario_description}. The expected behaviour is: {expected_behaviour}.
Add it to the test queries list with id="{case_id}", query_class="{class}".
Do not modify existing test cases.
```

**Example:**
```
Add a new test case to the eval harness for the following scenario:
user asks for a comparison between two asset classes but one doesn't exist
("Compare Bitcoin and Vibranium"). The expected behaviour is: the agent
should handle the unknown asset gracefully and explain it doesn't have
data for it.
Add it to the test queries list with id="q7_unknown_asset", query_class="medium".
Do not modify existing test cases.
```

**Pin:** `@file router.py` (for TEST_QUERIES), `@file eval_harness.py`

---

## 3. Add a new model to the router

**When:** The model lineup changes (new release, deprecation, pricing change).

**Template:**
```
Add {model_name} ({model_id}) to the router. Update MODEL_ALIASES in
router.py and MODEL_PRICES in pricing.py. Pricing is ${input_price}/${output_price}
per million tokens. Do not change the routing policy — just make the model
available.
```

**Example:**
```
Add Sonnet 4.6 (claude-sonnet-4-6) to the router. Update MODEL_ALIASES in
router.py and MODEL_PRICES in pricing.py. Pricing is $3.00/$15.00
per million tokens. Do not change the routing policy — just make the model
available.
```

**Pin:** `@file router.py`, `@file pricing.py`

---

## 4. Add a new observability backend

**When:** Integrating a new observability vendor.

**Template:**
```
Add a new observability backend called `{BackendName}` in
backends/{filename}.py. It should implement the EmissionBackend protocol
(emit and flush methods). Use the {vendor_sdk} SDK. Follow the same
structure as langfuse_backend.py. Add it to the --backend CLI choices
in main.py.
```

**Example:**
```
Add a new observability backend called `HeliconeBackend` in
backends/helicone_backend.py. It should implement the EmissionBackend protocol
(emit and flush methods). Use the helicone SDK. Follow the same
structure as langfuse_backend.py. Add it to the --backend CLI choices
in main.py.
```

**Pin:** `@file backends/base.py`, `@file backends/langfuse_backend.py`, `@file main.py`

---

## 5. Write a test for a specific function

**When:** Adding test coverage for a module.

**Template:**
```
Write tests for the `{function_name}` function in {module_path}.
Test the following cases: {case_list}.
Use plain assert statements — no pytest fixtures or parametrize unless
the cases genuinely benefit from it. Put the test file in the same
directory as the module.
```

**Example:**
```
Write tests for the `compute_cost` function in pricing.py.
Test the following cases: known model with realistic token counts,
unknown model returns 0.0, zero tokens returns 0.0, large token
counts produce expected cost.
Use plain assert statements — no pytest fixtures or parametrize unless
the cases genuinely benefit from it. Put the test file in the same
directory as the module.
```

**Pin:** `@file pricing.py`

---

## 6. Refactor a function that's too long

**When:** A function has grown past ~40 lines and needs decomposition.

**Template:**
```
Refactor `{function_name}` in {file_path}. It's currently {line_count}
lines. Extract the {section_description} into a helper function called
`{helper_name}`. Keep the public interface unchanged. Do not modify
any other functions in this file.
```

**Example:**
```
Refactor `run_baseline` in main.py. It's currently 55 lines. Extract the
per-query output formatting into a helper function called
`format_query_result`. Keep the public interface unchanged. Do not modify
any other functions in this file.
```

**Pin:** `@file main.py`

---

## 7. Update a README with actual run results

**When:** After running an exercise and verifying the output.

**Template:**
```
Update the README.md to replace the "Expected output" section with an
"Actual run results" section. Use the following terminal output:

{paste terminal output}

Format the results as a markdown table with columns for {column_list}.
Add a "Key observations" section with 2-3 bullet points about what the
results show. Do not modify any other sections of the README.
```

**Pin:** `@file README.md`

---

## 8. Fix a specific bug

**When:** You've identified exactly what's wrong and where.

**Template:**
```
In {file_path}, the `{function_name}` function has a bug: {bug_description}.
The fix is: {fix_description}. Make only this change — do not refactor
surrounding code or add features.
```

**Example:**
```
In eval_harness.py, the `_judge_quality` function has a bug: it uses
json.loads() directly on the LLM response, but Haiku 4.5 sometimes
wraps JSON in markdown code fences. The fix is: use a regex to extract
the JSON object from anywhere in the response before parsing. Make only
this change — do not refactor surrounding code or add features.
```

**Pin:** `@file eval_harness.py`

---

## 9. Generate a commit message

**When:** After reviewing a diff and wanting a multi-line commit message.

**Template:**
```
Write a git commit message for the following changes. First line: summary
under 72 chars. Then a blank line, then 2-4 lines explaining what changed
and the key insight. Use the style: what was built, what was found, what
the pattern is. Do not use conventional commit prefixes (feat:, fix:, etc.).

Changes:
{paste git diff summary or describe the changes}
```

**Pin:** none needed — this is a chat-only prompt

---

## 10. Scaffold a new exercise

**When:** Starting a new exercise from the spec in the module reference doc.

**Template:**
```
Create the file structure for Exercise {exercise_number} based on this spec:
{paste the exercise spec from the module reference doc}

Create the directory, README.md with setup instructions and acceptance
criteria, an empty main.py with the CLI argument structure, and a
requirements.txt. Do not write the implementation — just the skeleton.
Use the same patterns as Exercise {reference_exercise} for the CLI and
coloured output.
```

**Pin:** `@file {reference_exercise}/main.py`, `@file {reference_exercise}/README.md`