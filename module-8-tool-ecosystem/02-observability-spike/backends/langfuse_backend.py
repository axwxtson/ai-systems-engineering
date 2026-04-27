"""
backends/langfuse_backend.py — Pushes routing events to Langfuse.

Uses the Langfuse Python SDK v3 (OpenTelemetry-based). Each routing
event becomes a trace with a generation span inside it. Quality scores
are attached to the trace via create_score().

Setup:
  export LANGFUSE_SECRET_KEY="sk-lf-..."
  export LANGFUSE_PUBLIC_KEY="pk-lf-..."
  # Langfuse Cloud (EU default):
  export LANGFUSE_HOST="https://cloud.langfuse.com"
  # US region:
  # export LANGFUSE_HOST="https://us.cloud.langfuse.com"
"""

from __future__ import annotations

import os
import sys

from backends.base import RoutingEvent


def _check_langfuse_available() -> bool:
    try:
        import langfuse  # noqa: F401
        return True
    except ImportError:
        return False


class LangfuseBackend:
    """Pushes routing events to a Langfuse project.

    Each RoutingEvent maps to:
    - One Langfuse trace (the top-level routing decision)
    - One generation span inside the trace (the LLM call)
    - One score on the trace (the quality score, if present)
    """

    def __init__(self) -> None:
        if not _check_langfuse_available():
            print(
                "ERROR: langfuse package not installed. "
                "Run: pip3 install langfuse>=3.0.0 --break-system-packages",
                file=sys.stderr,
            )
            raise ImportError("langfuse not installed")

        # Check env vars
        required = ["LANGFUSE_SECRET_KEY", "LANGFUSE_PUBLIC_KEY"]
        missing = [k for k in required if not os.environ.get(k)]
        if missing:
            print(
                f"ERROR: Missing env vars: {', '.join(missing)}. "
                "See README for Langfuse setup.",
                file=sys.stderr,
            )
            raise EnvironmentError(f"Missing: {', '.join(missing)}")

        from langfuse import get_client
        self._client = get_client()
        self._count = 0

    def emit(self, event: RoutingEvent) -> None:
        """Create a Langfuse trace + generation for this routing event."""

        # Create a trace for the routing decision
        with self._client.start_as_current_observation(
            as_type="span",
            name=f"route:{event.query_class}",
        ) as trace_span:
            # Set trace-level attributes
            trace_span.update(
                input={"query": event.query, "query_class": event.query_class},
                output={"answer": event.answer[:500]},  # truncate for Langfuse UI
                metadata={
                    "routing_decision": event.routing_decision,
                    "model": event.model,
                    "cost_usd": event.cost_usd,
                    "latency_ms": event.latency_ms,
                },
            )

            # Set trace-level IO for eval features
            trace_span.set_trace_io(
                input={"query": event.query, "query_class": event.query_class},
                output={"answer": event.answer[:500]},
            )

            # Propagate session and tags
            from langfuse import propagate_attributes
            with propagate_attributes(
                session_id=event.session_id or "default",
                tags=event.tags or [event.query_class],
            ):
                # Create a generation span for the LLM call
                with self._client.start_as_current_observation(
                    as_type="generation",
                    name=f"llm:{event.model}",
                    model=event.model,
                    input=[{"role": "user", "content": event.query}],
                ) as gen:
                    gen.update(
                        output=event.answer[:500],
                        usage_details={
                            "input": event.input_tokens,
                            "output": event.output_tokens,
                        },
                        metadata={
                            "latency_ms": event.latency_ms,
                            "cost_usd": event.cost_usd,
                        },
                    )

            # Attach quality score if present
            if event.quality_score is not None:
                trace_span.score_trace(
                    name="quality",
                    value=event.quality_score,
                    data_type="NUMERIC",
                    comment=event.quality_comment or None,
                )

        self._count += 1

    def flush(self) -> None:
        """Flush the Langfuse client to ensure all events are sent."""
        self._client.flush()

    @property
    def event_count(self) -> int:
        return self._count