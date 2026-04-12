"""Observability — aggregate per-link metrics across many chain executions.

The ChainResult from a single execution gives you the attempt trace for that
one request. For a production-useful picture you need to aggregate many
executions and compute:

- **Per-link success rate** — what fraction of requests that reached this link
  were satisfied by it (not falling over).
- **Per-link fallback rate** — what fraction of requests that reached this
  link fell through to the next one. (Equivalent to 1 - success rate when
  success is defined as "returned a response," which is how we define it.)
- **Per-link retry count** — total retries fired on this link across all
  requests. A sustained high retry count is an early warning signal.
- **Per-link latency contribution** — how much of the total end-to-end
  latency was spent on this link (including retries and backoff waits).
- **Chain exhaustion rate** — what fraction of requests exhausted the chain.
  The number you alert on.

The golden rule from the reference doc (Concept 9): fallbacks aren't free.
Track the fallback rate per link and treat any sustained increase as an
incident. Without this data, the chain can silently degrade into expensive
Opus-heavy routing without anyone noticing until the bill arrives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean

from chain import ChainResult


@dataclass
class LinkMetrics:
    """Aggregated metrics for one link across many chain executions."""

    link_index: int
    model: str
    reached: int = 0        # requests where this link was tried at least once
    succeeded: int = 0      # requests where this link returned a response
    fell_over: int = 0      # requests where this link fell over to the next
    total_retries: int = 0  # sum of retries across all reaches
    total_latency: float = 0.0  # sum of latencies across all attempts
    total_backoff: float = 0.0  # sum of backoff waits

    @property
    def success_rate(self) -> float:
        return self.succeeded / self.reached if self.reached else 0.0

    @property
    def fallback_rate(self) -> float:
        return self.fell_over / self.reached if self.reached else 0.0

    @property
    def retries_per_request(self) -> float:
        return self.total_retries / self.reached if self.reached else 0.0


@dataclass
class ChainMetrics:
    """Aggregated metrics for a whole chain across many executions."""

    total_requests: int = 0
    successful_requests: int = 0
    exhausted_requests: int = 0
    total_end_to_end_latency: float = 0.0
    per_link: dict[int, LinkMetrics] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        return self.successful_requests / self.total_requests if self.total_requests else 0.0

    @property
    def exhaustion_rate(self) -> float:
        return self.exhausted_requests / self.total_requests if self.total_requests else 0.0

    @property
    def mean_latency(self) -> float:
        return self.total_end_to_end_latency / self.total_requests if self.total_requests else 0.0


def aggregate(results: list[ChainResult]) -> ChainMetrics:
    """Reduce a list of ChainResults to aggregate metrics.

    This is the function you run after every batch of requests (or on a
    rolling window in production) to produce the dashboard numbers.
    """
    metrics = ChainMetrics()
    metrics.total_requests = len(results)

    for result in results:
        metrics.total_end_to_end_latency += result.total_latency_seconds
        if result.exhausted:
            metrics.exhausted_requests += 1
        else:
            metrics.successful_requests += 1

        # Determine which link succeeded (if any) — the last attempt in a
        # non-exhausted result is the success. For exhausted results, no link
        # succeeded.
        success_attempt = None
        if not result.exhausted and result.attempts:
            success_attempt = result.attempts[-1]

        # Count reach / fall-over / retries per link.
        reached_links: set[int] = set()
        for attempt in result.attempts:
            link_idx = attempt.link_index
            reached_links.add(link_idx)

            link_metrics = metrics.per_link.setdefault(
                link_idx,
                LinkMetrics(link_index=link_idx, model=attempt.model),
            )
            link_metrics.total_latency += attempt.latency_seconds
            link_metrics.total_backoff += attempt.backoff_waited
            # attempt_number 0 means first try; >0 means a retry fired.
            if attempt.attempt_number > 0:
                link_metrics.total_retries += 1

        # Mark each reached link's "reached" count and resolve fell-over vs succeeded.
        for link_idx in reached_links:
            link_metrics = metrics.per_link[link_idx]
            link_metrics.reached += 1
            if success_attempt is not None and link_idx == success_attempt.link_index:
                link_metrics.succeeded += 1
            else:
                link_metrics.fell_over += 1

    return metrics


def format_report(metrics: ChainMetrics) -> str:
    """Human-readable summary for CLI output.

    Not a full dashboard — the raw ChainMetrics object is the machine-readable
    form. This is the "print to terminal at the end of a run" summary.
    """
    lines = []
    lines.append("Chain execution summary")
    lines.append("-" * 50)
    lines.append(f"  Total requests:    {metrics.total_requests}")
    lines.append(
        f"  Successful:        {metrics.successful_requests} "
        f"({metrics.success_rate:.1%})"
    )
    lines.append(
        f"  Exhausted:         {metrics.exhausted_requests} "
        f"({metrics.exhaustion_rate:.1%})"
    )
    lines.append(f"  Mean end-to-end:   {metrics.mean_latency:.2f}s")
    lines.append("")
    lines.append("Per-link metrics")
    lines.append("-" * 50)

    for idx in sorted(metrics.per_link.keys()):
        m = metrics.per_link[idx]
        lines.append(
            f"  Link {idx}  {m.model}"
        )
        lines.append(
            f"    reached:       {m.reached}   "
            f"succeeded: {m.succeeded}   "
            f"fell over: {m.fell_over}"
        )
        lines.append(
            f"    success rate:  {m.success_rate:.1%}   "
            f"fallback rate: {m.fallback_rate:.1%}"
        )
        lines.append(
            f"    retries:       {m.total_retries} "
            f"({m.retries_per_request:.2f}/request)"
        )
        lines.append(
            f"    latency sum:   {m.total_latency:.2f}s   "
            f"backoff sum: {m.total_backoff:.2f}s"
        )
        lines.append("")

    return "\n".join(lines)