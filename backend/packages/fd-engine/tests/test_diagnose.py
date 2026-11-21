"""Bisect, verify and fallback end to end on scripted replays."""

import math
from uuid import uuid4

import pytest

from fd_engine.bisect import Bisector
from fd_engine.checks import CheckRunner
from fd_engine.diagnose import Diagnoser
from fd_engine.errors import CheckBudgetError, ReplayUnavailableError
from fd_engine.fallback import rank_candidates
from fd_engine.models import CheckPhase, CheckResult, DiagnosisResult, ReplayOutcome, VerdictKind
from fd_engine.settings import EngineSettings

from .fakes import (
    TEST_MODEL,
    E,
    F,
    FakeFixer,
    FakeReader,
    FakeRunner,
    FakeSink,
    P,
    Script,
    break_at,
    settings,
)


async def run_diagnosis(
    runner: FakeRunner,
    step_count: int,
    *,
    fixer: FakeFixer | None = None,
    sink: FakeSink | None = None,
    config: EngineSettings | None = None,
) -> DiagnosisResult:
    reader = FakeReader(step_count)
    diagnoser = Diagnoser(
        reader=reader,
        runner=runner,
        sink=sink or FakeSink(),
        fixer=fixer or FakeFixer(),
        settings=config or settings(),
    )
    return await diagnoser.diagnose(reader.run_id, uuid4())


async def test_clean_break_is_found_and_verified() -> None:
    runner = FakeRunner(plain=break_at(4), fixed={4: [P, P, P, P, F]})

    result = await run_diagnosis(runner, step_count=8)

    assert result.verdict_kind is VerdictKind.STEP_VERIFIED
    assert result.first_domino_step == 4
    assert (result.verify_passes, result.verify_samples) == (4, 5)
    assert result.fixed_output is not None
    assert result.fixed_output.content == "fixed step 4"


async def test_break_at_step_one() -> None:
    runner = FakeRunner(plain=break_at(1), fixed={1: [P] * 5})

    result = await run_diagnosis(runner, step_count=6)

    assert result.verdict_kind is VerdictKind.STEP_VERIFIED
    assert result.first_domino_step == 1


async def test_task_that_always_fails_blames_no_step() -> None:
    runner = FakeRunner(plain=lambda _: [F, F, F])

    result = await run_diagnosis(runner, step_count=8)

    assert result.verdict_kind is VerdictKind.TASK_OR_TOOL_ISSUE
    assert result.first_domino_step is None
    assert result.check_count == 1
    assert [call.from_step for call in runner.calls] == [0]


async def test_flaky_middle_counts_any_pass_as_can_succeed() -> None:
    def flaky(save_point: int) -> list[ReplayOutcome]:
        if save_point >= 5:
            return [F, F, F]
        return [F, P, E] if save_point >= 2 else [P, P, P]

    runner = FakeRunner(plain=flaky, fixed={5: [P, P, P, F, F]})

    result = await run_diagnosis(runner, step_count=8)

    assert result.verdict_kind is VerdictKind.STEP_VERIFIED
    assert result.first_domino_step == 5


async def test_verify_that_does_not_flip_reports_partial_passes() -> None:
    runner = FakeRunner(plain=break_at(4), fixed={4: [P, P, F, F, F]})

    result = await run_diagnosis(runner, step_count=8)

    assert result.verdict_kind is VerdictKind.MULTIPLE_CAUSES
    assert result.first_domino_step == 4
    assert (result.verify_passes, result.verify_samples) == (2, 5)
    fallback_steps = [c.from_step + 1 for c in runner.calls if c.replacement_output][1:]
    assert fallback_steps == [3, 5, 2, 6]


async def test_fallback_neighbor_that_flips_is_verified() -> None:
    runner = FakeRunner(plain=break_at(4), fixed={3: [P] * 5})

    result = await run_diagnosis(runner, step_count=8)

    assert result.verdict_kind is VerdictKind.STEP_VERIFIED
    assert result.first_domino_step == 3


async def test_no_usable_fix_is_unverified_without_a_verify_replay() -> None:
    runner = FakeRunner(plain=break_at(4))
    fixer = FakeFixer(unfixable=set(range(1, 9)))

    result = await run_diagnosis(runner, step_count=8, fixer=fixer)

    assert result.verdict_kind is VerdictKind.STEP_UNVERIFIED
    assert result.first_domino_step == 4
    assert result.verify_passes is None
    assert all(call.replacement_output is None for call in runner.calls)
    assert result.cost_usd == pytest.approx(5 * fixer.cost_usd)


async def test_all_errored_check_stops_the_diagnosis() -> None:
    runner = FakeRunner(plain=lambda _: [E, E, E])

    with pytest.raises(ReplayUnavailableError):
        await run_diagnosis(runner, step_count=4)


async def test_replay_timeout_counts_as_errored() -> None:
    runner = FakeRunner(plain=break_at(2), delay_seconds=1.0)

    with pytest.raises(ReplayUnavailableError):
        await run_diagnosis(runner, step_count=4, config=settings(replay_timeout_seconds=0.01))


async def test_check_budget_is_enforced() -> None:
    runner = FakeRunner(plain=break_at(7))

    with pytest.raises(CheckBudgetError):
        await run_diagnosis(runner, step_count=16, config=settings(max_checks=2))


async def test_sink_sees_each_check_pending_then_finished() -> None:
    sink = FakeSink()
    runner = FakeRunner(plain=break_at(3), fixed={3: [P] * 5})

    result = await run_diagnosis(runner, step_count=8, sink=sink)

    assert [c.index for c in sink.started] == list(range(result.check_count))
    assert [c.index for c in sink.finished] == list(range(result.check_count))
    assert all(c.result is CheckResult.PENDING for c in sink.started)
    assert sink.finished[0].phase is CheckPhase.PRECHECK
    assert sink.finished[-1].phase is CheckPhase.VERIFY
    assert result.replay_count == sum(c.samples for c in sink.finished)


async def test_bisect_uses_strong_model_and_verify_uses_agent_model() -> None:
    runner = FakeRunner(plain=break_at(3), fixed={3: [P] * 5})

    await run_diagnosis(runner, step_count=8)

    plain = [c for c in runner.calls if c.replacement_output is None]
    fixed = [c for c in runner.calls if c.replacement_output is not None]
    assert all(c.model_override == TEST_MODEL for c in plain)
    assert [(c.from_step, c.model_override) for c in fixed] == [(2, None)]


@pytest.mark.parametrize("step_count", range(1, 13))
async def test_bisect_invariant_finds_every_break(step_count: int) -> None:
    for broken in range(1, step_count + 1):
        script: Script = break_at(broken)
        sink = FakeSink()
        checks = CheckRunner(
            diagnosis_id=uuid4(),
            run_id=uuid4(),
            runner=FakeRunner(plain=script),
            sink=sink,
            settings=settings(),
        )
        bisector = Bisector(diagnosis_id=uuid4(), checks=checks, sink=sink, settings=settings())

        found = await bisector.find_first_domino(step_count)

        assert found is not None
        assert found == broken
        assert P in script(found - 1)
        assert P not in script(found)
        assert checks.check_count <= 1 + math.ceil(math.log2(step_count))
        for event in sink.progress_events[1:]:
            assert event.search_low is not None
            assert event.search_high is not None
            assert event.search_low - 1 < broken <= event.search_high


def test_rank_candidates_nearest_first_within_bounds() -> None:
    assert rank_candidates(4, 8, 2) == [3, 5, 2, 6]
    assert rank_candidates(1, 3, 2) == [2, 3]
    assert rank_candidates(3, 3, 0) == []


def test_verify_threshold_cannot_exceed_samples() -> None:
    with pytest.raises(ValueError, match="verify_pass_threshold"):
        settings(verify_samples=2, verify_pass_threshold=3)
