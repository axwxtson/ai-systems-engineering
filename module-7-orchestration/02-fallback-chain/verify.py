"""Verification suite — runs every scenario and asserts expected outcomes.

For each scenario from injector.py, this module:
  1. Builds a fresh FallbackChain against the scripted MockProvider.
  2. Executes a single request through it.
  3. Asserts the expected outcome: final model, attempt counts per link,
     exhaustion state, whether the expected exception was raised.
  4. Reports pass/fail per scenario with a coloured summary.

Any failed assertion prints the trace so the discrepancy is obvious. Exit
code is 1 if any scenario fails, 0 otherwise.

This is the artefact that makes the chain trustworthy. Without it, the
exercise is "I wrote some retry logic and it seems to work." With it, every
failure mode is provably handled with a deterministic test that runs in
milliseconds and can be wired into CI.

Run from this directory with:
    PYTHONPATH=$(pwd) python3 verify.py
"""

import sys
from dataclasses import dataclass

from colorama import Fore, Style, init

from chain import ChainResult, FallbackChain, Link
from failures import ClientError
from injector import CHAIN_MODELS, Scenario, all_scenarios
from providers import CompletionRequest


init(autoreset=True)


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------


@dataclass
class AssertionResult:
    """Result of verifying a single scenario."""

    scenario: Scenario
    passed: bool
    failures: list[str]
    result: ChainResult | None
    raised: BaseException | None = None


def count_attempts_per_link(result: ChainResult, num_links: int) -> list[int]:
    """Reduce a ChainResult.attempts list to per-link attempt counts."""
    counts = [0] * num_links
    for attempt in result.attempts:
        if 0 <= attempt.link_index < num_links:
            counts[attempt.link_index] += 1
    return counts


def verify_scenario(scenario: Scenario) -> AssertionResult:
    """Run one scenario and check it against ExpectedOutcome.

    Builds a fresh provider + chain for each run so state from previous
    scenarios can't leak in.
    """
    provider = scenario.build_provider()
    chain = FallbackChain(
        links=[
            Link(provider=provider, model=model, timeout_seconds=5.0)
            for model in CHAIN_MODELS
        ]
    )
    request = CompletionRequest(
        messages=[{"role": "user", "content": "test query"}],
        model="",  # overridden per-link by the chain
        max_tokens=100,
    )

    failures: list[str] = []
    result: ChainResult | None = None
    raised: BaseException | None = None

    # Run the chain and capture whatever happens.
    try:
        result = chain.execute(request)
    except BaseException as exc:
        raised = exc

    expected = scenario.expected

    # Check: was an exception expected?
    if expected.raises is not None:
        if raised is None:
            failures.append(
                f"expected {expected.raises.__name__} to be raised, "
                f"but chain returned a result"
            )
        elif not isinstance(raised, expected.raises):
            failures.append(
                f"expected {expected.raises.__name__}, got "
                f"{type(raised).__name__}: {raised}"
            )
        # If the exception was expected, we still want to verify attempt counts
        # using the provider's call log since we don't have a ChainResult.
        if expected.attempts_per_link is not None and raised is not None:
            counts = [0] * len(CHAIN_MODELS)
            for req in provider.call_log:
                try:
                    idx = CHAIN_MODELS.index(req.model)
                    counts[idx] += 1
                except ValueError:
                    pass
            if counts != expected.attempts_per_link:
                failures.append(
                    f"attempts_per_link mismatch (from call log): "
                    f"expected {expected.attempts_per_link}, got {counts}"
                )
        return AssertionResult(
            scenario=scenario,
            passed=not failures,
            failures=failures,
            result=None,
            raised=raised,
        )

    # If no exception was expected but one was raised, that's a failure.
    if raised is not None:
        failures.append(
            f"chain raised unexpected {type(raised).__name__}: {raised}"
        )
        return AssertionResult(
            scenario=scenario,
            passed=False,
            failures=failures,
            result=None,
            raised=raised,
        )

    assert result is not None  # raised was None and no exception expected

    # Check: exhaustion state
    if result.exhausted != expected.exhausted:
        failures.append(
            f"exhausted mismatch: expected {expected.exhausted}, "
            f"got {result.exhausted}"
        )

    # Check: final model
    if expected.final_model != result.final_model:
        failures.append(
            f"final_model mismatch: expected {expected.final_model}, "
            f"got {result.final_model}"
        )

    # Check: attempts per link
    if expected.attempts_per_link is not None:
        actual_counts = count_attempts_per_link(result, len(CHAIN_MODELS))
        if actual_counts != expected.attempts_per_link:
            failures.append(
                f"attempts_per_link mismatch: "
                f"expected {expected.attempts_per_link}, got {actual_counts}"
            )

    # Scenario-specific extra checks
    if scenario.name == "retry_after_honoured":
        # The retry attempt must have a non-zero backoff_waited field.
        retries = [a for a in result.attempts if a.attempt_number > 0]
        if not retries:
            failures.append("expected at least one retry attempt, got none")
        elif retries[0].backoff_waited <= 0:
            failures.append(
                f"retry backoff not recorded: "
                f"backoff_waited={retries[0].backoff_waited}"
            )

    return AssertionResult(
        scenario=scenario,
        passed=not failures,
        failures=failures,
        result=result,
        raised=raised,
    )


# ---------------------------------------------------------------------------
# CLI output
# ---------------------------------------------------------------------------


def print_header(text: str) -> None:
    bar = "=" * 70
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{bar}")
    print(f"{text}")
    print(f"{bar}{Style.RESET_ALL}")


def print_result_line(idx: int, total: int, r: AssertionResult) -> None:
    if r.passed:
        status = f"{Fore.GREEN}PASS{Style.RESET_ALL}"
    else:
        status = f"{Fore.RED}FAIL{Style.RESET_ALL}"
    print(f"  [{idx:2d}/{total:2d}] {status}  {r.scenario.name:30s}  {r.scenario.description}")

    if not r.passed:
        for failure in r.failures:
            print(f"         {Fore.RED}- {failure}{Style.RESET_ALL}")
        if r.result is not None:
            print(f"         {Style.DIM}trace:{Style.RESET_ALL}")
            for a in r.result.attempts:
                s = "ok" if a.success else f"fail ({a.error_type})"
                print(
                    f"         {Style.DIM}  link{a.link_index} "
                    f"{a.model} attempt#{a.attempt_number} {s}{Style.RESET_ALL}"
                )


def main() -> int:
    print_header("Exercise 7.2 — Fallback Chain Verification Suite")

    scenarios = all_scenarios()
    print(f"Scenarios: {len(scenarios)}")
    print(f"Chain: {' → '.join(CHAIN_MODELS)}")
    print()
    print("Results:")

    results: list[AssertionResult] = []
    for i, scenario in enumerate(scenarios, start=1):
        r = verify_scenario(scenario)
        results.append(r)
        print_result_line(i, len(scenarios), r)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    print()
    print("=" * 70)
    if failed == 0:
        print(f"{Fore.GREEN}{Style.BRIGHT}All {passed} scenarios passed.{Style.RESET_ALL}")
    else:
        print(
            f"{Fore.RED}{Style.BRIGHT}{failed} scenario(s) failed, "
            f"{passed} passed.{Style.RESET_ALL}"
        )
    print("=" * 70)

    # Summary of what was verified
    print("\nWhat this suite verifies:")
    print("  - Happy path (clean success on link 0)")
    print("  - Retryable failures (rate limit, 5xx, malformed) retry correctly")
    print("  - Retry budgets are bounded; excess failures fall over")
    print("  - Non-retryable failures (timeout, refusal) fall over immediately")
    print("  - ClientError propagates without falling over")
    print("  - Chain exhaustion is detectable")
    print("  - Compound failures across multiple links recover on deeper links")
    print("  - Retry-After hint triggers a non-zero wait on retry")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())