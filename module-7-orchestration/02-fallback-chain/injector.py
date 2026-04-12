"""Failure injector — scripted failure scenarios for testing the chain.

Real rate limits, 5xx errors, and timeouts are hard to trigger on demand.
This module produces MockProviders configured to simulate specific failure
modes at specific links, deterministically, for a single query. The
verification suite (verify.py) runs the chain against each scenario and
asserts that the chain responded correctly.

Every scenario returns a configured `MockProvider` and a short description.
The provider is wired via *handler mode* so the chain's per-link model
selection drives the failure behaviour — the handler looks at
`request.model` and decides what to do based on which link is calling it.

Why handler mode rather than list mode: the chain calls different models as
it falls over through links. List mode can't distinguish "this call is from
link 0" from "this call is from link 1" — it just pops the next response.
Handler mode makes the failure condition explicit: "fail on haiku, succeed
on sonnet."

Each scenario has:
  - A name (for reporting)
  - A short description (what failure this simulates)
  - A factory that builds the MockProvider
  - The expected chain behaviour (asserted by verify.py)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from failures import (
    ClientError,
    MalformedOutputError,
    RateLimitError,
    RefusalError,
    ServerError,
    TimeoutError_,
)
from providers import CompletionRequest, CompletionResponse, MockProvider


# ---------------------------------------------------------------------------
# Chain configuration used by every scenario
# ---------------------------------------------------------------------------


# The injector builds scenarios against a three-link chain with these model
# strings. verify.py constructs actual Link objects from the same strings so
# the chain and the injector stay in sync.
CHAIN_MODELS: list[str] = [
    "claude-haiku-4-5-20251001",  # link 0
    "claude-sonnet-4-6",          # link 1
    "claude-opus-4-6",            # link 2
]

LINK_0, LINK_1, LINK_2 = CHAIN_MODELS


def _ok_response(model: str, text: str = "OK") -> CompletionResponse:
    """Build a successful response for a given model."""
    return CompletionResponse(
        text=text,
        model_used=model,
        input_tokens=10,
        output_tokens=len(text.split()),
        stop_reason="end_turn",
        latency_seconds=0.0,
    )


# ---------------------------------------------------------------------------
# Expected outcomes — what verify.py will assert
# ---------------------------------------------------------------------------


@dataclass
class ExpectedOutcome:
    """What the chain should do in response to a scenario.

    Either the chain exhausts OR it succeeds on a specific model, having
    made a specific number of attempts.
    """

    exhausted: bool = False
    final_model: str | None = None
    # Per-link expected attempt counts. The list is the expected number of
    # attempts made against each link, in link order. A zero means "this
    # link should not have been tried." An exact count means "this exact
    # number of attempts, including retries."
    attempts_per_link: list[int] | None = None
    # If the scenario should raise a specific exception instead of returning,
    # set this. Used for ClientError which propagates out of the chain.
    raises: type[BaseException] | None = None


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@dataclass
class Scenario:
    name: str
    description: str
    build_provider: Callable[[], MockProvider]
    expected: ExpectedOutcome


def _scenario_clean_success() -> Scenario:
    """Baseline: no failures anywhere. Link 0 succeeds immediately."""
    def build():
        def handler(req: CompletionRequest) -> CompletionResponse:
            return _ok_response(req.model, f"clean {req.model}")
        return MockProvider(handler=handler)

    return Scenario(
        name="clean_success",
        description="No failures. Link 0 succeeds on first attempt.",
        build_provider=build,
        expected=ExpectedOutcome(
            final_model=LINK_0,
            attempts_per_link=[1, 0, 0],
        ),
    )


def _scenario_rate_limit_then_success() -> Scenario:
    """Link 0 rate-limited twice, succeeds on the third attempt (second retry)."""
    def build():
        state = {"count": 0}

        def handler(req: CompletionRequest) -> CompletionResponse:
            if req.model == LINK_0:
                state["count"] += 1
                if state["count"] <= 2:
                    raise RateLimitError("slow down", retry_after_seconds=0.01)
                return _ok_response(LINK_0, "recovered")
            return _ok_response(req.model)

        return MockProvider(handler=handler)

    return Scenario(
        name="rate_limit_recovered",
        description="Link 0 rate-limited twice, succeeds on retry. Chain stays on link 0.",
        build_provider=build,
        expected=ExpectedOutcome(
            final_model=LINK_0,
            # 3 attempts on link 0: first fails, retry 1 fails, retry 2 succeeds
            attempts_per_link=[3, 0, 0],
        ),
    )


def _scenario_rate_limit_exhausts_link0() -> Scenario:
    """Link 0 rate-limited indefinitely — exhausts retries and falls to link 1."""
    def build():
        def handler(req: CompletionRequest) -> CompletionResponse:
            if req.model == LINK_0:
                raise RateLimitError("still slow", retry_after_seconds=0.01)
            return _ok_response(req.model, "sonnet save")
        return MockProvider(handler=handler)

    return Scenario(
        name="rate_limit_exhausts",
        description="Link 0 rate-limits repeatedly. After 2 retries, falls over to link 1.",
        build_provider=build,
        expected=ExpectedOutcome(
            final_model=LINK_1,
            # Link 0: first + 2 retries = 3 attempts. Link 1: 1 attempt.
            attempts_per_link=[3, 1, 0],
        ),
    )


def _scenario_server_error_then_fall_over() -> Scenario:
    """Link 0 returns 500 repeatedly; link 1 succeeds."""
    def build():
        def handler(req: CompletionRequest) -> CompletionResponse:
            if req.model == LINK_0:
                raise ServerError("503 bad gateway")
            return _ok_response(req.model, "recovered")
        return MockProvider(handler=handler)

    return Scenario(
        name="server_error_fall_over",
        description="Link 0 returns 5xx on all attempts. Chain retries twice then falls over.",
        build_provider=build,
        expected=ExpectedOutcome(
            final_model=LINK_1,
            attempts_per_link=[3, 1, 0],
        ),
    )


def _scenario_timeout_immediate_fall_over() -> Scenario:
    """Link 0 times out — falls over immediately without retrying."""
    def build():
        def handler(req: CompletionRequest) -> CompletionResponse:
            if req.model == LINK_0:
                raise TimeoutError_("deadline exceeded")
            return _ok_response(req.model, "sonnet handled it")
        return MockProvider(handler=handler)

    return Scenario(
        name="timeout_fall_over",
        description="Link 0 times out. No retry on timeout — immediate fall over to link 1.",
        build_provider=build,
        expected=ExpectedOutcome(
            final_model=LINK_1,
            attempts_per_link=[1, 1, 0],
        ),
    )


def _scenario_refusal_fall_over() -> Scenario:
    """Link 0 refuses — falls over (same model would refuse again)."""
    def build():
        def handler(req: CompletionRequest) -> CompletionResponse:
            if req.model == LINK_0:
                raise RefusalError("I cannot comply with that request")
            return _ok_response(req.model, "sonnet answered")
        return MockProvider(handler=handler)

    return Scenario(
        name="refusal_fall_over",
        description="Link 0 refuses. Refusals never retry — fall over to link 1 immediately.",
        build_provider=build,
        expected=ExpectedOutcome(
            final_model=LINK_1,
            attempts_per_link=[1, 1, 0],
        ),
    )


def _scenario_malformed_output_retry_once() -> Scenario:
    """Link 0 produces malformed output once, then succeeds on retry."""
    def build():
        state = {"count": 0}

        def handler(req: CompletionRequest) -> CompletionResponse:
            if req.model == LINK_0:
                state["count"] += 1
                if state["count"] == 1:
                    raise MalformedOutputError("missing required field 'answer'")
                return _ok_response(LINK_0, "well-formed on retry")
            return _ok_response(req.model)
        return MockProvider(handler=handler)

    return Scenario(
        name="malformed_retry",
        description="Link 0 malformed output once. Chain retries once; second attempt succeeds.",
        build_provider=build,
        expected=ExpectedOutcome(
            final_model=LINK_0,
            attempts_per_link=[2, 0, 0],
        ),
    )


def _scenario_malformed_exhausts_retry() -> Scenario:
    """Malformed output gets exactly one retry, then falls over."""
    def build():
        def handler(req: CompletionRequest) -> CompletionResponse:
            if req.model == LINK_0:
                raise MalformedOutputError("always bad")
            return _ok_response(req.model, "sonnet clean")
        return MockProvider(handler=handler)

    return Scenario(
        name="malformed_exhausts",
        description="Link 0 always malformed. 1 retry budget; after 2 attempts, fall over.",
        build_provider=build,
        expected=ExpectedOutcome(
            final_model=LINK_1,
            # Link 0: first + 1 retry = 2 attempts. Link 1: 1 attempt.
            attempts_per_link=[2, 1, 0],
        ),
    )


def _scenario_client_error_propagates() -> Scenario:
    """ClientError (400 bad request) must propagate out — no fall over.

    The rule: 4xx (non-429) is the caller's bug. Falling over would mask it.
    """
    def build():
        def handler(req: CompletionRequest) -> CompletionResponse:
            raise ClientError("400: invalid request schema")
        return MockProvider(handler=handler)

    return Scenario(
        name="client_error_propagates",
        description="Link 0 raises ClientError. Chain must propagate, NOT fall over.",
        build_provider=build,
        expected=ExpectedOutcome(
            raises=ClientError,
            # Only link 0 is tried; the error stops the chain.
            attempts_per_link=[1, 0, 0],
        ),
    )


def _scenario_chain_exhaustion() -> Scenario:
    """Every link fails with a fall-over error. Chain exhausts."""
    def build():
        def handler(req: CompletionRequest) -> CompletionResponse:
            raise TimeoutError_(f"{req.model} also down")
        return MockProvider(handler=handler)

    return Scenario(
        name="chain_exhausts",
        description="Every link times out. Chain exhausts with full failure trace.",
        build_provider=build,
        expected=ExpectedOutcome(
            exhausted=True,
            final_model=None,
            attempts_per_link=[1, 1, 1],
        ),
    )


def _scenario_cascading_recovery() -> Scenario:
    """Link 0 and link 1 both fail with different modes; link 2 succeeds.

    Compound failure test: link 0 rate-limits indefinitely (exhausts retries,
    falls over), link 1 times out (immediate fall over), link 2 succeeds.
    Exercises all three error-handling paths in one run.
    """
    def build():
        def handler(req: CompletionRequest) -> CompletionResponse:
            if req.model == LINK_0:
                raise RateLimitError("persistent", retry_after_seconds=0.01)
            if req.model == LINK_1:
                raise TimeoutError_("too slow")
            return _ok_response(LINK_2, "opus to the rescue")
        return MockProvider(handler=handler)

    return Scenario(
        name="cascading_recovery",
        description="Link 0 rate-limits (retries exhaust), link 1 times out, link 2 succeeds.",
        build_provider=build,
        expected=ExpectedOutcome(
            final_model=LINK_2,
            # link 0: 3 attempts (first + 2 retries), link 1: 1, link 2: 1
            attempts_per_link=[3, 1, 1],
        ),
    )


def _scenario_retry_after_honoured() -> Scenario:
    """Rate limit with an explicit Retry-After hint.

    We can't directly assert the exact sleep duration without adding hooks
    into the chain, but we can assert the chain recovered and the backoff
    was greater than zero on the retry attempt. verify.py checks the
    retry attempt's `backoff_waited` field.
    """
    def build():
        state = {"count": 0}

        def handler(req: CompletionRequest) -> CompletionResponse:
            if req.model == LINK_0:
                state["count"] += 1
                if state["count"] == 1:
                    raise RateLimitError("slow", retry_after_seconds=0.05)
                return _ok_response(LINK_0, "recovered after wait")
            return _ok_response(req.model)
        return MockProvider(handler=handler)

    return Scenario(
        name="retry_after_honoured",
        description="Link 0 returns Retry-After=0.05s. Chain should wait at least that long.",
        build_provider=build,
        expected=ExpectedOutcome(
            final_model=LINK_0,
            attempts_per_link=[2, 0, 0],
        ),
    )


# ---------------------------------------------------------------------------
# All scenarios exposed as a single list
# ---------------------------------------------------------------------------


def all_scenarios() -> list[Scenario]:
    """The full scenario list, in verification order.

    verify.py iterates this list and runs each scenario through a fresh
    FallbackChain built from the same CHAIN_MODELS.
    """
    return [
        _scenario_clean_success(),
        _scenario_rate_limit_then_success(),
        _scenario_rate_limit_exhausts_link0(),
        _scenario_server_error_then_fall_over(),
        _scenario_timeout_immediate_fall_over(),
        _scenario_refusal_fall_over(),
        _scenario_malformed_output_retry_once(),
        _scenario_malformed_exhausts_retry(),
        _scenario_client_error_propagates(),
        _scenario_chain_exhaustion(),
        _scenario_cascading_recovery(),
        _scenario_retry_after_honoured(),
    ]