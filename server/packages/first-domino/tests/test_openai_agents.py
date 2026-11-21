import json

import pytest

pytest.importorskip("agents", reason="needs the agents extra: first-domino[agents]")

from agents import Agent, Model, ModelProvider, RunConfig, function_tool, set_tracing_disabled
from agents.items import TResponseOutputItem
from agents.testing import ScriptedModel, assistant_message, function_call

import first_domino as fd
from first_domino import openai_agents as fd_agents
from first_domino.client import FirstDominoClient
from first_domino.responses_format import items_to_messages, messages_to_items
from first_domino.testing import FakeApi, make_job

set_tracing_disabled(disabled=True)

CALLER = "+91 99490 55621"


@function_tool
def lookup_contact(phone: str) -> str:
    """Look up a phone number in the user's contacts."""
    return json.dumps({"phone": phone, "name": "Srinivas" if phone == CALLER else None})


def call_assistant(model: Model | None = None) -> Agent:
    return Agent(
        name="call-assistant",
        instructions="Answer calls for Arjun.",
        tools=[lookup_contact],
        model=model,
    )


def lookup(phone: str, call_id: str) -> TResponseOutputItem:
    return function_call("lookup_contact", {"phone": phone}, call_id=call_id)


async def test_a_run_is_recorded_one_turn_per_step_with_its_tool_results(
    api: FakeApi, client: FirstDominoClient
) -> None:
    model = ScriptedModel([[lookup(CALLER, "c1")], [assistant_message("It is Srinivas.")]])
    task = fd.TaskInput(prompt="Incoming call", metadata={"task_id": "t07"})

    async with fd.record("call-assistant", task, client=client) as run:
        result = await fd_agents.run_recorded(call_assistant(model), "Incoming call", run)
        await run.finish(fd.RunOutcome.passed, final_output=str(result.final_output))

    assert run.run_id is not None
    assert api.runs[run.run_id].tool_names == ["lookup_contact"]
    first, last = api.steps
    assert (first.index, last.index) == (1, 2)
    assert first.output.tool_calls == [
        fd.ToolCall(
            id="c1",
            name="lookup_contact",
            arguments=json.dumps({"phone": CALLER}, separators=(",", ":")),
        )
    ]
    (tool_result,) = first.tool_results or []
    assert tool_result.tool_call_id == "c1"
    assert "Srinivas" in (tool_result.content or "")
    assert [m.role for m in first.messages] == ["user", "assistant", "tool"]
    assert last.output.content == "It is Srinivas."
    assert last.tool_results == []
    assert len(last.messages) == 4


async def test_a_replay_resumes_from_the_save_point_with_the_replacement(
    api: FakeApi, client: FirstDominoClient
) -> None:
    saved = [fd.Message(role=fd.MessageRole.user, content="Incoming call")]
    wrong_lookup = fd.Message(
        role=fd.MessageRole.assistant,
        content=None,
        tool_calls=[fd.ToolCall(id="r1", name="lookup_contact", arguments='{"phone": "0"}')],
    )
    model = ScriptedModel([[assistant_message("Unknown caller.")]])
    job = make_job(from_step=0, messages=saved, replacement_output=wrong_lookup)
    ctx = fd.ReplayContext(
        job=job, run=fd.start_recording("call-assistant", job.task_input, client=client)
    )

    result = await fd_agents.replay(ctx, call_assistant(model))

    assert result.final_output == "Unknown caller."
    assert ctx.final_output == "Unknown caller."
    assert len(model.calls) == 1
    resumed = items_to_messages(model.calls[0].input)
    assert [m.role for m in resumed] == ["user", "assistant", "tool"]
    assert resumed[2].tool_call_id == "r1"
    assert [s.index for s in api.steps] == [1, 2]
    assert api.steps[0].output.tool_calls == wrong_lookup.tool_calls


class NamedModels(ModelProvider):
    def __init__(self, models: dict[str, Model]) -> None:
        self.asked: list[str | None] = []
        self._models = models

    def get_model(self, model_name: str | None) -> Model:
        self.asked.append(model_name)
        return self._models[model_name or ""]


async def test_a_replay_runs_with_the_model_override(client: FirstDominoClient) -> None:
    strong = ScriptedModel([[assistant_message("Handled.")]])
    provider = NamedModels({"strong-model": strong})
    ctx = fd.ReplayContext(
        job=make_job(from_step=0, model_override="strong-model"),
        run=fd.RecordedRun(client, None),
    )

    await fd_agents.replay(ctx, call_assistant(), run_config=RunConfig(model_provider=provider))

    assert provider.asked == ["strong-model"]
    assert len(strong.calls) == 1


def test_items_and_messages_round_trip() -> None:
    items = [
        {"role": "user", "content": "Incoming call"},
        {"type": "reasoning", "id": "rs_1", "summary": []},
        {"role": "assistant", "content": "Checking."},
        {"type": "function_call", "call_id": "c1", "name": "lookup_contact", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "c1", "output": "ok"},
    ]

    messages = items_to_messages(items)

    assert [m.role for m in messages] == ["user", "assistant", "tool"]
    assert messages[1].content == "Checking."
    assert [c.id for c in messages[1].tool_calls or []] == ["c1"]
    assert messages_to_items(messages) == [items[0], *items[2:]]
