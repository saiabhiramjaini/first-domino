"""Binary search over save points for the first step from which the run is doomed."""

from uuid import UUID

from fd_engine.checks import CheckRequest, CheckRunner
from fd_engine.ports import CheckSink
from fd_engine.settings import EngineSettings
from fd_shared.enums import CheckPhase, CheckResult, DiagnosisStatus

CAN_SUCCEED_PASSES = 1
"""A save point can succeed when any one of its replays passes."""


class Bisector:
    """Finds the first doomed step of one failed run."""

    def __init__(
        self,
        *,
        diagnosis_id: UUID,
        checks: CheckRunner,
        sink: CheckSink,
        settings: EngineSettings,
    ) -> None:
        self._diagnosis_id = diagnosis_id
        self._checks = checks
        self._sink = sink
        self._settings = settings

    async def find_first_domino(self, step_count: int) -> int | None:
        """Return the first doomed step, or None when even a fresh run cannot succeed.

        A fresh run that never succeeds is a task or tool problem, so no step is blamed. The
        fresh-run check at save point 0 runs only when the first bisect check is doomed: a pass
        at any save point already shows a fresh run can succeed.
        """
        await self._progress(0, step_count)
        if step_count == 0:
            return None
        lo, hi = 1, step_count
        if lo < hi:
            lo, hi = await self._halve(lo, hi)
        if lo == 1 and not await self._can_succeed(0, CheckPhase.PRECHECK):
            return None
        return await self._search(lo, hi)

    async def _search(self, lo: int, hi: int) -> int:
        """Halve the range [lo, hi] until one step is left.

        Invariant: the run can succeed from save point `lo - 1` and is doomed at `hi`. It holds
        at the start because save point `lo - 1` passed a check (the fresh-run check when it is
        0) and the recorded run failed with all its steps kept. On exit `lo == hi`: keeping
        steps 1..lo-1 can succeed and keeping 1..lo cannot, so step `lo` is the first domino.
        """
        while lo < hi:
            lo, hi = await self._halve(lo, hi)
        return lo

    async def _halve(self, lo: int, hi: int) -> tuple[int, int]:
        """Check the middle save point and keep the half that holds the first domino."""
        mid = (lo + hi) // 2
        if await self._can_succeed(mid, CheckPhase.BISECT):
            lo = mid + 1
        else:
            hi = mid
        await self._progress(lo, hi)
        return lo, hi

    async def _can_succeed(self, save_point: int, phase: CheckPhase) -> bool:
        check = await self._checks.run(
            CheckRequest(
                phase=phase,
                save_point=save_point,
                samples=self._settings.samples_per_check,
                required_passes=CAN_SUCCEED_PASSES,
                model_override=(
                    self._settings.strong_model if self._settings.bisect_with_strong_model else None
                ),
            )
        )
        return check.result is CheckResult.CAN_SUCCEED

    async def _progress(self, lo: int, hi: int) -> None:
        await self._sink.progress(
            self._diagnosis_id,
            status=DiagnosisStatus.BISECTING,
            search_low=lo,
            search_high=hi,
        )
