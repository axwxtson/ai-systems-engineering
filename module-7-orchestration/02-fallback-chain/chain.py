"""FallbackChain — execute a request through an ordered list of links.

A Link wraps one (provider, model, config) combination. A FallbackChain is an
ordered list of links executed sequentially until one returns a response or
the chain exhausts.

The execution model, per link:

    1. Record attempt start time
    2. Call provider.complete(request)
    3a. On success: return, recording link + latency + result
    3b. On failure: classify the exception
        - RAISE: propagate to caller (fatal — caller's bug)
        - RETRY: wait (backoff + jitter, respect Retry-After), try again
          up to max_retries. If still failing, fall over.
        - FALL_OVER: move to the next link immediately
    4. If all links fall over: raise ChainExhaustedError with the full trace

Every decision is logged in a LinkAttempt record. The LinkAttempt list is
what observability.py consumes to produce the per-link metrics.

Design notes:

- Timeouts are per-link. The link's `timeout_seconds` is an upper bound on
  how long the provider call may take. In this exercise we don't actually
  enforce the timeout (the Anthropic SDK has its own timeout handling); we
  use the link's timeout as metadata and as the budget a provider's timeout
  argument *would* be set to. A production version would wrap the call in
  asyncio.wait_for or a thread-based timeout.
- The chain is synchronous. Async comes later if Step 3 needs it; none of
  the failure modes require async to demonstrate.
- Exhaustion is an exception, not a None return. Callers should be forced
  to handle the "every link failed" case explicitly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from failures import (
    ClientError,
    FailureAction,
    ProviderError,
    backoff_seconds,
    classify,
)
from providers import CompletionRequest, CompletionResponse, LLMProvider


# ---------------------------------------------------------------------------
# Link configuration
# ---------------------------------------------------------------------------


@dataclass
class Link:
    """One link in the fallback chain.

    The link bundles a provider, the model to call, and the per-link timing
    budget. The chain doesn't care whether the provider is mocked or real —
    it just calls `provider.complete()` and handles the exceptions.
    """

    provider: LLMProvider
    model: str
    timeout_seconds: float = 30.0
    # Retry behaviour comes from the failure classification, but the link
    # can cap max retries at a lower value than the classification allows.
    # This is how you implement "Opus only gets one retry, everyone else gets two."
    max_retries_override: int | None = None

    @property
    def label(self) -> str:
        """Short human-readable label for logs."""
        return f"{self.model.split('-')[1] if '-' in self.model else self.model}"


# ---------------------------------------------------------------------------
# Execution trace — one record per attempt (including retries)
# ---------------------------------------------------------------------------


@dataclass
class LinkAttempt:
    """Record of a single provider call made by the chain.

    One chain execution may produce many LinkAttempts: one per retry per link,
    plus one per link tried. The LinkAttempt list is the primary data source
    for observability metrics.
    """

    link_index: int         # 0-indexed position in the chain
    model: str
    attempt_number: int     # 0 = first try, 1 = first retry, ...
    success: bool
    latency_seconds: float
    error_type: str | None = None
    error_message: str | None = None
    backoff_waited: float = 0.0  # seconds waited before this attempt (for retries)


@dataclass
class ChainResult:
    """Final result of a chain execution.

    Holds the successful response (or None if the chain exhausted) plus the
    full attempt trace for observability.
    """

    response: CompletionResponse | None
    attempts: list[LinkAttempt]
    exhausted: bool
    total_latency_seconds: float

    @property
    def final_model(self) -> str | None:
        """The model that produced the final successful response, if any."""
        return self.response.model_used if self.response else None

    @property
    def links_tried(self) -> int:
        """How many distinct links were attempted (not counting retries)."""
        if not self.attempts:
            return 0
        return len({a.link_index for a in self.attempts})


# ---------------------------------------------------------------------------
# Chain exhaustion — the "everything failed" error
# ---------------------------------------------------------------------------


class ChainExhaustedError(Exception):
    """Raised when every link in the chain has fallen over without a response.

    Holds the full attempt trace so callers can log or degrade gracefully.
    Callers that reach this exception should either return a cached response,
    show a "service temporarily unavailable" message, or queue the request
    for later retry — they should NOT swallow it silently.
    """

    def __init__(self, attempts: list[LinkAttempt]):
        self.attempts = attempts
        last_errors = [
            f"link{a.link_index}({a.model}): {a.error_type}" for a in attempts if not a.success
        ]
        super().__init__(
            f"Fallback chain exhausted after {len(attempts)} attempts. "
            f"Last errors: {', '.join(last_errors[-3:])}"
        )


# ---------------------------------------------------------------------------
# The chain itself
# ---------------------------------------------------------------------------


class FallbackChain:
    """An ordered list of links, executed with retry + fall-over semantics.

    Usage:

        chain = FallbackChain([
            Link(provider, "claude-haiku-4-5-20251001", timeout_seconds=5.0),
            Link(provider, "claude-sonnet-4-6",          timeout_seconds=15.0),
            Link(provider, "claude-opus-4-6",            timeout_seconds=30.0),
        ])

        result = chain.execute(request)
        if result.exhausted:
            # every link failed
            ...
        else:
            print(result.response.text)
    """

    def __init__(self, links: list[Link]):
        if not links:
            raise ValueError("FallbackChain requires at least one link.")
        self.links = links

    def execute(self, request: CompletionRequest) -> ChainResult:
        """Run the request through the chain. Never raises on a handled failure
        — instead returns a ChainResult with exhausted=True. Raises only on
        ClientError (caller's bug) or programmer errors.
        """
        attempts: list[LinkAttempt] = []
        chain_start = time.perf_counter()

        for link_index, link in enumerate(self.links):
            # Copy the request and override the model for this link.
            link_request = CompletionRequest(
                messages=request.messages,
                model=link.model,
                max_tokens=request.max_tokens,
                system=request.system,
                temperature=request.temperature,
                tools=request.tools,
            )

            result = self._try_link(link, link_index, link_request, attempts)
            if result is not None:
                # Success on this link.
                return ChainResult(
                    response=result,
                    attempts=attempts,
                    exhausted=False,
                    total_latency_seconds=time.perf_counter() - chain_start,
                )
            # otherwise: link fell over, try the next one

        # All links exhausted.
        return ChainResult(
            response=None,
            attempts=attempts,
            exhausted=True,
            total_latency_seconds=time.perf_counter() - chain_start,
        )

    def _try_link(
        self,
        link: Link,
        link_index: int,
        request: CompletionRequest,
        attempts: list[LinkAttempt],
    ) -> CompletionResponse | None:
        """Try one link with its retry budget.

        Returns the successful response, or None if the link fell over
        (chain should move on to the next link). Raises on ClientError —
        those propagate all the way out to the caller.
        """
        attempt_number = 0
        backoff_waited = 0.0

        while True:
            start = time.perf_counter()
            try:
                response = link.provider.complete(request)
            except BaseException as exc:
                elapsed = time.perf_counter() - start
                policy = classify(exc)

                # Fatal: propagate immediately. Do not fall over.
                if policy.action == FailureAction.RAISE:
                    attempts.append(
                        LinkAttempt(
                            link_index=link_index,
                            model=link.model,
                            attempt_number=attempt_number,
                            success=False,
                            latency_seconds=elapsed,
                            error_type=type(exc).__name__,
                            error_message=str(exc),
                            backoff_waited=backoff_waited,
                        )
                    )
                    raise

                # Record this failed attempt.
                attempts.append(
                    LinkAttempt(
                        link_index=link_index,
                        model=link.model,
                        attempt_number=attempt_number,
                        success=False,
                        latency_seconds=elapsed,
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                        backoff_waited=backoff_waited,
                    )
                )

                # Decide what to do next.
                if policy.action == FailureAction.FALL_OVER:
                    return None

                # policy.action == RETRY
                max_retries = policy.max_retries
                if link.max_retries_override is not None:
                    max_retries = min(max_retries, link.max_retries_override)

                if attempt_number >= max_retries:
                    # We've exhausted the retry budget for this link.
                    # Fall over to the next link.
                    return None

                # Wait before retrying. Respect Retry-After if present.
                retry_after = getattr(exc, "retry_after_seconds", None)
                backoff_waited = backoff_seconds(
                    attempt_number,
                    base=1.0,
                    cap=30.0,
                    jitter=0.25,
                    retry_after=retry_after,
                )
                time.sleep(backoff_waited)
                attempt_number += 1
                continue

            # Success. Record and return.
            elapsed = time.perf_counter() - start
            attempts.append(
                LinkAttempt(
                    link_index=link_index,
                    model=link.model,
                    attempt_number=attempt_number,
                    success=True,
                    latency_seconds=elapsed,
                    backoff_waited=backoff_waited,
                )
            )
            return response