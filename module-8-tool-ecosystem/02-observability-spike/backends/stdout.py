"""
backends/stdout.py — Prints structured JSON events to stdout.

The default backend. Works without any external dependencies. Useful for:
1. Proving the abstraction works before wiring up Langfuse.
2. Demoing the observability layer in an interview without needing
   a Langfuse account to load.
3. Piping output to jq for ad-hoc analysis.
"""

from __future__ import annotations

import json
import sys

from backends.base import EmissionBackend, RoutingEvent


class StdoutBackend:
    """Prints each event as a single-line JSON object to stdout."""

    def __init__(self, pretty: bool = False) -> None:
        self._pretty = pretty
        self._count = 0

    def emit(self, event: RoutingEvent) -> None:
        d = event.to_dict()
        if self._pretty:
            line = json.dumps(d, indent=2, default=str)
        else:
            line = json.dumps(d, default=str)
        print(line, file=sys.stdout)
        self._count += 1

    def flush(self) -> None:
        # stdout is unbuffered in most terminal contexts; this is a no-op.
        sys.stdout.flush()

    @property
    def event_count(self) -> int:
        return self._count