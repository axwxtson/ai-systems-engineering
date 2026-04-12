"""Failure taxonomy and retry logic for the fallback chain.

The chain needs to know, for every exception a provider raises, two things:

1. Is this failure *retryable* on the same link, or should we fall over to
   the next link immediately?
2. If retryable, how long should we wait before retrying?

This module defines the typed failure hierarchy, the classification rules,
and the backoff calculator. The chain itself (chain.py) just asks:

    action = classify(exception)
    if action.retryable:
        time.sleep(backoff(attempt, retry_after))
        retry
    else:
        fall over to next link

Design notes:

- We define our own exception hierarchy rather than propagating Anthropic SDK
  exceptions everywhere. Reason: the chain works across providers, and each
  provider has its own exception types. The AnthropicProvider (and any future
  provider) should translate SDK exceptions into these types at the provider
  boundary, so the chain only ever deals with the unified hierarchy.
- The classification table is explicit and in one place. Adding a new failure
  mode means adding a new class here and one branch in `classify()`. No
  scattered `isinstance` checks in the chain.
- Backoff is exponential with jitter, bounded, and respects Retry-After if
  present. Three rules from the reference doc.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# The failure hierarchy
# ---------------------------------------------------------------------------


class ProviderError(Exception):
    """Base class for all provider failures the chain knows about.

    Any exception raised by a provider that isn't a subclass of this is
    treated as an unknown failure and triggers a fall-over with no retry.
    That's the safe default: better to fall over on a mystery error than to
    retry it blindly.
    """

    def __init__(self, message: str, retry_after_seconds: float | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class RateLimitError(ProviderError):
    """HTTP 429 — the server is telling us to slow down.

    Retryable with backoff. If a Retry-After hint is present, honour it
    rather than using exponential backoff.
    """


class ServerError(ProviderError):
    """HTTP 5xx — the provider is having a bad day.

    Retryable with backoff.
    """


class TimeoutError_(ProviderError):
    """The call took longer than the link's timeout budget.

    NOT retryable on the same link. If a model didn't respond within its
    allocated window, retrying the same model rarely helps — the more useful
    action is to fall over to a faster or different model. Suffix underscore
    on the class name to avoid shadowing the builtin `TimeoutError`.
    """


class RefusalError(ProviderError):
    """The model refused to answer the query.

    NOT retryable on the same link (the same model will refuse again — the
    refusal is a property of the model's training, not a transient condition).
    Falls over to the next link, which uses a different model that may or may
    not refuse the same query. If the whole chain refuses, the user-facing
    answer is "this system cannot answer that query" — which is the right
    outcome for inputs that genuinely should be refused.

    Detecting a refusal is a separate concern from raising this error —
    providers or the chain wrap a successful response with a refusal check
    and raise this if the response looks like a refusal.
    """


class MalformedOutputError(ProviderError):
    """The model returned output that failed validation (bad JSON, missing
    required structure, length below minimum).

    Retryable *once* on the same link — sometimes the next sample from the
    same model will be well-formed — then falls over. More than one retry on
    this error is wasteful.
    """


class ClientError(ProviderError):
    """HTTP 4xx (not 429) — the request itself is broken.

    NOT retryable and does NOT fall over. This is our bug: malformed request,
    invalid auth, missing field. Retrying just hammers the API with the same
    broken call; falling over would mask the bug. The chain raises this
    straight through so the caller fixes their code.
    """


class UnknownProviderError(ProviderError):
    """A provider raised an exception the chain doesn't recognise.

    Treated as a non-retryable fall-over — better to try the next link than
    to retry a mystery condition. Logged prominently so the operator can
    add explicit handling for the new failure mode.
    """


# ---------------------------------------------------------------------------
# Classification — what do we do with each failure type?
# ---------------------------------------------------------------------------


class FailureAction(Enum):
    """What the chain should do when it sees a particular failure."""

    RETRY = "retry"          # retry on the same link with backoff
    FALL_OVER = "fall_over"  # skip retries, go to the next link
    RAISE = "raise"          # propagate immediately; do not fall over


@dataclass
class FailurePolicy:
    """Per-failure-type policy: retry count and what to do after retries."""

    action: FailureAction
    max_retries: int = 0  # only meaningful when action == RETRY

    @property
    def retryable(self) -> bool:
        return self.action == FailureAction.RETRY and self.max_retries > 0


# The classification table. One place to look up "what should I do with a
# <ThingError>?" — no scattered isinstance checks elsewhere.
#
# Note the explicit distinction between max_retries=2 (up to 2 retries, then
# fall over) and max_retries=1 (exactly one retry, then fall over).
# MalformedOutputError gets 1 because retrying is cheap and sometimes works
# but two retries rarely add value over one.
_CLASSIFICATION: dict[type, FailurePolicy] = {
    RateLimitError: FailurePolicy(action=FailureAction.RETRY, max_retries=2),
    ServerError: FailurePolicy(action=FailureAction.RETRY, max_retries=2),
    MalformedOutputError: FailurePolicy(action=FailureAction.RETRY, max_retries=1),
    TimeoutError_: FailurePolicy(action=FailureAction.FALL_OVER),
    RefusalError: FailurePolicy(action=FailureAction.FALL_OVER),
    UnknownProviderError: FailurePolicy(action=FailureAction.FALL_OVER),
    ClientError: FailurePolicy(action=FailureAction.RAISE),
}


def classify(exc: BaseException) -> FailurePolicy:
    """Look up the policy for a given exception.

    Unknown exception types fall through to a safe default: fall over to the
    next link. This is deliberate — the chain should not retry mystery errors,
    but also should not crash the whole request because the operator hasn't
    yet added handling for a new failure mode.
    """
    for exc_type, policy in _CLASSIFICATION.items():
        if isinstance(exc, exc_type):
            return policy
    # Anything not in the table: fall over without retrying.
    return FailurePolicy(action=FailureAction.FALL_OVER)


# ---------------------------------------------------------------------------
# Backoff calculator
# ---------------------------------------------------------------------------


def backoff_seconds(
    attempt: int,
    base: float = 1.0,
    cap: float = 30.0,
    jitter: float = 0.25,
    retry_after: float | None = None,
) -> float:
    """Exponential backoff with jitter, bounded by `cap`.

    Args:
        attempt: 0-indexed retry attempt (0 = first retry, 1 = second, ...)
        base: the initial wait time in seconds
        cap: maximum wait time; the exponential growth is clipped here
        jitter: +/- fraction to randomly perturb the wait by (0.25 = ±25%)
        retry_after: if the server told us exactly when to come back, honour
            it and skip the exponential calculation entirely

    Why jitter matters: without it, many clients that all hit a rate limit
    at the same moment will all retry at the same moment, producing a
    second rate-limit spike. Randomising the wait spreads the retries so
    the server's rate limiter cools down naturally.

    Why cap matters: exponential backoff grows fast. 2^10 seconds is 17 minutes.
    For a user-facing request, any wait over 30 seconds is effectively a
    failure anyway — the cap prevents the retry logic from inadvertently
    taking longer than the original request would have.
    """
    if retry_after is not None and retry_after > 0:
        # Server knows best. Still add a small random component so many clients
        # don't all come back at exactly the same tick.
        return retry_after + random.uniform(0, jitter)

    raw = base * (2 ** attempt)
    bounded = min(raw, cap)
    # Symmetric jitter around the bounded value.
    spread = bounded * jitter
    return max(0.0, bounded + random.uniform(-spread, spread))


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print("Failures module smoke test")
    print("=" * 50)

    # Classification
    print("\nClassification:")
    samples = [
        RateLimitError("slow down", retry_after_seconds=2.5),
        ServerError("503 bad gateway"),
        TimeoutError_("deadline exceeded"),
        RefusalError("I cannot comply with that request"),
        MalformedOutputError("missing required field 'answer'"),
        ClientError("400: bad request schema"),
        ValueError("random non-provider exception"),  # unknown type
    ]
    for exc in samples:
        policy = classify(exc)
        print(
            f"  {type(exc).__name__:22s}  action={policy.action.value:10s}  "
            f"retries={policy.max_retries}  retryable={policy.retryable}"
        )

    # Backoff
    print("\nBackoff schedule (base=1.0, cap=30.0, jitter=0.25):")
    for attempt in range(5):
        wait = backoff_seconds(attempt, base=1.0, cap=30.0, jitter=0.25)
        print(f"  attempt {attempt}: {wait:.2f}s")

    print("\nBackoff with Retry-After hint (server says 4.0s):")
    for _ in range(3):
        wait = backoff_seconds(0, retry_after=4.0)
        print(f"  {wait:.2f}s (should be ~4.0-4.25s)")

    print("\nOK")