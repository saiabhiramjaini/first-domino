from types import SimpleNamespace
from typing import Any
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr

import first_domino as fd
from first_domino._generated.models import (
    ApiErrorCode,
    DiagnosisStatus,
    FailureReason,
    RunStatus,
)
from first_domino.client import FirstDominoClient
from first_domino.errors import ApiRequestError
from first_domino.settings import SdkSettings
from first_domino.testing import FakeApi

TASK = fd.TaskInput(prompt="Incoming call from +91 40 2311 4455", metadata={"task_id": "t01"})
USER = fd.Message(role=fd.MessageRole.user, content="Incoming call")
REPLY = fd.Message(role=fd.MessageRole.assistant, content="Handled.")
RUN_ID = UUID(int=42)


async def test_recording_is_dark_without_an_api_key(
    api: FakeApi, dark_client: FirstDominoClient
) -> None:
    async with fd.record("call-assistant", TASK, client=dark_client) as run:
        await run.step(model="m", output=REPLY, messages=[USER, REPLY])
        await run.finish(fd.RunOutcome.passed)

    assert run.run_id is None
    assert api.auth_headers == []


async def test_a_recorded_run_sends_start_steps_and_finish(
    api: FakeApi, client: FirstDominoClient
) -> None:
    async with fd.record("call-assistant", TASK, client=client) as run:
        await run.step(model="m", output=REPLY, messages=[USER, REPLY], tokens_in=12)
        await run.step(model="m", output=REPLY, messages=[USER, REPLY, REPLY])
        await run.finish(fd.RunOutcome.failed, final_output="Handled.")

    assert run.run_id in api.runs
    assert [step.index for step in api.steps] == [1, 2]
    assert api.steps[0].tokens_in == 12
    assert [(f.status, f.final_output) for f in api.finished] == [
        (fd.RunOutcome.failed, "Handled.")
    ]
    assert set(api.auth_headers) == {"Bearer fd_live_test"}


async def test_finish_is_sent_once(api: FakeApi, client: FirstDominoClient) -> None:
    async with fd.record("call-assistant", TASK, client=client) as run:
        await run.finish(fd.RunOutcome.passed)
        await run.finish(fd.RunOutcome.failed)

    assert len(api.finished) == 1


async def test_api_failures_never_reach_the_agent(api: FakeApi, client: FirstDominoClient) -> None:
    api.fail_paths = {"steps.record": 500, "runs.finish": 500}
    async with fd.record("call-assistant", TASK, client=client) as run:
        await run.step(model="m", output=REPLY, messages=[USER, REPLY])
        await run.finish(fd.RunOutcome.passed)

    assert run.finished


async def test_a_failed_start_leaves_the_run_dark(api: FakeApi, client: FirstDominoClient) -> None:
    api.fail_paths = {"runs.start": 503}
    async with fd.record("call-assistant", TASK, client=client) as run:
        await run.step(model="m", output=REPLY, messages=[USER, REPLY])

    assert run.run_id is None
    assert api.steps == []


async def test_an_agent_exception_finishes_the_run_as_errored_and_propagates(
    api: FakeApi, client: FirstDominoClient
) -> None:
    with pytest.raises(RuntimeError, match="agent broke"):
        async with fd.record("call-assistant", TASK, client=client):
            raise RuntimeError("agent broke")

    assert [f.status for f in api.finished] == [fd.RunOutcome.errored]


async def test_an_api_error_carries_its_stable_code(
    api: FakeApi, client: FirstDominoClient
) -> None:
    api.fail_paths = {"diagnoses.create": 409}
    with pytest.raises(ApiRequestError) as caught:
        await fd.diagnose(RUN_ID, client=client)

    assert caught.value.code == ApiErrorCode.conflict
    assert not caught.value.retryable


async def test_a_network_failure_is_retryable() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = FirstDominoClient(
        SdkSettings(api_key=SecretStr("fd_live_test"), base_url="http://first-domino.test"),
        httpx.AsyncClient(transport=httpx.MockTransport(refuse)),
    )
    with pytest.raises(ApiRequestError) as caught:
        await fd.diagnose(RUN_ID, client=client)

    assert caught.value.retryable
    assert caught.value.status_code is None


async def test_diagnose_then_wait_until_done(api: FakeApi, client: FirstDominoClient) -> None:
    api.diagnosis_statuses = [DiagnosisStatus.queued]
    started = await fd.diagnose(RUN_ID, client=client)
    api.diagnosis_statuses = [DiagnosisStatus.bisecting, DiagnosisStatus.done]
    final = await fd.wait_for_diagnosis(started.id, client=client)

    assert started.run_id == RUN_ID
    assert final.status == DiagnosisStatus.done
    assert final.first_domino_step == 4


def openai_response(content: str | None, tool_calls: list[dict[str, Any]] | None) -> Any:
    message = {"role": "assistant", "content": content, "tool_calls": tool_calls}
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(model_dump=lambda: message))],
        usage=SimpleNamespace(prompt_tokens=30, completion_tokens=5),
    )


class FakeCompletions:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = responses

    async def create(self, **_: Any) -> Any:
        return self._responses.pop(0)


async def test_wrap_records_each_completion_with_its_tool_results(
    api: FakeApi, client: FirstDominoClient
) -> None:
    call = {"id": "c1", "type": "function", "function": {"name": "end_call", "arguments": "{}"}}
    completions = FakeCompletions([openai_response(None, [call]), openai_response("Done.", None)])
    openai = SimpleNamespace(chat=SimpleNamespace(completions=completions), api_key="secret")
    first = [{"role": "user", "content": "Incoming call"}]

    async with fd.record("call-assistant", TASK, client=client) as run:
        wrapped = fd.wrap(openai, run)
        tools = [{"type": "function", "function": {"name": "end_call", "parameters": {}}}]
        await wrapped.chat.completions.create(model="small", messages=first, tools=tools)
        tool = {"role": "tool", "tool_call_id": "c1", "content": '{"ok": true}'}
        second = [*first, {"role": "assistant", "content": None, "tool_calls": [call]}, tool]
        await wrapped.chat.completions.create(model="small", messages=second)
        await run.finish(fd.RunOutcome.passed)

    assert wrapped.api_key == "secret"
    assert run.run_id is not None
    assert api.runs[run.run_id].tool_names == ["end_call"]
    assert [step.index for step in api.steps] == [1, 2]
    first_step, last_step = api.steps
    assert first_step.output.tool_calls == [fd.ToolCall(id="c1", name="end_call", arguments="{}")]
    assert [m.tool_call_id for m in first_step.tool_results or []] == ["c1"]
    assert len(first_step.messages) == 3
    assert last_step.output.content == "Done."
    assert last_step.tool_results == []
    assert first_step.tokens_in == 30


async def test_wrap_returns_the_client_unchanged_when_recording_is_off(
    dark_client: FirstDominoClient,
) -> None:
    openai = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions([])))
    async with fd.record("call-assistant", TASK, client=dark_client) as run:
        assert fd.wrap(openai, run) is openai


def test_openai_messages_round_trip() -> None:
    call = {"id": "c1", "type": "function", "function": {"name": "f", "arguments": "{}"}}
    params: list[dict[str, Any]] = [
        {"role": "system", "content": "Be helpful."},
        {"role": "assistant", "content": None, "tool_calls": [call]},
        {"role": "tool", "tool_call_id": "c1", "content": "ok"},
    ]
    messages = [fd.message_from_openai(p) for p in params]
    assert fd.messages_to_openai(messages) == params


async def test_record_sends_tool_names_and_starts_at_the_first_step(
    api: FakeApi, client: FirstDominoClient
) -> None:
    async with fd.record("call-assistant", TASK, tool_names=["a", "b"], client=client) as run:
        assert run.run_id is None
        run.add_tool_names(["b", "c"])
        await run.step(model="m", output=REPLY, messages=[USER, REPLY])
        run.add_tool_names(["too-late"])
        await run.finish(fd.RunOutcome.passed)

    assert run.run_id is not None
    assert api.runs[run.run_id].tool_names == ["a", "b", "c"]


@pytest.mark.parametrize(
    ("status", "reason", "sent"),
    [
        (fd.RunOutcome.failed, "Booked Tuesday, the caller said Thursday", True),
        (fd.RunOutcome.passed, "Booked Tuesday, the caller said Thursday", False),
        (fd.RunOutcome.errored, "Booked Tuesday, the caller said Thursday", False),
    ],
)
async def test_finish_sends_the_failure_reason_only_for_a_failed_run(
    api: FakeApi, client: FirstDominoClient, status: fd.RunOutcome, reason: str, sent: bool
) -> None:
    async with fd.record("call-assistant", TASK, client=client) as run:
        await run.finish(status, failure_reason=reason)

    (finished,) = api.finished
    assert finished.failure_reason == (FailureReason(reason) if sent else None)


async def test_a_long_failure_reason_is_cut_to_the_api_limit(
    api: FakeApi, client: FirstDominoClient
) -> None:
    async with fd.record("call-assistant", TASK, client=client) as run:
        await run.finish(fd.RunOutcome.failed, failure_reason="x" * 2500)

    assert api.finished[0].failure_reason == FailureReason("x" * 2000)


async def test_current_run_id_inside_record_once_the_run_started(client: FirstDominoClient) -> None:
    async with fd.record("call-assistant", TASK, client=client) as run:
        before = fd.current_run_id()
        await run.start()
        after = fd.current_run_id()

    assert before is None
    assert after is not None
    assert after == run.run_id
    assert fd.current_run_id() is None


async def finished_run(client: FirstDominoClient, outcome: fd.RunOutcome) -> UUID:
    async with fd.record("call-assistant", TASK, client=client) as run:
        await run.step(model="m", output=REPLY, messages=[USER, REPLY])
        await run.finish(outcome, final_output="Handled.")
    assert run.run_id is not None
    return run.run_id


async def test_flag_marks_a_passed_run_failed_with_the_reason(
    api: FakeApi, client: FirstDominoClient
) -> None:
    run_id = await finished_run(client, fd.RunOutcome.passed)
    reason = "The user said the visit was booked on the wrong day"

    run = await fd.flag(run_id, reason, client=client)

    assert run.id == run_id
    assert run.status == RunStatus.failed
    assert run.failure_reason == reason
    assert run.flagged_at is not None
    assert [(f.run_id, f.reason) for f in api.flagged] == [(run_id, reason)]


async def test_flag_refuses_a_run_that_did_not_pass(
    api: FakeApi, client: FirstDominoClient
) -> None:
    run_id = await finished_run(client, fd.RunOutcome.failed)

    with pytest.raises(ApiRequestError) as caught:
        await fd.flag(run_id, "The user complained", client=client)

    assert caught.value.status_code == 409
    assert caught.value.code == ApiErrorCode.conflict
    assert api.flagged == []


async def test_flag_of_an_unknown_run_is_not_found(client: FirstDominoClient) -> None:
    with pytest.raises(ApiRequestError) as caught:
        await fd.flag(RUN_ID, "The user complained", client=client)

    assert caught.value.code == ApiErrorCode.not_found
