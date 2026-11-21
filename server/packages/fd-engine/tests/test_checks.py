"""A check stops its replays once its result is decided, and bisect skips implied checks."""

import asyncio
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest

from fd_engine.bisect import Bisector
from fd_engine.checks import CheckRequest, CheckRunner
from fd_engine.errors import ReplayNotFaithfulError, ReplayUnavailableError
from fd_engine.settings import EngineSettings
from fd_shared.enums import CheckPhase, CheckResult
from fd_shared.models import Message, ReplayResult

from .fakes import D, E, F, FakeRunner, FakeSink, P, Scripted, as_result, break_at, settings

HANG = None
"""A scripted replay that never finishes until it is cancelled."""


@dataclass
class GatedRunner:
    """One scripted outcome per call, in order; `HANG` waits until the call is cancelled."""

    script: list[Scripted | None]
    calls: int = 0
    cancelled: int = 0
    in_flight: int = 0
    peak_in_flight: int = 0
    samples_asked: list[int] = field(default_factory=list)

    async def replay(
        self,
        run_id: UUID,
        *,
        from_step: int,
        samples: int,
        model_override: str | None,
        replacement_output: Message | None,
    ) -> list[ReplayResult]:
        outcome = self.script[self.calls]
        self.calls += 1
        self.samples_asked.append(samples)
        self.in_flight += 1
        self.peak_in_flight = max(self.peak_in_flight, self.in_flight)
        try:
            await asyncio.sleep(0)
            if outcome is None:
                await asyncio.Event().wait()
            return [as_result(outcome)] if outcome is not None else []
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
        finally:
            self.in_flight -= 1


def check_runner(
    runner: GatedRunner, config: EngineSettings | None = None, sink: FakeSink | None = None
) -> CheckRunner:
    return CheckRunner(
        diagnosis_id=uuid4(),
        run_id=uuid4(),
        runner=runner,
        sink=sink or FakeSink(),
        settings=config or settings(),
    )


def bisect_check(samples: int = 3) -> CheckRequest:
    return CheckRequest(phase=CheckPhase.BISECT, save_point=2, samples=samples, required_passes=1)


def verify_check() -> CheckRequest:
    return CheckRequest(phase=CheckPhase.VERIFY, save_point=2, samples=5, required_passes=3)


async def test_can_succeed_stops_the_other_replays_after_one_pass() -> None:
    runner = GatedRunner([P, HANG, HANG])
    checks = check_runner(runner)

    check = await checks.run(bisect_check())

    assert check.result is CheckResult.CAN_SUCCEED
    assert (check.passes, check.samples) == (1, 1)
    assert runner.cancelled == 2
    assert checks.replay_count == 1


async def test_doomed_waits_for_every_replay() -> None:
    runner = GatedRunner([F, F, F])

    check = await check_runner(runner).run(bisect_check())

    assert check.result is CheckResult.DOOMED
    assert (check.passes, check.samples) == (0, 3)
    assert runner.cancelled == 0


async def test_replays_of_a_check_run_at_once_one_per_call() -> None:
    runner = GatedRunner([F, F, F, F, F])

    await check_runner(runner).run(verify_check())

    assert runner.peak_in_flight == 5
    assert runner.samples_asked == [1] * 5


@pytest.mark.parametrize(
    ("script", "result", "passes"),
    [
        ([P, P, P, HANG, HANG], CheckResult.CAN_SUCCEED, 3),
        ([F, F, F, HANG, HANG], CheckResult.DOOMED, 0),
    ],
)
async def test_verify_stops_once_its_result_is_decided(
    script: list[Scripted | None], result: CheckResult, passes: int
) -> None:
    runner = GatedRunner(script)

    check = await check_runner(runner).run(verify_check())

    assert check.result is result
    assert (check.passes, check.samples) == (passes, 3)
    assert runner.cancelled == 2


async def test_an_errored_replay_does_not_decide_a_check() -> None:
    runner = GatedRunner([E, P, HANG])

    check = await check_runner(runner).run(bisect_check())

    assert check.result is CheckResult.CAN_SUCCEED
    assert (check.passes, check.samples) == (1, 1)


async def test_a_check_whose_replays_all_errored_is_unavailable() -> None:
    with pytest.raises(ReplayUnavailableError):
        await check_runner(GatedRunner([E, E, E])).run(bisect_check())


async def test_drifted_replays_are_reported_but_not_counted() -> None:
    runner = GatedRunner([D, P, D, P, P])
    checks = check_runner(runner)

    check = await checks.run(verify_check())

    assert check.result is CheckResult.CAN_SUCCEED
    assert (check.passes, check.samples) == (3, 3)
    assert (check.drifted, check.drift_tool_name) == (2, "lookup")
    assert checks.replay_count == 5


async def test_a_drifted_pass_does_not_decide_a_check() -> None:
    runner = GatedRunner([D, P, HANG])

    check = await check_runner(runner).run(bisect_check())

    assert check.result is CheckResult.CAN_SUCCEED
    assert (check.passes, check.samples, check.drifted) == (1, 1, 1)
    assert runner.cancelled == 1


async def test_verify_stops_early_once_drift_leaves_too_few_replays() -> None:
    runner = GatedRunner([D, D, F, HANG, HANG])

    check = await check_runner(runner).run(verify_check())

    assert check.result is CheckResult.DOOMED
    assert (check.passes, check.samples, check.drifted) == (0, 1, 2)
    assert runner.cancelled == 2


@pytest.mark.parametrize("script", [[D, D, D], [E, D, E]], ids=["all_drifted", "mixed"])
async def test_a_check_with_drift_and_no_evidence_is_not_faithful(
    script: list[Scripted | None],
) -> None:
    sink = FakeSink()

    with pytest.raises(ReplayNotFaithfulError):
        await check_runner(GatedRunner(script), sink=sink).run(bisect_check())

    [finished] = sink.finished
    assert finished.result is CheckResult.PENDING
    assert (finished.passes, finished.samples) == (0, 0)
    assert (finished.drifted, finished.drift_tool_name) == (script.count(D), "lookup")


async def test_a_timeout_keeps_the_replays_that_finished() -> None:
    runner = GatedRunner([F, HANG, HANG])

    checks = check_runner(runner, settings(replay_timeout_seconds=0.05))

    check = await checks.run(bisect_check())

    assert check.result is CheckResult.DOOMED
    assert (check.passes, check.samples) == (0, 1)
    assert checks.replay_count == 3
    assert runner.cancelled == 2


async def bisect(step_count: int, broken: int) -> tuple[int | None, list[CheckPhase]]:
    sink = FakeSink()
    checks = CheckRunner(
        diagnosis_id=uuid4(),
        run_id=uuid4(),
        runner=FakeRunner(plain=break_at(broken)),
        sink=sink,
        settings=settings(),
    )
    bisector = Bisector(diagnosis_id=uuid4(), checks=checks, sink=sink, settings=settings())
    found = await bisector.find_first_domino(step_count)
    return found, [check.phase for check in sink.finished]


async def test_the_fresh_run_check_is_skipped_when_the_first_bisect_check_passes() -> None:
    found, phases = await bisect(step_count=8, broken=6)

    assert found == 6
    assert CheckPhase.PRECHECK not in phases


async def test_the_fresh_run_check_runs_after_a_doomed_first_bisect_check() -> None:
    found, phases = await bisect(step_count=8, broken=2)

    assert found == 2
    assert phases[:2] == [CheckPhase.BISECT, CheckPhase.PRECHECK]


async def test_a_one_step_run_needs_only_the_fresh_run_check() -> None:
    found, phases = await bisect(step_count=1, broken=1)

    assert found == 1
    assert phases == [CheckPhase.PRECHECK]
