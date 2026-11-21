"""Per-case benchmark results and the scores computed from them."""

from statistics import fmean

from pydantic import BaseModel, ConfigDict

from fd_demo_agent.bugs import BugKind
from fd_shared.enums import BenchmarkMethod, VerdictKind


class CaseResult(BaseModel):
    """One method's answer for one labelled run."""

    model_config = ConfigDict(frozen=True)

    method: BenchmarkMethod
    case_id: str
    bug_kind: BugKind
    true_step: int
    predicted_step: int | None
    verified: bool | None
    verdict_kind: VerdictKind | None
    error_code: str | None
    cost_usd: float
    seconds: float
    replays: int | None = None
    """Replays started, including ones stopped early; None for a method that does not replay."""


class MethodScore(BaseModel):
    """One method's scores over every labelled run."""

    model_config = ConfigDict(frozen=True)

    method: BenchmarkMethod
    runs_scored: int
    exact_accuracy: float
    within_one_accuracy: float
    verified_rate: float | None
    mean_cost_usd: float
    mean_seconds: float
    mean_replays: float | None = None


def _within_one(result: CaseResult) -> bool:
    return result.predicted_step is not None and abs(result.predicted_step - result.true_step) <= 1


def score(method: BenchmarkMethod, results: list[CaseResult]) -> MethodScore:
    """Score one method. A missing prediction is a miss; `verified_rate` is None without proof.

    Raises:
        ValueError: `results` has no result for `method`.
    """
    mine = [result for result in results if result.method is method]
    if not mine:
        msg = f"no results for {method}"
        raise ValueError(msg)
    proofs = [result.verified for result in mine if result.verified is not None]
    replays = [result.replays for result in mine if result.replays is not None]
    return MethodScore(
        method=method,
        runs_scored=len(mine),
        exact_accuracy=fmean(result.predicted_step == result.true_step for result in mine),
        within_one_accuracy=fmean(_within_one(result) for result in mine),
        verified_rate=fmean(proofs) if proofs else None,
        mean_cost_usd=fmean(result.cost_usd for result in mine),
        mean_seconds=fmean(result.seconds for result in mine),
        mean_replays=fmean(replays) if replays else None,
    )
