"""A diagnosis first checks that the success check fails a replay keeping every step."""

import pytest

from fd_engine.errors import CheckBudgetError, CheckInconsistentError, ReplayNotFaithfulError
from fd_shared.enums import CheckPhase, DiagnosisStatus, VerdictKind

from .fakes import D, F, FakeRunner, FakeSink, P, Scripted, break_at, settings
from .test_diagnose import run_diagnosis


def passes_when_all_kept(step_count: int, kept: list[Scripted]) -> FakeRunner:
    """Doomed from step 3 on, except that keeping all `step_count` steps gives `kept`."""
    doomed = break_at(3)
    return FakeRunner(
        plain=lambda save_point: kept if save_point == step_count else doomed(save_point),
        fixed={3: [P] * 5},
    )


async def test_a_doomed_calibration_lets_the_search_go_on() -> None:
    sink = FakeSink()
    runner = FakeRunner(plain=break_at(3), fixed={3: [P] * 5})

    result = await run_diagnosis(runner, step_count=8, sink=sink)

    assert result.verdict_kind is VerdictKind.STEP_VERIFIED
    assert result.first_domino_step == 3
    calibration = sink.finished[0]
    assert (calibration.phase, calibration.save_point) == (CheckPhase.CALIBRATE, 8)
    assert (calibration.samples, calibration.passes) == (2, 0)
    assert sink.progress_events[0].status is DiagnosisStatus.BISECTING
    assert (sink.progress_events[0].search_low, sink.progress_events[0].search_high) == (0, 8)


async def test_a_pass_with_every_step_kept_stops_as_inconsistent() -> None:
    sink = FakeSink()
    runner = passes_when_all_kept(8, [F, P])

    with pytest.raises(CheckInconsistentError):
        await run_diagnosis(runner, step_count=8, sink=sink)

    assert [check.phase for check in sink.finished] == [CheckPhase.CALIBRATE]


async def test_calibration_drift_stops_as_not_faithful() -> None:
    with pytest.raises(ReplayNotFaithfulError):
        await run_diagnosis(passes_when_all_kept(8, [D]), step_count=8)


async def test_calibration_off_starts_with_the_search() -> None:
    sink = FakeSink()
    runner = passes_when_all_kept(8, [P])

    result = await run_diagnosis(runner, step_count=8, sink=sink, config=settings(calibrate=False))

    assert result.first_domino_step == 3
    assert CheckPhase.CALIBRATE not in [check.phase for check in sink.finished]
    assert 8 not in [call.from_step for call in runner.calls]


@pytest.mark.parametrize(("calibrate", "check_count"), [(False, 2), (True, None)])
async def test_calibration_counts_toward_the_check_budget(
    calibrate: bool, check_count: int | None
) -> None:
    runner = FakeRunner(plain=break_at(2), fixed={2: [P] * 5})
    config = settings(max_checks=2, calibrate=calibrate)

    if check_count is None:
        with pytest.raises(CheckBudgetError):
            await run_diagnosis(runner, step_count=2, config=config)
    else:
        result = await run_diagnosis(runner, step_count=2, config=config)
        assert result.check_count == check_count
