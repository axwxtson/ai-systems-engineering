"""
Eval runner: orchestrates running evals across the golden dataset and
aggregates results into a report.

Three eval types run per case:
  - UNIT evals: deterministic assertions (e.g. refusal queries must be flagged as refused)
  - TRAJECTORY evals: did the agent use the expected tools?
  - END-TO-END evals: LLM-as-judge on faithfulness, relevance, refusal correctness

Results are aggregated by metric and by difficulty level so you can see
where the system is strong and where it regresses.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from golden_dataset import GOLDEN_DATASET
from analyser import run_analysis
from judges import check_faithfulness, check_relevance, check_refusal_correctness


@dataclass
class CaseResult:
    """Results for a single eval case."""
    case_id: str
    query: str
    difficulty: str
    expected_behaviour: str

    # System outputs
    answer: str = ""
    tools_called: list[str] = field(default_factory=list)
    sources_used: list[str] = field(default_factory=list)
    refused: bool = False
    latency_seconds: float = 0.0

    # Unit eval
    unit_passed: Optional[bool] = None
    unit_reason: str = ""

    # Trajectory eval
    trajectory_passed: Optional[bool] = None
    trajectory_reason: str = ""

    # End-to-end (LLM-as-judge) scores
    faithfulness_score: Optional[int] = None
    faithfulness_reasoning: str = ""
    relevance_score: Optional[int] = None
    relevance_reasoning: str = ""
    refusal_score: Optional[int] = None
    refusal_reasoning: str = ""

    # Any errors during execution
    error: Optional[str] = None


def run_unit_eval(case: dict, result: CaseResult) -> None:
    """
    Unit eval: deterministic assertion.

    For refusal cases, assert the system was detected as refusing.
    For answer cases, assert a non-empty answer was produced.
    """
    if case["expected_behaviour"] == "refuse":
        if result.refused:
            result.unit_passed = True
            result.unit_reason = "Correctly flagged as refused"
        else:
            result.unit_passed = False
            result.unit_reason = "Expected refusal but system attempted to answer"
    else:
        if result.answer and not result.refused:
            result.unit_passed = True
            result.unit_reason = "Answer produced"
        elif result.refused:
            result.unit_passed = False
            result.unit_reason = "System refused but case expected an answer"
        else:
            result.unit_passed = False
            result.unit_reason = "Empty answer"


def run_trajectory_eval(case: dict, result: CaseResult) -> None:
    """
    Trajectory eval: did the agent call the expected tools?

    Passes if every expected tool was called at least once. Extra tool
    calls are allowed (the agent may legitimately explore). For cases with
    no expected tools (boundary refusals), passes iff no tools were called.
    """
    expected = set(case["expected_tools"])
    called = set(result.tools_called)

    if not expected:
        # Should have called no tools (e.g. boundary refusal)
        if not called:
            result.trajectory_passed = True
            result.trajectory_reason = "Correctly called no tools"
        else:
            result.trajectory_passed = False
            result.trajectory_reason = (
                f"Expected no tool calls, but called: {sorted(called)}"
            )
        return

    missing = expected - called
    if not missing:
        extra = called - expected
        if extra:
            result.trajectory_passed = True
            result.trajectory_reason = (
                f"All expected tools called. Extra: {sorted(extra)}"
            )
        else:
            result.trajectory_passed = True
            result.trajectory_reason = "Exact match on tool calls"
    else:
        result.trajectory_passed = False
        result.trajectory_reason = f"Missing expected tools: {sorted(missing)}"


def run_llm_judges(case: dict, result: CaseResult) -> None:
    """Run LLM-as-judge graders appropriate for this case's expected behaviour."""
    # Faithfulness: always applicable when context was retrieved
    faith = check_faithfulness(result.answer, result.context_for_grading())
    result.faithfulness_score = faith.get("score")
    result.faithfulness_reasoning = faith.get("reasoning", "")

    # Relevance: always applicable
    rel = check_relevance(case["query"], result.answer)
    result.relevance_score = rel.get("score")
    result.relevance_reasoning = rel.get("reasoning", "")

    # Refusal correctness: only for refuse cases
    if case["expected_behaviour"] == "refuse":
        ref = check_refusal_correctness(case["query"], result.answer)
        result.refusal_score = ref.get("score")
        result.refusal_reasoning = ref.get("reasoning", "")


def _attach_context(result: CaseResult, context: str) -> None:
    """Helper to attach context string for faithfulness grading."""
    result._context = context


def _case_context(result: CaseResult) -> str:
    return getattr(result, "_context", "")


# Monkey-patch method onto CaseResult for cleaner API
CaseResult.context_for_grading = lambda self: getattr(self, "_context", "")


def run_single_case(case: dict, verbose: bool = False) -> CaseResult:
    """Run the full eval pipeline on a single case."""
    result = CaseResult(
        case_id=case["id"],
        query=case["query"],
        difficulty=case["difficulty"],
        expected_behaviour=case["expected_behaviour"],
    )

    try:
        start = time.time()
        system_output = run_analysis(case["query"], verbose=verbose)
        result.latency_seconds = time.time() - start

        result.answer = system_output["answer"]
        result.tools_called = system_output["tools_called"]
        result.sources_used = system_output["sources_used"]
        result.refused = system_output["refused"]
        _attach_context(result, system_output["context"])

        run_unit_eval(case, result)
        run_trajectory_eval(case, result)
        run_llm_judges(case, result)

    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"

    return result


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

@dataclass
class AggregateReport:
    """Aggregated results across all eval cases."""
    total_cases: int
    cases_with_errors: int

    unit_pass_rate: float
    trajectory_pass_rate: float

    mean_faithfulness: float
    mean_relevance: float
    mean_refusal: float  # only computed over refusal cases

    total_latency: float
    mean_latency: float

    by_difficulty: dict  # difficulty -> {unit, trajectory, faithfulness, relevance}
    regressions: list    # cases where any metric scored <= 2
    case_results: list   # full CaseResult list


def _safe_mean(values: list[float]) -> float:
    clean = [v for v in values if v is not None]
    return sum(clean) / len(clean) if clean else 0.0


def aggregate(case_results: list[CaseResult]) -> AggregateReport:
    """Build an aggregate report from per-case results."""
    total = len(case_results)
    errors = sum(1 for r in case_results if r.error)

    unit_passes = [r.unit_passed for r in case_results if r.unit_passed is not None]
    traj_passes = [r.trajectory_passed for r in case_results if r.trajectory_passed is not None]

    faithfulness_scores = [r.faithfulness_score for r in case_results]
    relevance_scores = [r.relevance_score for r in case_results]
    refusal_scores = [r.refusal_score for r in case_results if r.refusal_score is not None]
    latencies = [r.latency_seconds for r in case_results]

    # Group by difficulty
    by_diff: dict = {}
    for r in case_results:
        d = r.difficulty
        if d not in by_diff:
            by_diff[d] = {
                "count": 0,
                "unit_passes": 0,
                "trajectory_passes": 0,
                "faithfulness": [],
                "relevance": [],
            }
        by_diff[d]["count"] += 1
        if r.unit_passed:
            by_diff[d]["unit_passes"] += 1
        if r.trajectory_passed:
            by_diff[d]["trajectory_passes"] += 1
        if r.faithfulness_score is not None:
            by_diff[d]["faithfulness"].append(r.faithfulness_score)
        if r.relevance_score is not None:
            by_diff[d]["relevance"].append(r.relevance_score)

    for d in by_diff:
        by_diff[d]["mean_faithfulness"] = _safe_mean(by_diff[d]["faithfulness"])
        by_diff[d]["mean_relevance"] = _safe_mean(by_diff[d]["relevance"])

    # Regressions: any case where a judge scored <= 2 or a unit/trajectory eval failed
    regressions = []
    for r in case_results:
        flagged = []
        if r.unit_passed is False:
            flagged.append("unit")
        if r.trajectory_passed is False:
            flagged.append("trajectory")
        if r.faithfulness_score is not None and r.faithfulness_score <= 2:
            flagged.append("faithfulness")
        if r.relevance_score is not None and r.relevance_score <= 2:
            flagged.append("relevance")
        if r.refusal_score is not None and r.refusal_score <= 2:
            flagged.append("refusal")
        if flagged:
            regressions.append({"case_id": r.case_id, "flagged": flagged, "result": r})

    return AggregateReport(
        total_cases=total,
        cases_with_errors=errors,
        unit_pass_rate=sum(unit_passes) / len(unit_passes) if unit_passes else 0.0,
        trajectory_pass_rate=sum(traj_passes) / len(traj_passes) if traj_passes else 0.0,
        mean_faithfulness=_safe_mean(faithfulness_scores),
        mean_relevance=_safe_mean(relevance_scores),
        mean_refusal=_safe_mean(refusal_scores),
        total_latency=sum(latencies),
        mean_latency=_safe_mean(latencies),
        by_difficulty=by_diff,
        regressions=regressions,
        case_results=case_results,
    )


def run_full_eval(verbose: bool = False, on_case_complete=None) -> AggregateReport:
    """
    Run the full eval suite over the golden dataset.

    on_case_complete: optional callback(case_index, total, CaseResult) for
                       progress reporting from the CLI.
    """
    results: list[CaseResult] = []
    total = len(GOLDEN_DATASET)

    for idx, case in enumerate(GOLDEN_DATASET):
        result = run_single_case(case, verbose=verbose)
        results.append(result)
        if on_case_complete:
            on_case_complete(idx + 1, total, result)

    return aggregate(results)