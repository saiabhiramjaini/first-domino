"""Bisect, verify and fallback end to end on scripted replays."""

import math
from uuid import uuid4

import pytest

from fd_engine.bisect import Bisector
from fd_engine.checks import CheckRunner
from fd_engine.diagnose import Diagnoser
from fd_engine.errors import CheckBudgetError, ReplayUnavailableError
from fd_engine.fallback import rank_candidates
from fd_engine.settings import EngineSettings
from fd_shared.enums import CheckPhase, CheckResult, ReplayOutcome, VerdictKind
from fd_shared.models import DiagnosisResult

from .fakes import (
    TEST_MODEL,
    E,
    F,
    FakeExplainer,
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
    explainer: FakeExplainer | None = None,
    config: EngineSettings | None = None,
) -> DiagnosisResult:
    reader = FakeReader(step_count)
    diagnoser = Diagnoser(
        reader=reader,
        runner=runner,
        sink=sink or FakeSink(),
        fixer=fixer or FakeFixer(),
        explainer=explainer or FakeExplainer(),
        settings=config or settings(),
    )
    return await diagnoser.diagnose(reader.run_id, uuid4())


async def test_clean_break_is_found_and_verified() -> None:
    runner = FakeRunner(plain=break_at(4), fixed={4: [P, P, P, P, F]})

    result = await run_diagnosis(runner, step_count=8)

    assert result.verdict_kind is VerdictKind.STEP_VERIFIED
    assert result.first_domino_step == 4
    assert (result.verify_passes, result.verify_samples) == (3, 3)
    assert result.fixed_output is not None
    assert result.fixed_output.content == "fixed step 4"


async def test_found_step_is_explained_and_costed() -> None:
    runner = FakeRunner(plain=break_at(4), fixed={4: [P] * 5})
    explainer = FakeExplainer()

    result = await run_diagnosis(runner, step_count=8, explainer=explainer)

    assert explainer.explained == [4]
    assert result.explanation is not None
    assert result.cost_usd == pytest.approx(FakeFixer().cost_usd + explainer.cost_usd)


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
    assert result.explanation is None
    assert result.check_count == 2
    assert list(dict.fromkeys(call.from_step for call in runner.calls)) == [4, 0]


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
    fixed_steps = dict.fromkeys(c.from_step + 1 for c in runner.calls if c.replacement_output)
    assert list(fixed_steps) == [4, 3, 5, 2, 6]


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
    assert result.cost_usd == pytest.approx(5 * fixer.cost_usd + FakeExplainer().cost_usd)


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
    assert [c.phase for c in sink.finished[:2]] == [CheckPhase.BISECT, CheckPhase.PRECHECK]
    assert sink.finished[-1].phase is CheckPhase.VERIFY
    assert result.replay_count == sum(c.samples for c in sink.finished)


@pytest.mark.parametrize(("with_strong", "bisect_model"), [(False, None), (True, TEST_MODEL)])
async def test_bisect_model_follows_settings_and_verify_uses_agent_model(
    with_strong: bool, bisect_model: str | None
) -> None:
    runner = FakeRunner(plain=break_at(3), fixed={3: [P] * 5})

    await run_diagnosis(runner, step_count=8, config=settings(bisect_with_strong_model=with_strong))

    plain = [c for c in runner.calls if c.replacement_output is None]
    fixed = [c for c in runner.calls if c.replacement_output is not None]
    assert all(c.model_override == bisect_model for c in plain)
    assert {(c.from_step, c.model_override) for c in fixed} == {(2, None)}


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


@pytest.mark.parametrize(
    ("fixed", "fixes"),
    [({3: [P] * 5}, 1), ({}, 1 + 4)],
    ids=["verified", "fallback"],
)
async def test_each_model_call_cost_is_reported_as_it_happens(
    fixed: dict[int, list[ReplayOutcome]], fixes: int
) -> None:
    sink = FakeSink()
    reader = FakeReader(8)
    diagnoser = Diagnoser(
        reader=reader,
        runner=FakeRunner(plain=break_at(3), fixed=fixed),
        sink=sink,
        fixer=FakeFixer(cost_usd=0.01),
        explainer=FakeExplainer(cost_usd=0.02),
        settings=settings(),
        cost_sink=sink,
    )

    result = await diagnoser.diagnose(reader.run_id, uuid4())

    assert sink.costs == [0.01] * fixes + [0.02]
    assert sum(sink.costs) == pytest.approx(result.cost_usd)


async def test_an_unlucky_check_is_rechecked_before_blaming_a_step() -> None:
    def unlucky(save_point: int) -> list[ReplayOutcome]:
        if save_point >= 3:
            return [F, F, F]
        return [F, F, F, P, F, F] if save_point >= 1 else [P, P, P]

    runner = FakeRunner(plain=unlucky, fixed={3: [P] * 5})

    result = await run_diagnosis(runner, step_count=4, config=settings(doomed_recheck_samples=3))

    assert result.verdict_kind is VerdictKind.STEP_VERIFIED
    assert result.first_domino_step == 3


async def test_a_doomed_save_point_is_checked_twice() -> None:
    runner = FakeRunner(plain=break_at(2), fixed={2: [P] * 5})

    result = await run_diagnosis(runner, step_count=4, config=settings(doomed_recheck_samples=3))

    assert result.first_domino_step == 2
    doomed_checks = [
        c.from_step for c in runner.calls if c.replacement_output is None and c.from_step >= 2
    ]
    assert doomed_checks.count(2) == 6
