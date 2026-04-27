"""
backends/base.py — The EmissionBackend protocol.

Every observability backend implements this protocol. The emit layer
(emit.py) calls these methods; the backend decides where the data goes.
This is the same pattern as the Module 7 Exercise 7.2 provider
abstraction — a protocol that decouples the calling code from the
destination, justified by testability rather than speculative flexibility.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Protocol, Any


@dataclass
class RoutingEvent:
    """A single routing decision with all its observability data.

    Every field is populated by the router or the eval harness before
    emission. The backend receives this and decides how to persist it.
    """

    # --- Identity ---
    trace_id: str                  # unique per top-level request
    query: str                     # the user's input
    query_class: str               # easy / medium / hard

    # --- Routing decision ---
    model: str                     # which model handled it
    routing_decision: str          # why: "policy_match", "escalation", "default"

    # --- Measurements ---
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0

    # --- Output ---
    answer: str = ""

    # --- Quality (optional — filled by eval harness) ---
    quality_score: float | None = None
    quality_comment: str = ""

    # --- Metadata ---
    timestamp: str = ""            # ISO 8601, set by emit layer
    session_id: str = ""           # groups related requests
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


class EmissionBackend(Protocol):
    """Protocol for observability backends.

    Implement `emit` and `flush`. That's it. Adding a new backend
    (Helicone, Honeycomb, Braintrust) should be under 30 lines.
    """

    def emit(self, event: RoutingEvent) -> None:
        """Send a single routing event to the backend."""
        ...

    def flush(self) -> None:
        """Ensure all buffered events are persisted.

        Called at the end of a run. Backends that send events
        synchronously can no-op here.
        """
        ...