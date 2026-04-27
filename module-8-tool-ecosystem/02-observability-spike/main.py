"""
main.py — CLI for the observability spike.

Runs the router against 6 test queries, optionally evaluates each
output with the eval harness, and emits all events through the
chosen backend.

Usage:
  PYTHONPATH=$(pwd) python3 main.py                        # stdout, no judge
  PYTHONPATH=$(pwd) python3 main.py --backend stdout       # explicit stdout
  PYTHONPATH=$(pwd) python3 main.py --backend langfuse     # push to Langfuse
  PYTHONPATH=$(pwd) python3 main.py --judge                # enable LLM-as-judge
  PYTHONPATH=$(pwd) python3 main.py --pretty                # pretty-print JSON (stdout only)
"""

from __future__ import annotations

import argparse
import sys

from colorama import Fore, Style, init as colorama_init

from backends.stdout import StdoutBackend
from backends.base import RoutingEvent
from emit import Emitter
from router import Router, TEST_QUERIES, TestQuery
from eval_harness import evaluate


def colour_score(score: float) -> str:
    """Colour a quality score green/yellow/red."""
    if score >= 0.8:
        return f"{Fore.GREEN}{score:.3f}{Style.RESET_ALL}"
    elif score >= 0.5:
        return f"{Fore.YELLOW}{score:.3f}{Style.RESET_ALL}"
    else:
        return f"{Fore.RED}{score:.3f}{Style.RESET_ALL}"


def colour_model(model: str) -> str:
    """Colour model name by tier."""
    if "haiku" in model:
        return f"{Fore.CYAN}{model}{Style.RESET_ALL}"
    elif "sonnet" in model:
        return f"{Fore.BLUE}{model}{Style.RESET_ALL}"
    elif "opus" in model:
        return f"{Fore.MAGENTA}{model}{Style.RESET_ALL}"
    return model


def print_banner() -> None:
    print()
    print("=" * 78)
    print(" EXERCISE 8.2: OBSERVABILITY SPIKE ".center(78, "="))
    print("=" * 78)
    print()
    print("Wire a simplified Module 7 router into an observability backend.")
    print(f"Test queries: {len(TEST_QUERIES)}")
    print()


def print_event_summary(event: RoutingEvent, tq: TestQuery) -> None:
    """Print a coloured summary of a single routing event."""
    print(f"  [{tq.id}] ({tq.query_class})")
    print(f"    Query:    {tq.query[:70]}{'...' if len(tq.query) > 70 else ''}")
    print(f"    Model:    {colour_model(event.model)}")
    print(f"    Decision: {event.routing_decision}")
    print(f"    Tokens:   {event.input_tokens} in / {event.output_tokens} out")
    print(f"    Latency:  {event.latency_ms:.0f}ms")
    print(f"    Cost:     ${event.cost_usd:.6f}")
    if event.quality_score is not None:
        print(f"    Quality:  {colour_score(event.quality_score)}")
        print(f"    Comment:  {event.quality_comment}")
    answer_preview = event.answer[:120].replace("\n", " ")
    print(f"    Answer:   {answer_preview}{'...' if len(event.answer) > 120 else ''}")
    print()


def print_summary_table(events: list[RoutingEvent]) -> None:
    """Print a summary table of all events."""
    print()
    print("=" * 78)
    print(" SUMMARY ".center(78, "="))
    print("=" * 78)
    print()

    total_cost = sum(e.cost_usd for e in events)
    total_input = sum(e.input_tokens for e in events)
    total_output = sum(e.output_tokens for e in events)
    avg_latency = sum(e.latency_ms for e in events) / len(events) if events else 0

    print(f"  Total cost:     ${total_cost:.6f}")
    print(f"  Total tokens:   {total_input} in / {total_output} out")
    print(f"  Avg latency:    {avg_latency:.0f}ms")

    scored = [e for e in events if e.quality_score is not None]
    if scored:
        avg_quality = sum(e.quality_score for e in scored) / len(scored)
        print(f"  Avg quality:    {colour_score(avg_quality)}")

    # Per-model breakdown
    models_used = set(e.model for e in events)
    print()
    print("  Per-model breakdown:")
    for model in sorted(models_used):
        model_events = [e for e in events if e.model == model]
        m_cost = sum(e.cost_usd for e in model_events)
        m_count = len(model_events)
        m_scored = [e for e in model_events if e.quality_score is not None]
        m_quality = (
            sum(e.quality_score for e in m_scored) / len(m_scored)
            if m_scored else None
        )
        quality_str = colour_score(m_quality) if m_quality is not None else "n/a"
        print(
            f"    {colour_model(model):40s}  "
            f"calls={m_count}  cost=${m_cost:.6f}  quality={quality_str}"
        )

    print()


def create_backend(backend_name: str, pretty: bool = False):
    """Factory: create the appropriate backend."""
    if backend_name == "stdout":
        return StdoutBackend(pretty=pretty)
    elif backend_name == "langfuse":
        from backends.langfuse_backend import LangfuseBackend
        return LangfuseBackend()
    else:
        print(f"Unknown backend: {backend_name}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    colorama_init()

    parser = argparse.ArgumentParser(description="Exercise 8.2: Observability Spike")
    parser.add_argument(
        "--backend",
        choices=["stdout", "langfuse"],
        default="stdout",
        help="Observability backend (default: stdout)",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Enable LLM-as-judge quality scoring (adds ~6 Haiku calls)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON events (stdout backend only)",
    )
    parser.add_argument(
        "--no-eval",
        action="store_true",
        help="Skip all quality evaluation (emit raw routing events only)",
    )
    args = parser.parse_args()

    print_banner()

    # 1. Create backend and emitter
    backend = create_backend(args.backend, pretty=args.pretty)
    emitter = Emitter(backend)
    print(f"Backend: {emitter.backend_name}")
    print()

    # 2. Create router
    router = Router(emitter=emitter)

    # 3. Route all queries (events are emitted inside router.route())
    print("-" * 78)
    print(" ROUTING QUERIES ".center(78, "-"))
    print("-" * 78)
    print()

    events: list[RoutingEvent] = []
    for tq in TEST_QUERIES:
        event = router.route(tq)

        # 4. Optionally evaluate
        if not args.no_eval:
            event = evaluate(event, tq, use_judge=args.judge)
            # Re-emit with quality score if using Langfuse
            # (stdout already emitted in router.route(), so we print
            #  the quality score in the summary instead)

        events.append(event)
        print_event_summary(event, tq)

    # 5. Flush
    emitter.flush()

    # 6. Summary
    print_summary_table(events)

    print(f"Events emitted: {backend.event_count}")
    if args.backend == "langfuse":
        print("Check your Langfuse project dashboard for traces.")
    print()


if __name__ == "__main__":
    main()