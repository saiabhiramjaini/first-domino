"""A flagged run's replays are judged against its failure reason; other runs never are."""

import json
from uuid import uuid4

import pytest

from fd_engine.diagnose import Diagnoser
from fd_engine.errors import ReplayUnavailableError
from fd_engine.judge import LlmReplayJudge
from fd_engine.judged_replays import JudgedReplayRunner
from fd_engine.llm import Llm
from fd_engine.transcript import render_task
from fd_shared.enums import CheckPhase, CheckResult, ReplayOutcome, VerdictKind
from fd_shared.models import DiagnosisResult, ReplayResult

from .fakes import (
    BlindWorker,
    F,
    FakeExplainer,
    FakeFixer,
    FakeJudge,
    FakeReader,
    FakeRunner,
    FakeSink,
    FakeTransport,
    P,
    break_at,
    settings,
    tool_step,
)

REASON = "The user asked for Monday and got Tuesday."


async def flagged_diagnosis(
    runner: FakeRunner,
    reader: FakeReader,
    judge: FakeJudge,
    sink: FakeSink | None = None,
) -> DiagnosisResult:
    sink = sink or FakeSink()
    diagnoser = Diagnoser(
        reader=reader,
        runner=BlindWorker(runner, reader),
        sink=sink,
        fixer=FakeFixer(cost_usd=0.01),
        explainer=FakeExplainer(cost_usd=0.02),
        judge=judge,
        settings=settings(),
        cost_sink=sink,
    )
    return await diagnoser.diagnose(reader.run_id, uuid4())


async def test_the_judge_finds_the_step_the_worker_check_cannot_see() -> None:
    reader = FakeReader(8, failure_reason=REASON)
    judge = FakeJudge()
    sink = FakeSink()

    result = await flagged_diagnosis(
        FakeRunner(plain=break_at(4), fixed={4: [P] * 5}), reader, judge, sink
    )

    calibration = sink.finished[0]
    assert (calibration.phase, calibration.result) == (CheckPhase.CALIBRATE, CheckResult.DOOMED)
    assert result.verdict_kind is VerdictKind.STEP_VERIFIED
    assert result.first_domino_step == 4
    assert (result.verify_passes, result.verify_samples) == (3, 3)
    judge_costs = [judge.cost_usd] * len(judge.judged)
    assert sink.costs.count(judge.cost_usd) == len(judge.judged)
    assert result.cost_usd == pytest.approx(0.01 + 0.02 + sum(judge_costs))
    assert sum(sink.costs) == pytest.approx(result.cost_usd)


async def test_calibration_replays_are_judged_on_the_whole_recorded_run() -> None:
    reader = FakeReader(4, failure_reason=REASON)
    judge = FakeJudge()

    await flagged_diagnosis(FakeRunner(plain=break_at(2), fixed={2: [P] * 5}), reader, judge)

    calibration_samples = settings().calibration_samples
    assert all(len(steps) == 4 for steps in judge.judged[:calibration_samples])


async def test_a_degraded_judge_leaves_no_evidence() -> None:
    reader = FakeReader(4, failure_reason=REASON)

    with pytest.raises(ReplayUnavailableError):
        await flagged_diagnosis(FakeRunner(plain=break_at(2)), reader, FakeJudge(degraded=True))


async def test_a_replay_without_a_recorded_run_is_errored() -> None:
    reader = FakeReader(4, failure_reason=REASON)
    diagnoser = Diagnoser(
        reader=reader,
        runner=FakeRunner(plain=break_at(2)),
        sink=FakeSink(),
        fixer=FakeFixer(),
        explainer=FakeExplainer(),
        judge=FakeJudge(),
        settings=settings(),
    )

    with pytest.raises(ReplayUnavailableError):
        await diagnoser.diagnose(reader.run_id, uuid4())


async def test_a_run_that_is_not_flagged_is_never_judged() -> None:
    reader = FakeReader(8)
    judge = FakeJudge()
    diagnoser = Diagnoser(
        reader=reader,
        runner=FakeRunner(plain=break_at(4), fixed={4: [P] * 5}),
        sink=FakeSink(),
        fixer=FakeFixer(),
        explainer=FakeExplainer(),
        judge=judge,
        settings=settings(),
    )

    result = await diagnoser.diagnose(reader.run_id, uuid4())

    assert result.first_domino_step == 4
    assert judge.judged == []


async def test_the_judge_reads_the_kept_steps_then_the_replay_steps() -> None:
    reader = FakeReader(4, failure_reason=REASON)
    replay_run_id = uuid4()
    reader.replay_outputs[replay_run_id] = ReplayOutcome.PASSED.value
    reader.replay_steps[replay_run_id] = [tool_step(3, "new_tool")]
    judge = FakeJudge()
    run = await reader.get_run(reader.run_id)
    runner = JudgedReplayRunner(
        FakeRunner(plain=lambda _: [ReplayResult(outcome=F, replay_run_id=replay_run_id)]),
        judge=judge,
        reader=reader,
        run=run,
        steps=await reader.get_steps(reader.run_id),
        diagnosis_id=uuid4(),
        cost_sink=None,
    )

    [result] = await runner.replay(
        reader.run_id, from_step=2, samples=1, model_override=None, replacement_output=None
    )

    assert result.outcome is ReplayOutcome.PASSED
    [steps] = judge.judged
    assert [(s.index, s.output.tool_calls[0].name) for s in steps] == [
        (1, "tool_1"),
        (2, "tool_2"),
        (3, "new_tool"),
    ]
    assert runner.cost_usd == judge.cost_usd


def judge_with(*replies: str | None) -> tuple[LlmReplayJudge, FakeTransport]:
    transport = FakeTransport(replies=list(replies))
    llm = Llm(settings(), transport=transport)
    return LlmReplayJudge(llm, model="judge-test-model", temperature=0.0), transport


async def judged_by(model: LlmReplayJudge) -> ReplayOutcome:
    reader = FakeReader(2, failure_reason=REASON)
    replay_run_id = uuid4()
    reader.replay_outputs[replay_run_id] = "booked Monday"
    run = await reader.get_run(reader.run_id)
    replay = await reader.get_run(replay_run_id)
    judged = await model.judge(run, replay, await reader.get_steps(reader.run_id))
    return judged.outcome


@pytest.mark.parametrize(
    ("passed", "outcome"), [(True, ReplayOutcome.PASSED), (False, ReplayOutcome.FAILED)]
)
async def test_the_llm_judge_decides_from_one_cold_call(
    passed: bool, outcome: ReplayOutcome
) -> None:
    model, transport = judge_with(json.dumps({"passed": passed, "reason": "It booked Monday."}))

    assert await judged_by(model) is outcome
    assert transport.models == ["judge-test-model"]
    assert transport.temperatures == [0.0]
    [prompt] = transport.prompts
    assert f"Reported failure: {REASON}" in prompt
    assert "booked the wrong visit" in prompt
    assert "booked Monday" in prompt


@pytest.mark.parametrize(
    "replies",
    [
        ("not json", None),
        (json.dumps({"reason": "no decision"}), json.dumps({"reason": "still none"})),
        (json.dumps({"passed": None, "reason": "unsure"}),) * 2,
    ],
    ids=["garbage", "reason_only", "null_decision"],
)
async def test_an_unusable_judge_reply_makes_the_replay_errored(
    replies: tuple[str | None, ...],
) -> None:
    model, _ = judge_with(*replies)

    assert await judged_by(model) is ReplayOutcome.ERRORED


async def test_a_valid_decision_is_salvaged_from_a_bad_reason() -> None:
    reply = json.dumps({"passed": False, "reason": 7})
    model, _ = judge_with(reply, reply)

    assert await judged_by(model) is ReplayOutcome.FAILED


async def test_the_task_names_the_reported_failure_only_when_there_is_one() -> None:
    reader = FakeReader(1)
    flagged = FakeReader(1, failure_reason=REASON)

    assert "Reported failure" not in render_task(await reader.get_run(reader.run_id))
    assert render_task(await flagged.get_run(flagged.run_id)).endswith(
        f"Reported failure: {REASON}"
    )
