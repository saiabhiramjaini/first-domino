"""Protocol ports the engine depends on: ReplayRunner, RunReader, CheckSink and CostSink.

The API implements them in `fd_api.adapters`. The engine never reaches storage or HTTP any
other way.
"""

from typing import Protocol
from uuid import UUID

from fd_shared.enums import DiagnosisStatus, ReplayOutcome
from fd_shared.models import CheckView, Message, RunView, StepView


class RunReader(Protocol):
    """Loads the failed run and its recorded steps."""

    async def get_run(self, run_id: UUID) -> RunView:
        """Return the run, its task input and its step count."""
        ...

    async def get_steps(self, run_id: UUID) -> list[StepView]:
        """Return the run's steps ordered by index, starting at 1."""
        ...


class ReplayRunner(Protocol):
    """Replays a run on the customer side and reports each replay's outcome."""

    async def replay(
        self,
        run_id: UUID,
        *,
        from_step: int,
        samples: int,
        model_override: str | None,
        replacement_output: Message | None,
    ) -> list[ReplayOutcome]:
        """Enqueue `samples` replays of `run_id` and wait for all of them.

        Args:
            run_id: The recorded run to replay.
            from_step: Keep steps 1..`from_step` as recorded; 0 starts fresh.
            samples: How many independent replays to run.
            model_override: Run the remaining steps with this model, or the agent's own if None.
            replacement_output: Use this as step `from_step + 1`'s model output instead of
                calling the model, then continue.

        Returns:
            One outcome per replay, `samples` long. A replay that times out is `errored`.
        """
        ...


class CheckSink(Protocol):
    """Stores each check and the live search range so the web app can show them."""

    async def check_started(self, check: CheckView) -> None:
        """Store a new check whose result is `pending`."""
        ...

    async def check_finished(self, check: CheckView) -> None:
        """Store the passes and result of a check stored earlier with the same index."""
        ...

    async def progress(
        self,
        diagnosis_id: UUID,
        *,
        status: DiagnosisStatus,
        search_low: int | None,
        search_high: int | None,
    ) -> None:
        """Store the diagnosis status and the current bisect range."""
        ...


class CostSink(Protocol):
    """Receives the cost of each engine model call while a diagnosis runs, for a live total."""

    async def cost_added(self, diagnosis_id: UUID, cost_usd: float) -> None:
        """Add one model call's cost (a fix or an explanation) to the diagnosis's running total.

        The final `DiagnosisResult.cost_usd` is still the whole total. Grouping runs after the
        diagnosis, in the API, which adds its cost itself.
        """
        ...
