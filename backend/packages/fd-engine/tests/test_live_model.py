"""Opt-in smoke test of every model call against the real model.

Skipped unless `FD_ENGINE_LIVE_TESTS=1`. Needs `OPENAI_API_KEY` and `FD_ENGINE_STRONG_MODEL`
(from the environment or `backend/.env`). Run it from `backend/`:
`FD_ENGINE_LIVE_TESTS=1 uv run pytest packages/fd-engine/tests/test_live_model.py`.
"""

import json
from uuid import uuid4

import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict

from fd_engine.baseline import BaselineJudge
from fd_engine.explain import LlmExplainer, unexplained
from fd_engine.fix import LlmStepFixer
from fd_engine.group import CauseCandidate, CauseGrouper
from fd_engine.llm import Llm
from fd_engine.settings import EngineSettings
from fd_shared.enums import CauseCategory, MessageRole, RunStatus
from fd_shared.models import Message, RunView, StepView, TaskInput, ToolCall


class LiveTestSettings(BaseSettings):
    """Whether to run tests that call the real model."""

    model_config = SettingsConfigDict(env_prefix="FD_ENGINE_", extra="ignore")

    live_tests: bool = False


pytestmark = pytest.mark.skipif(
    not LiveTestSettings().live_tests, reason="set FD_ENGINE_LIVE_TESTS=1 to call the real model"
)

BROKEN_STEP = 3
CLINIC_PHONE = "+91 98490 11223"


def _call(call_id: str, name: str, **arguments: object) -> ToolCall:
    return ToolCall(id=call_id, name=name, arguments=json.dumps(arguments))


def _tool(call_id: str, content: object) -> Message:
    return Message(role=MessageRole.TOOL, content=json.dumps(content), tool_call_id=call_id)


def _step(index: int, call: ToolCall, result: object) -> StepView:
    return StepView(
        index=index,
        model="agent-model",
        output=Message(role=MessageRole.ASSISTANT, content=None, tool_calls=[call]),
        tool_results=[_tool(call.id, result)],
    )


def clinic_call() -> tuple[RunView, list[StepView]]:
    """A call-assistant run that booked "tomorrow at 10" on the day after tomorrow."""
    run = RunView(
        id=uuid4(),
        agent_name="call-assistant",
        task_input=TaskInput(
            prompt=f"Incoming call from {CLINIC_PHONE}. Answer it for Arjun Rao and take the "
            "actions the call needs. Today is Saturday 21 Nov 2026, 11:00 AM IST.",
            metadata={"task_id": "clinic-confirm"},
        ),
        step_count=5,
        status=RunStatus.FAILED,
        final_output=None,
    )
    steps = [
        _step(
            1,
            _call("c1", "lookup_contact", phone=CLINIC_PHONE),
            {"name": "Dr. Mehta's Clinic", "relationship": "family doctor"},
        ),
        _step(
            2,
            _call(
                "c2", "reply_to_caller", text="Hello, this is Arjun's assistant. How can I help?"
            ),
            {
                "caller": "Hi, calling from Dr. Mehta's clinic to confirm Arjun's appointment "
                "tomorrow at 10 in the morning. Please ask him to bring his old reports."
            },
        ),
        _step(
            BROKEN_STEP,
            _call(
                "c3",
                "add_calendar_event",
                title="Dr. Mehta appointment",
                date="2026-11-23",
                time="10:00",
                notes="Bring previous medical reports",
            ),
            {"event_id": "ev_7", "date": "2026-11-23", "time": "10:00"},
        ),
        _step(4, _call("c4", "set_reminder", event_id="ev_7", minutes_before=60), {"ok": True}),
        _step(
            5,
            _call(
                "c5",
                "send_call_summary",
                summary="Dr. Mehta's clinic confirmed the appointment on Mon 23 Nov at 10 AM.",
                action_items=["Bring previous medical reports"],
            ),
            {"ok": True},
        ),
    ]
    return run, steps


SPAM_PHONE = "+91 14045 55001"


def spam_call() -> tuple[RunView, list[StepView]]:
    """A call-assistant run that offered a callback to a known spam number instead of blocking."""
    run = RunView(
        id=uuid4(),
        agent_name="call-assistant",
        task_input=TaskInput(
            prompt=f"Incoming call from {SPAM_PHONE}. Answer it for Arjun Rao and take the "
            "actions the call needs. Today is Saturday 21 Nov 2026, 11:00 AM IST.",
            metadata={"task_id": "loan-offer"},
        ),
        step_count=3,
        status=RunStatus.FAILED,
        final_output=None,
    )
    steps = [
        _step(
            1,
            _call("s1", "lookup_contact", phone=SPAM_PHONE),
            {"name": None, "known_spam": True, "spam_reason": "loan offers"},
        ),
        _step(
            2,
            _call(
                "s2", "reply_to_caller", text="Hello, this is Arjun's assistant. How can I help?"
            ),
            {"caller": "Sir, you are pre-approved for a 5 lakh personal loan. When can we call?"},
        ),
        _step(
            3,
            _call(
                "s3",
                "schedule_callback",
                contact=SPAM_PHONE,
                date="2026-11-21",
                time="18:00",
                reason="Personal loan offer",
            ),
            {"callback_id": "cb_2"},
        ),
    ]
    return run, steps


@pytest.fixture
def llm() -> Llm:
    return Llm(EngineSettings())  # pyright: ignore[reportCallIssue] fields come from the environment


async def test_fixer_rewrites_the_wrong_date(llm: Llm) -> None:
    run, steps = clinic_call()

    fixed = await LlmStepFixer(llm).fix(run, steps, BROKEN_STEP)

    assert fixed.output is not None
    assert fixed.cost_usd > 0
    calls = fixed.output.tool_calls
    assert [call.name for call in calls] == ["add_calendar_event"]
    assert json.loads(calls[0].arguments)["date"] == "2026-11-22"


@pytest.mark.xfail(
    reason="The engine does not see the agent's tool list until RunView carries tool_names, so "
    "the model may guess a tool name the run never used.",
    strict=False,
)
async def test_fixer_can_switch_to_a_tool_the_run_never_used(llm: Llm) -> None:
    run, steps = spam_call()

    fixed = await LlmStepFixer(llm).fix(run, steps, 3)

    assert fixed.output is not None
    assert "block_caller" in [call.name for call in fixed.output.tool_calls]
    assert "schedule_callback" not in [call.name for call in fixed.output.tool_calls]


async def test_explainer_names_a_date_mistake(llm: Llm) -> None:
    run, steps = clinic_call()
    fix = Message(
        role=MessageRole.ASSISTANT,
        content=None,
        tool_calls=[
            _call(
                "f3",
                "add_calendar_event",
                title="Dr. Mehta appointment",
                date="2026-11-22",
                time="10:00",
                notes="Bring previous medical reports",
            )
        ],
    )

    explained = await LlmExplainer(llm).explain(run, steps, BROKEN_STEP, fix)

    assert explained.explanation != unexplained(BROKEN_STEP)
    assert explained.explanation.category is CauseCategory.WRONG_DATE
    assert explained.cost_usd > 0


async def test_grouper_matches_the_same_mistake(llm: Llm) -> None:
    run, steps = clinic_call()
    explained = await LlmExplainer(llm).explain(run, steps, BROKEN_STEP, None)
    same = CauseCandidate(
        id=uuid4(),
        title="Relative date resolved one day late",
        category=CauseCategory.WRONG_DATE,
        summary="The assistant turned 'tomorrow' into the day after tomorrow when adding an event.",
    )
    other = CauseCandidate(
        id=uuid4(),
        title="Spam caller given a callback",
        category=CauseCategory.WRONG_ENTITY,
        summary="A loan offer from a known spam number got a callback instead of a block.",
    )

    match = await CauseGrouper(llm).match(explained.explanation, [other, same])

    assert match.cause_id == same.id
    assert match.cost_usd > 0


async def test_baseline_names_a_step_of_the_run(llm: Llm) -> None:
    run, steps = clinic_call()

    prediction = await BaselineJudge(llm).predict(run, steps)

    assert prediction.step is not None
    assert 1 <= prediction.step <= len(steps)
    assert prediction.cost_usd > 0
