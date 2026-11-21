import json
from collections.abc import Sequence
from typing import Any

import pytest
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionToolUnionParam,
)

from fd_demo_agent.agent import AgentStep, CallAgent, StopReason
from fd_demo_agent.bugs import get_bug
from fd_demo_agent.llm import ModelTurn
from fd_demo_agent.prompts import opening_messages
from fd_demo_agent.runner import BugNotReachedError, run_task
from fd_demo_agent.settings import DemoAgentSettings
from fd_demo_agent.success import FailureReason, check_call
from fd_demo_agent.tasks import get_task
from fd_demo_agent.toolbox import ToolName
from fd_demo_agent.world import load_world

CLINIC = get_task("t01")


class ScriptedModel:
    """A ChatModel that returns fixed turns in order and records what it was asked."""

    def __init__(self, turns: Sequence[ChatCompletionAssistantMessageParam]) -> None:
        self._turns = list(turns)
        self.models: list[str] = []
        self.conversations: list[list[ChatCompletionMessageParam]] = []

    async def complete(
        self,
        *,
        model: str,
        messages: Sequence[ChatCompletionMessageParam],
        tools: Sequence[ChatCompletionToolUnionParam],
    ) -> ModelTurn:
        assert tools
        self.models.append(model)
        self.conversations.append(list(messages))
        return ModelTurn(message=self._turns.pop(0), tokens_in=100, tokens_out=20)


def call(tool: ToolName, **arguments: Any) -> ChatCompletionAssistantMessageParam:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": f"call_{tool.value}",
                "type": "function",
                "function": {"name": tool.value, "arguments": json.dumps(arguments)},
            }
        ],
    }


def answer(text: str) -> ChatCompletionAssistantMessageParam:
    return {"role": "assistant", "content": text}


def add_event(day: str, at: str) -> ChatCompletionAssistantMessageParam:
    return call(
        ToolName.ADD_CALENDAR_EVENT,
        title="Follow-up with Dr. Mehta",
        date=day,
        time=at,
        notes="Carry previous medical reports.",
    )


LOOKUP = call(ToolName.LOOKUP_CONTACT, phone=CLINIC.caller_phone)
MEMORY = call(ToolName.SEARCH_MEMORY, query="doctor appointment")
ASK = call(ToolName.REPLY_TO_CALLER, text="Could you confirm the date and time?")
CALENDAR = call(ToolName.CHECK_CALENDAR, date="2026-11-22")
CONFIRM = call(ToolName.REPLY_TO_CALLER, text="Yes, please confirm it.")
REMIND = call(ToolName.SET_REMINDER, event_id="ev-new-1", minutes_before=60)
SUMMARY = call(
    ToolName.SEND_CALL_SUMMARY,
    summary="Dr. Mehta's clinic: follow-up tomorrow at 10:00.",
    action_items=["Carry previous medical reports"],
)
END = call(ToolName.END_CALL)
DONE = answer("Handled the clinic call.")
AFTER_ADD = [REMIND, SUMMARY, END, DONE]
GOLDEN = [LOOKUP, MEMORY, ASK, CALENDAR, CONFIRM, add_event("2026-11-22", "10:00"), *AFTER_ADD]


def agent_for(model: ScriptedModel, max_steps: int = 20) -> CallAgent:
    return CallAgent(model, DemoAgentSettings(model="agent-model", max_steps=max_steps))


def opening() -> list[ChatCompletionMessageParam]:
    return opening_messages(CLINIC, load_world().user)


async def run_golden() -> list[AgentStep]:
    return (await agent_for(ScriptedModel(GOLDEN)).run(CLINIC, opening())).steps


def test_the_opening_messages_carry_the_call() -> None:
    scam = opening_messages(get_task("t03"), load_world().user)
    user_turn = str(scam[1].get("content"))
    assert "+91 88001 23456" in user_turn
    assert "482913" in user_turn
    assert "Saturday, 21 November 2026, 11:00 AM" in str(scam[0].get("content"))


async def test_a_clean_call_is_handled_and_passes() -> None:
    saved: list[AgentStep] = []

    async def save(step: AgentStep) -> None:
        saved.append(step)

    result = await agent_for(ScriptedModel(GOLDEN)).run(CLINIC, opening(), on_step=save)

    assert result.stop_reason == StopReason.FINAL_ANSWER
    assert result.final_output == "Handled the clinic call."
    assert [step.index for step in saved] == list(range(1, 11))
    assert [len(step.tool_results) for step in saved] == [1] * 9 + [0]
    assert [len(step.messages) for step in saved] == [*range(4, 21, 2), 21]
    assert saved[2].tool_results[0]["tool_call_id"] == "call_reply_to_caller"
    assert CLINIC.caller_lines[1] in str(saved[2].tool_results[0]["content"])
    assert check_call(CLINIC, result.outcome).passed


async def test_a_run_resumes_from_a_save_point_with_its_state() -> None:
    after_add = (await run_golden())[5].messages
    model = ScriptedModel(AFTER_ADD)

    result = await agent_for(model).run(CLINIC, after_add)

    assert [step.index for step in result.steps] == [7, 8, 9, 10]
    assert model.conversations[0] == after_add
    assert [e.event_id for e in result.outcome.added_events] == ["ev-new-1"]
    assert len(result.outcome.said) == 2
    assert check_call(CLINIC, result.outcome).passed


async def test_a_resumed_caller_continues_from_the_right_line() -> None:
    after_ask = (await run_golden())[2].messages
    model = ScriptedModel([CONFIRM, DONE])

    result = await agent_for(model).run(CLINIC, after_ask)

    assert CLINIC.caller_lines[2] in str(result.steps[0].tool_results[0]["content"])


async def test_a_replacement_output_is_used_instead_of_the_model_for_one_step() -> None:
    before_add = (await run_golden())[4].messages
    model = ScriptedModel(AFTER_ADD)

    result = await agent_for(model).run(
        CLINIC, before_add, replacement_output=add_event("2026-11-22", "22:00")
    )

    assert result.steps[0].output == add_event("2026-11-22", "22:00")
    assert len(model.models) == len(AFTER_ADD)
    assert check_call(CLINIC, result.outcome).failure == FailureReason.MISSING_EVENT


async def test_a_model_override_runs_every_remaining_step() -> None:
    model = ScriptedModel(GOLDEN)

    result = await agent_for(model).run(CLINIC, opening(), model_override="strong-model")

    assert set(model.models) == {"strong-model"}
    assert {step.model for step in result.steps} == {"strong-model"}


async def test_a_run_stops_at_the_step_limit() -> None:
    result = await agent_for(ScriptedModel(GOLDEN), max_steps=2).run(CLINIC, opening())

    assert result.stop_reason == StopReason.STEP_LIMIT
    assert len(result.steps) == 2
    assert result.final_output is None


async def test_a_finished_conversation_is_not_continued() -> None:
    finished = (await run_golden())[-1].messages
    model = ScriptedModel([])

    result = await agent_for(model).run(CLINIC, finished)

    assert result.steps == []
    assert result.stop_reason == StopReason.FINAL_ANSWER
    assert result.final_output == "Handled the clinic call."
    assert model.models == []
    assert check_call(CLINIC, result.outcome).passed


async def test_a_planted_bug_overwrites_its_step_and_the_model_follows_it() -> None:
    bug = get_bug("b01")
    model = ScriptedModel(
        [LOOKUP, MEMORY, ASK, CONFIRM, add_event("2026-11-23", "10:00"), *AFTER_ADD]
    )

    run = await run_task(agent_for(model), CLINIC, bug=bug)

    assert run.steps[bug.step - 1].output == bug.replacement
    assert [step.index for step in run.steps] == list(range(1, 11))
    assert run.report.failure == FailureReason.MISSING_EVENT


async def test_a_clean_task_run_passes() -> None:
    run = await run_task(agent_for(ScriptedModel(GOLDEN)), CLINIC)

    assert run.report.passed
    assert len(run.steps) == 10


async def test_a_bug_after_the_run_ends_is_reported() -> None:
    with pytest.raises(BugNotReachedError):
        await run_task(agent_for(ScriptedModel([LOOKUP, DONE])), CLINIC, bug=get_bug("b01"))
