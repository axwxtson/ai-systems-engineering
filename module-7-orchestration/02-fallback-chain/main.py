"""Exercise 7.2 — Fallback Chain CLI (Step 2: real-API runner)

Runs a small set of queries through a Haiku → Sonnet → Opus fallback chain
using the real Anthropic API. All links succeed under normal conditions, so
this run mainly verifies:

  - The chain executes against a real provider
  - Success is recorded on the cheapest (first) link
  - Per-link observability metrics are computed correctly
  - ChainResult traces contain the expected attempts

Step 3 adds the failure injection harness that actually stresses the
fall-over behaviour. For Step 2, we're establishing that the happy path
works end-to-end before anything fails on purpose.

Run from this directory with:
    PYTHONPATH=$(pwd) python3 main.py
"""

import json
import sys
from dataclasses import asdict

from colorama import Fore, Style, init

from chain import ChainExhaustedError, ChainResult, FallbackChain, Link
from observability import aggregate, format_report
from providers import AnthropicProvider, CompletionRequest


init(autoreset=True)


# Small set of queries — we are testing the chain, not quality.
QUERIES = [
    "What is a stablecoin in one sentence?",
    "Define 'yield curve inversion' in one sentence.",
    "Name one use case for prompt caching in LLM applications.",
    "In one sentence, what does 'slippage' mean in trading?",
    "Give one reason why BTC and ETH prices often move together.",
]


def header(text: str) -> None:
    bar = "=" * 60
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{bar}")
    print(f"{text}")
    print(f"{bar}{Style.RESET_ALL}")


def subheader(text: str) -> None:
    print(f"\n{Fore.CYAN}{text}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'-' * len(text)}{Style.RESET_ALL}")


def green(text: str) -> str:
    return f"{Fore.GREEN}{text}{Style.RESET_ALL}"


def yellow(text: str) -> str:
    return f"{Fore.YELLOW}{text}{Style.RESET_ALL}"


def red(text: str) -> str:
    return f"{Fore.RED}{text}{Style.RESET_ALL}"


def describe_attempt_line(idx: int, total: int, query: str, result: ChainResult) -> str:
    query_short = query[:40] + ("..." if len(query) > 40 else "")
    if result.exhausted:
        status = red("EXHAUSTED")
    else:
        status = green(f"{result.final_model}")
    return (
        f"  [{idx:2d}/{total:2d}]  {query_short:43s}  "
        f"{status}  links_tried={result.links_tried}  "
        f"attempts={len(result.attempts)}  {result.total_latency_seconds:.2f}s"
    )


def print_trace(result: ChainResult) -> None:
    """Per-attempt breakdown for a single chain execution."""
    for a in result.attempts:
        status = green("ok") if a.success else red("fail")
        retry_note = f" retry#{a.attempt_number}" if a.attempt_number > 0 else ""
        backoff_note = f" (waited {a.backoff_waited:.2f}s)" if a.backoff_waited > 0 else ""
        error_note = f" {a.error_type}: {a.error_message}" if not a.success else ""
        print(
            f"      link{a.link_index} {a.model}{retry_note}  "
            f"{status}  {a.latency_seconds:.2f}s{backoff_note}{error_note}"
        )


def main() -> int:
    header("Exercise 7.2 — Fallback Chain (Step 2, real API)")
    print(f"Queries: {len(QUERIES)}")

    provider = AnthropicProvider()
    chain = FallbackChain(
        [
            Link(provider=provider, model="claude-haiku-4-5-20251001", timeout_seconds=10.0),
            Link(provider=provider, model="claude-sonnet-4-6",          timeout_seconds=20.0),
            Link(provider=provider, model="claude-opus-4-6",            timeout_seconds=40.0),
        ]
    )
    print(f"Chain: {' → '.join(l.model for l in chain.links)}")

    subheader("Running queries")
    results: list[ChainResult] = []
    for i, query in enumerate(QUERIES, start=1):
        request = CompletionRequest(
            messages=[{"role": "user", "content": query}],
            model="",  # overridden per-link
            max_tokens=100,
        )

        try:
            result = chain.execute(request)
        except ChainExhaustedError as e:
            # Should not happen under normal conditions — chain.execute only
            # raises on ClientError. But handle it gracefully.
            print(red(f"  Chain exhausted: {e}"))
            return 1

        results.append(result)
        print(describe_attempt_line(i, len(QUERIES), query, result))
        # For Step 2, print the trace only if something unusual happened
        # (more than one attempt or the chain exhausted).
        if len(result.attempts) > 1 or result.exhausted:
            print_trace(result)

    # Aggregate and report.
    subheader("Observability report")
    metrics = aggregate(results)
    print(format_report(metrics))

    # Sanity checks — what we expect on a clean run.
    subheader("Verdict")
    expected_first_link = chain.links[0].model
    all_on_first = all(
        not r.exhausted and r.final_model == expected_first_link for r in results
    )
    if all_on_first:
        print(green("  All requests satisfied by link 0 (expected on a clean API day)."))
    else:
        # Not a failure — real APIs have genuine incidents — but worth flagging.
        print(yellow("  Some requests escalated past link 0. Inspect per-link metrics."))

    if metrics.exhausted_requests > 0:
        print(red(f"  {metrics.exhausted_requests} request(s) exhausted the chain."))
        return 1

    # Save the raw traces for Step 3 to compare against.
    out = {
        "chain": [l.model for l in chain.links],
        "results": [
            {
                "query": q,
                "final_model": r.final_model,
                "exhausted": r.exhausted,
                "total_latency": r.total_latency_seconds,
                "attempts": [
                    {
                        "link_index": a.link_index,
                        "model": a.model,
                        "attempt_number": a.attempt_number,
                        "success": a.success,
                        "latency_seconds": a.latency_seconds,
                        "error_type": a.error_type,
                        "error_message": a.error_message,
                        "backoff_waited": a.backoff_waited,
                    }
                    for a in r.attempts
                ],
            }
            for q, r in zip(QUERIES, results)
        ],
        "metrics": {
            "total_requests": metrics.total_requests,
            "successful_requests": metrics.successful_requests,
            "exhausted_requests": metrics.exhausted_requests,
            "success_rate": metrics.success_rate,
            "exhaustion_rate": metrics.exhaustion_rate,
            "mean_latency": metrics.mean_latency,
            "per_link": {
                str(idx): {
                    "model": m.model,
                    "reached": m.reached,
                    "succeeded": m.succeeded,
                    "fell_over": m.fell_over,
                    "success_rate": m.success_rate,
                    "fallback_rate": m.fallback_rate,
                    "total_retries": m.total_retries,
                    "total_latency": m.total_latency,
                    "total_backoff": m.total_backoff,
                }
                for idx, m in metrics.per_link.items()
            },
        },
    }
    with open("results.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n  Raw traces saved to results.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())