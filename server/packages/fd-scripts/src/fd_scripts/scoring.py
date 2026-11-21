"""Per-case benchmark results and the scores computed from them."""

from statistics import fmean

from pydantic import BaseModel, ConfigDict, Field, computed_field

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

    @computed_field
    @property
    def exact(self) -> bool:
        """The named step is the labelled step. False when no step was named."""
        return self.predicted_step == self.true_step

    @computed_field
    @property
    def within_one(self) -> bool:
        """The named step is at most one off. False when no step was named."""
        return self.predicted_step is not None and abs(self.predicted_step - self.true_step) <= 1


ACCURACY_DEFINITION = (
    "Accuracy is over every labelled run (runs_scored). A run where the method named no step, "
    "such as a task_or_tool_issue verdict or an error, counts as a miss."
)


class MethodScore(BaseModel):
    """One method's scores over every labelled run. See `ACCURACY_DEFINITION`."""

    model_config = ConfigDict(frozen=True)

    method: BenchmarkMethod
    runs_scored: int = Field(description="Every labelled run, including ones with no step named.")
    exact_accuracy: float = Field(
        description="Runs where the named step is the labelled step, over `runs_scored`."
    )
    within_one_accuracy: float = Field(
        description="Runs where the named step is at most one off, over `runs_scored`."
    )
    verified_rate: float | None
    mean_cost_usd: float
    mean_seconds: float
    mean_replays: float | None = None


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
        exact_accuracy=fmean(result.exact for result in mine),
        within_one_accuracy=fmean(result.within_one for result in mine),
        verified_rate=fmean(proofs) if proofs else None,
        mean_cost_usd=fmean(result.cost_usd for result in mine),
        mean_seconds=fmean(result.seconds for result in mine),
        mean_replays=fmean(replays) if replays else None,
    )
