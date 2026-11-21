import json
from collections.abc import Sequence

import pytest
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionToolUnionParam,
)

from fd_demo_agent.agent import AgentStep, BookingAgent, StopReason
from fd_demo_agent.bugs import get_bug
from fd_demo_agent.llm import ModelTurn
from fd_demo_agent.prompts import opening_messages
from fd_demo_agent.runner import BugNotReachedError, run_task
from fd_demo_agent.sandbox import BookingStatus
from fd_demo_agent.settings import DemoAgentSettings
from fd_demo_agent.success import FailureReason, check_booking
from fd_demo_agent.tasks import get_task
from fd_demo_agent.toolbox import ToolName
from fd_demo_agent.world import load_world


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


def call(tool: ToolName, **arguments: str) -> ChatCompletionAssistantMessageParam:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": f"call_{tool.value}_{len(arguments)}",
                "type": "function",
                "function": {"name": tool.value, "arguments": json.dumps(arguments)},
            }
        ],
    }


def answer(text: str) -> ChatCompletionAssistantMessageParam:
    return {"role": "assistant", "content": text}


SEARCH = call(ToolName.SEARCH_DOCTORS, name="Mehta", area="Kukatpally")
FEE = call(ToolName.CHECK_FEE, doctor_id="d-anil-mehta-kph")
SLOTS = call(ToolName.LIST_SLOTS, doctor_id="d-anil-mehta-kph", date="2026-11-22")
BOOK = call(
    ToolName.BOOK_APPOINTMENT, slot_id="s-anil-mehta-kph-1122-1130", patient_name="Ramesh Rao"
)
DONE = answer("Booked Dr. Anil Mehta, Arogya Kukatpally, Sun 22 Nov 11:30 for Ramesh Rao.")
GOLDEN_T01 = [SEARCH, FEE, SLOTS, BOOK, DONE]


def agent_for(model: ScriptedModel, max_steps: int = 12) -> BookingAgent:
    return BookingAgent(model, DemoAgentSettings(model="agent-model", max_steps=max_steps))


def opening() -> list[ChatCompletionMessageParam]:
    return opening_messages(get_task("t01").prompt, load_world().calendar.today)


async def run_golden() -> list[AgentStep]:
    return (await agent_for(ScriptedModel(GOLDEN_T01)).run(opening())).steps


async def test_a_clean_run_books_and_passes() -> None:
    saved: list[AgentStep] = []

    async def save(step: AgentStep) -> None:
        saved.append(step)

    result = await agent_for(ScriptedModel(GOLDEN_T01)).run(opening(), on_step=save)

    assert result.stop_reason == StopReason.FINAL_ANSWER
    assert result.final_output == DONE.get("content")
    assert [step.index for step in saved] == [1, 2, 3, 4, 5]
    assert [len(step.tool_results) for step in saved] == [1, 1, 1, 1, 0]
    assert [len(step.messages) for step in saved] == [4, 6, 8, 10, 11]
    assert saved[0].tool_results[0]["tool_call_id"] == "call_search_doctors_2"
    assert check_booking(get_task("t01"), result.booking).passed


async def test_a_run_resumes_from_a_save_point_with_its_bookings() -> None:
    after_booking = (await run_golden())[3].messages
    model = ScriptedModel([DONE])

    result = await agent_for(model).run(after_booking)

    assert [step.index for step in result.steps] == [5]
    assert model.conversations == [after_booking]
    assert result.booking is not None
    assert result.booking.slot_id == "s-anil-mehta-kph-1122-1130"


async def test_a_replacement_output_is_used_instead_of_the_model_for_one_step() -> None:
    after_slots = (await run_golden())[2].messages
    waitlist = call(
        ToolName.BOOK_APPOINTMENT, slot_id="s-anil-mehta-kph-1122-1030", patient_name="Ramesh Rao"
    )
    model = ScriptedModel([DONE])

    result = await agent_for(model).run(after_slots, replacement_output=waitlist)

    assert result.steps[0].output == waitlist
    assert len(model.models) == 1
    assert result.booking is not None
    assert result.booking.status == BookingStatus.WAITLISTED
    assert check_booking(get_task("t01"), result.booking).failure == FailureReason.WAITLISTED


async def test_a_model_override_runs_every_remaining_step() -> None:
    model = ScriptedModel(GOLDEN_T01)

    result = await agent_for(model).run(opening(), model_override="strong-model")

    assert set(model.models) == {"strong-model"}
    assert {step.model for step in result.steps} == {"strong-model"}


async def test_a_run_stops_at_the_step_limit() -> None:
    result = await agent_for(ScriptedModel(GOLDEN_T01), max_steps=2).run(opening())

    assert result.stop_reason == StopReason.STEP_LIMIT
    assert len(result.steps) == 2
    assert result.final_output is None


async def test_a_finished_conversation_is_not_continued() -> None:
    finished = (await run_golden())[-1].messages
    model = ScriptedModel([])

    result = await agent_for(model).run(finished)

    assert result.steps == []
    assert result.stop_reason == StopReason.FINAL_ANSWER
    assert result.final_output == DONE.get("content")
    assert model.models == []


async def test_a_planted_bug_overwrites_its_step_and_fails_the_task() -> None:
    bug = get_bug("b02")
    model = ScriptedModel(
        [
            SEARCH,
            call(ToolName.LIST_SLOTS, doctor_id="d-anil-mehta-mdp", date="2026-11-22"),
            call(
                ToolName.BOOK_APPOINTMENT,
                slot_id="s-anil-mehta-mdp-1122-1000",
                patient_name="Ramesh Rao",
            ),
            answer("Booked."),
        ]
    )

    run = await run_task(agent_for(model), get_task("t01"), bug=bug)

    assert run.steps[1].output == bug.replacement
    assert [step.index for step in run.steps] == [1, 2, 3, 4, 5]
    assert run.report.failure == FailureReason.WRONG_DOCTOR


async def test_a_clean_task_run_passes() -> None:
    run = await run_task(agent_for(ScriptedModel(GOLDEN_T01)), get_task("t01"))

    assert run.report.passed
    assert len(run.steps) == 5


async def test_a_bug_after_the_run_ends_is_reported() -> None:
    with pytest.raises(BugNotReachedError):
        await run_task(agent_for(ScriptedModel([DONE])), get_task("t01"), bug=get_bug("b02"))
