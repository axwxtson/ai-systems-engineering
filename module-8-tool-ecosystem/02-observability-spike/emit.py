"""
emit.py — The backend-agnostic emission interface.

This module owns the contract between the router and the observability
backend. The router calls emit_event(); this module stamps it with a
timestamp and forwards to whichever backend is active.

The pattern: the emit layer is yours, the backend is swappable. You
should be able to add a Helicone or Honeycomb backend in under 30 lines
by implementing the EmissionBackend protocol.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backends.base import EmissionBackend, RoutingEvent


class Emitter:
    """Wraps a backend and handles timestamp injection."""

    def __init__(self, backend: EmissionBackend) -> None:
        self._backend = backend

    def emit(self, event: RoutingEvent) -> None:
        """Stamp the event with a timestamp and forward to the backend."""
        if not event.timestamp:
            event.timestamp = datetime.now(timezone.utc).isoformat()
        self._backend.emit(event)

    def flush(self) -> None:
        """Forward flush to the backend."""
        self._backend.flush()

    @property
    def backend_name(self) -> str:
        return type(self._backend).__name__