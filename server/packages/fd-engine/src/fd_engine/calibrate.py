"""Calibration: the success check must fail a replay that keeps every recorded step."""

from uuid import UUID

from fd_engine.bisect import CAN_SUCCEED_PASSES, bisect_model_override
from fd_engine.checks import CheckRequest, CheckRunner
from fd_engine.errors import CheckInconsistentError
from fd_engine.ports import CheckSink
from fd_engine.settings import EngineSettings
from fd_shared.enums import CheckPhase, CheckResult, DiagnosisStatus


class Calibrator:
    """Checks that a failed run replays as failed before the search relies on it."""

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

    async def calibrate(self, step_count: int) -> None:
        """Replay from save point `step_count` and require every replay to fail.

        The search assumes the run is doomed with all its steps kept. When a replay of exactly
        that passes, the success check does not reliably fail this run and no step can be
        blamed. Skipped when `calibrate` is off or the run has no step.

        Raises:
            CheckInconsistentError: A replay that kept every step passed.
        """
        if not self._settings.calibrate or step_count == 0:
            return
        await self._sink.progress(
            self._diagnosis_id,
            status=DiagnosisStatus.BISECTING,
            search_low=0,
            search_high=step_count,
        )
        check = await self._checks.run(
            CheckRequest(
                phase=CheckPhase.CALIBRATE,
                save_point=step_count,
                samples=self._settings.calibration_samples,
                required_passes=CAN_SUCCEED_PASSES,
                model_override=bisect_model_override(self._settings),
            )
        )
        if check.result is CheckResult.CAN_SUCCEED:
            raise CheckInconsistentError
