"""Benchmark scores and the message conversion the in-process replays rely on."""

import pytest

from fd_demo_agent.bugs import PLANTED_BUGS, BugKind
from fd_scripts.convert import assistant_message, assistant_param, conversation, tool_message
from fd_scripts.scoring import CaseResult, score
from fd_shared.enums import BenchmarkMethod, MessageRole
from fd_shared.models import Message, StepView


def result(
    method: BenchmarkMethod, predicted: int | None, *, verified: bool | None = None
) -> CaseResult:
    return CaseResult(
        method=method,
        case_id="c",
        bug_kind=BugKind.AM_AS_PM,
        true_step=5,
        predicted_step=predicted,
        verified=verified,
        verdict_kind=None,
        error_code=None,
        cost_usd=0.5,
        seconds=2.0,
    )


def test_score_counts_exact_within_one_and_misses() -> None:
    engine = BenchmarkMethod.FIRST_DOMINO
    results = [
        result(engine, 5, verified=True),
        result(engine, 6, verified=True),
        result(engine, 8, verified=False),
        result(engine, None, verified=False),
        result(BenchmarkMethod.READ_TRACE_JUDGE, 5),
    ]

    scores = score(engine, results)

    assert scores.runs_scored == 4
    assert scores.exact_accuracy == pytest.approx(0.25)
    assert scores.within_one_accuracy == pytest.approx(0.5)
    assert scores.verified_rate == pytest.approx(0.5)
    assert scores.mean_cost_usd == pytest.approx(0.5)


def test_a_method_without_proof_has_no_verified_rate() -> None:
    judge = BenchmarkMethod.READ_TRACE_JUDGE

    assert score(judge, [result(judge, 4)]).verified_rate is None


def test_planted_turns_survive_a_round_trip() -> None:
    for bug in PLANTED_BUGS:
        assert assistant_param(assistant_message(bug.replacement)) == bug.replacement


def test_conversation_rebuilds_turns_and_tool_results_in_order() -> None:
    output = assistant_message(PLANTED_BUGS[0].replacement)
    call_id = output.tool_calls[0].id
    step = StepView(
        index=1,
        model="m",
        output=output,
        tool_results=[
            tool_message({"role": "tool", "tool_call_id": call_id, "content": '{"ok": true}'})
        ],
    )
    opening = [{"role": "user", "content": "Incoming call"}]

    messages = conversation(opening, [step])  # pyright: ignore[reportArgumentType] a literal user message

    assert [message["role"] for message in messages] == ["user", "assistant", "tool"]
    assert messages[2] == {"role": "tool", "tool_call_id": call_id, "content": '{"ok": true}'}
    assert Message.model_validate(output.model_dump()).role is MessageRole.ASSISTANT
