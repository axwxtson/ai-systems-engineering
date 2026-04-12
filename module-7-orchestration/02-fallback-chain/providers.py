"""Provider abstraction layer.

The rest of this exercise never calls the Anthropic SDK directly. It calls
`provider.complete(request)` and gets back a `CompletionResponse`. That
indirection buys three things:

1. **Testability.** MockProvider lets us script failures and canned responses
   so the fallback chain can be verified deterministically, without spending
   a penny on the API.
2. **Swap-ability.** Adding a second real provider (OpenAI, a local model, a
   new Anthropic beta endpoint) is one new class implementing the same protocol.
3. **A clean failure surface.** Every provider call raises exceptions from
   the same taxonomy (see failures.py in Step 2), so the chain can reason
   about failures uniformly.

This is the module-7 concept 7 pattern. We are deliberately building the
abstraction here because we're about to build a multi-provider system (chain
of real + mock) and the abstraction pays for itself immediately.

Design choices:

- `CompletionRequest` mirrors the Anthropic messages.create surface closely
  enough that the AnthropicProvider is a thin wrapper, but doesn't leak SDK
  types. Provider-specific features (prompt caching, extended thinking) would
  go in as optional fields — none in scope for this exercise.
- `CompletionResponse` is the normalised output shape. The raw SDK response
  is kept in the `raw` field for debugging but the chain never reads it.
- Providers raise standard Python exceptions for now. Step 2 replaces these
  with a typed failure hierarchy that the chain can classify.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import anthropic


# ---------------------------------------------------------------------------
# Request / Response dataclasses — the normalised interface
# ---------------------------------------------------------------------------


@dataclass
class CompletionRequest:
    """A provider-agnostic completion request.

    Mirrors the shape of Anthropic's messages.create() call closely, but does
    not import or reference any SDK types. A second provider (OpenAI, local
    model) implements its own translation from this shape.
    """

    messages: list[dict]
    model: str
    max_tokens: int = 1024
    system: str | None = None
    temperature: float | None = None
    # Not in scope for 7.2, but the fields exist so downstream code doesn't
    # need to grow to support them:
    tools: list[dict] | None = None


@dataclass
class CompletionResponse:
    """A provider-agnostic completion response.

    The `raw` field carries the original SDK response object for debugging.
    The chain itself should never read `raw` — if it does, that's a sign the
    abstraction is leaking.
    """

    text: str
    model_used: str
    input_tokens: int
    output_tokens: int
    stop_reason: str
    latency_seconds: float
    raw: Any = None


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------


class LLMProvider(Protocol):
    """Every provider exposes the same one-method interface.

    Implementations may raise exceptions to signal failure. In Step 1 these
    are plain Python exceptions; Step 2 introduces a typed hierarchy so the
    fallback chain can classify failures correctly.
    """

    def complete(self, request: CompletionRequest) -> CompletionResponse: ...


# ---------------------------------------------------------------------------
# Real provider — thin wrapper over the Anthropic SDK
# ---------------------------------------------------------------------------


class AnthropicProvider:
    """Wraps the Anthropic Messages API behind the LLMProvider protocol.

    The wrapper is intentionally minimal: it translates request fields into
    SDK kwargs, calls `messages.create`, and unwraps the response. Anything
    more (retries, caching, observability) belongs in the layer above.
    """

    def __init__(self, api_key: str | None = None, client: anthropic.Anthropic | None = None):
        # Allow injecting a client for testing; otherwise construct one from env.
        self.client = client or anthropic.Anthropic(api_key=api_key)

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        kwargs: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": request.messages,
        }
        if request.system is not None:
            kwargs["system"] = request.system
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.tools:
            kwargs["tools"] = request.tools

        start = time.perf_counter()
        raw = self.client.messages.create(**kwargs)
        elapsed = time.perf_counter() - start

        text = "".join(
            block.text for block in raw.content if getattr(block, "type", None) == "text"
        ).strip()

        return CompletionResponse(
            text=text,
            model_used=raw.model,
            input_tokens=raw.usage.input_tokens,
            output_tokens=raw.usage.output_tokens,
            stop_reason=raw.stop_reason or "unknown",
            latency_seconds=elapsed,
            raw=raw,
        )


# ---------------------------------------------------------------------------
# Mock provider — scripted responses and failures for testing the chain
# ---------------------------------------------------------------------------


# Sentinel type returned by a response script to signal "raise this exception
# instead of returning a response." See MockProvider docstring for usage.
@dataclass
class _Raise:
    exception: BaseException


def raise_(exc: BaseException) -> _Raise:
    """Helper for scripting a failure in a MockProvider response list.

    Usage:
        provider = MockProvider(responses=[
            raise_(TimeoutError("deadline")),
            CompletionResponse(text="hello", ...),
        ])

    The first call raises TimeoutError; the second returns a real response.
    """
    return _Raise(exc)


class MockProvider:
    """Scripted provider for deterministic testing of the fallback chain.

    Two usage modes, pick one:

    **Response list mode** — pass a list of responses (or `_Raise` sentinels)
    and each call pops the next one:

        mock = MockProvider(responses=[
            raise_(RateLimitError("slow down")),
            raise_(RateLimitError("slow down")),
            CompletionResponse(text="finally", ...),
        ])

        # First two calls raise; third returns the real response.

    **Handler mode** — pass a callable that takes the request and returns a
    response (or raises):

        def handler(req):
            if "opus" in req.model:
                raise TimeoutError("slow model")
            return CompletionResponse(text="fast path", ...)

        mock = MockProvider(handler=handler)

    Handler mode is useful when the mock behaviour depends on the request
    content (e.g., "always fail on this model, always succeed on that one").
    List mode is useful when you want to script a sequence of outcomes
    independent of request content.

    Every call is logged in `call_log` so tests can assert on what the chain
    actually called and in what order.
    """

    def __init__(
        self,
        responses: list[CompletionResponse | _Raise] | None = None,
        handler: Callable[[CompletionRequest], CompletionResponse | _Raise] | None = None,
        default_latency: float = 0.01,
    ):
        if responses is not None and handler is not None:
            raise ValueError("MockProvider: pass either responses or handler, not both.")
        if responses is None and handler is None:
            raise ValueError("MockProvider: must pass responses or handler.")

        self.responses = list(responses) if responses is not None else None
        self.handler = handler
        self.default_latency = default_latency
        self.call_log: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.call_log.append(request)

        if self.handler is not None:
            result = self.handler(request)
        else:
            if not self.responses:
                raise RuntimeError(
                    "MockProvider: response list exhausted. "
                    "The chain made more calls than the test scripted for."
                )
            result = self.responses.pop(0)

        # Simulate a small wall-clock so latency measurements are non-zero
        time.sleep(self.default_latency)

        if isinstance(result, _Raise):
            raise result.exception

        # Fill in latency if the scripted response didn't specify one.
        if result.latency_seconds == 0.0:
            result.latency_seconds = self.default_latency
        return result

    @property
    def call_count(self) -> int:
        return len(self.call_log)

    def assert_called_with_model(self, model: str, call_index: int = -1) -> None:
        """Assert that the most recent (or indexed) call used the given model."""
        if not self.call_log:
            raise AssertionError(f"Expected call to {model}, but no calls were made.")
        actual = self.call_log[call_index].model
        if actual != model:
            raise AssertionError(
                f"Expected call [{call_index}] to use model {model}, got {actual}."
            )


# ---------------------------------------------------------------------------
# Smoke test — run `python3 providers.py` to verify both providers are wired up
# ---------------------------------------------------------------------------


def _make_canned_response(text: str, model: str = "mock-model-1") -> CompletionResponse:
    return CompletionResponse(
        text=text,
        model_used=model,
        input_tokens=10,
        output_tokens=len(text.split()),
        stop_reason="end_turn",
        latency_seconds=0.0,
    )


def _smoke_test_mock() -> None:
    print("  MockProvider — list mode")
    mock = MockProvider(
        responses=[
            _make_canned_response("first"),
            raise_(RuntimeError("simulated failure")),
            _make_canned_response("third"),
        ]
    )
    req = CompletionRequest(messages=[{"role": "user", "content": "hi"}], model="test")

    r1 = mock.complete(req)
    assert r1.text == "first", f"expected 'first', got {r1.text!r}"

    try:
        mock.complete(req)
    except RuntimeError as e:
        assert "simulated failure" in str(e)
    else:
        raise AssertionError("expected RuntimeError from mock")

    r3 = mock.complete(req)
    assert r3.text == "third"
    assert mock.call_count == 3
    print("    ok — 3 calls, 1 failure, 2 responses")

    print("  MockProvider — handler mode")
    def handler(r: CompletionRequest) -> CompletionResponse:
        if r.model == "fast":
            return _make_canned_response("fast reply", model="fast")
        raise TimeoutError(f"model {r.model} too slow")

    mock2 = MockProvider(handler=handler)
    r_fast = mock2.complete(CompletionRequest(messages=[{"role": "user", "content": "x"}], model="fast"))
    assert r_fast.text == "fast reply"

    try:
        mock2.complete(CompletionRequest(messages=[{"role": "user", "content": "x"}], model="slow"))
    except TimeoutError:
        pass
    else:
        raise AssertionError("expected TimeoutError")
    print("    ok — handler routes by request content")


def _smoke_test_anthropic() -> None:
    """Live API smoke test. Only runs if ANTHROPIC_API_KEY is set."""
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("  AnthropicProvider — skipped (no ANTHROPIC_API_KEY set)")
        return

    print("  AnthropicProvider — live API call")
    provider = AnthropicProvider()
    req = CompletionRequest(
        messages=[{"role": "user", "content": "Say 'pong' and nothing else."}],
        model="claude-haiku-4-5-20251001",
        max_tokens=20,
    )
    response = provider.complete(req)
    assert response.text, "expected non-empty response"
    assert response.input_tokens > 0
    assert response.output_tokens > 0
    assert response.latency_seconds > 0
    print(
        f"    ok — '{response.text[:40]}' "
        f"({response.input_tokens}in / {response.output_tokens}out, "
        f"{response.latency_seconds:.2f}s)"
    )


def _smoke_test_interchangeability() -> None:
    """Prove both providers are interchangeable behind the protocol.

    A function typed against LLMProvider should accept either without knowing
    which one it got.
    """
    print("  Interchangeability — function accepts any LLMProvider")

    def use_any_provider(provider: LLMProvider, req: CompletionRequest) -> str:
        return provider.complete(req).text

    mock = MockProvider(responses=[_make_canned_response("mock says hi")])
    req = CompletionRequest(messages=[{"role": "user", "content": "hi"}], model="test")
    result = use_any_provider(mock, req)
    assert result == "mock says hi"
    print("    ok — LLMProvider protocol works structurally")


if __name__ == "__main__":
    print("Provider abstraction smoke test")
    print("=" * 50)
    _smoke_test_mock()
    _smoke_test_anthropic()
    _smoke_test_interchangeability()
    print("\nAll smoke tests passed.")