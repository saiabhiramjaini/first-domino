"""What a replay from save point 0 starts from, and how a cause names its step."""

from uuid import uuid4

from fd_api.services.snapshots import opening_messages
from fd_api.services.verdicts import step_label
from fd_database import tables
from fd_shared.enums import MessageRole
from fd_shared.models import Message, ToolCall

SYSTEM = Message(role=MessageRole.SYSTEM, content="You are a call assistant.")
USER = Message(role=MessageRole.USER, content="Book tomorrow at 10")
CALL = ToolCall(id="c1", name="add_calendar_event", arguments="{}")
OUTPUT = Message(role=MessageRole.ASSISTANT, content=None, tool_calls=[CALL])
RESULT = Message(role=MessageRole.TOOL, content="ok", tool_call_id="c1")


def _step(output: Message, tool_results: list[Message]) -> tables.Step:
    return tables.Step(
        project_id=uuid4(),
        run_id=uuid4(),
        index=1,
        model="m",
        output=output,
        tool_results=tool_results,
        messages=[SYSTEM, USER, output, *tool_results],
        tokens_in=1,
        tokens_out=1,
        latency_ms=1,
    )


def test_opening_messages_drop_step_one_and_its_tool_results() -> None:
    assert opening_messages(_step(OUTPUT, [RESULT])) == [SYSTEM, USER]


def test_step_label_is_the_first_tool_called() -> None:
    assert step_label(_step(OUTPUT, [RESULT])) == "add_calendar_event"


def test_step_label_without_tools_is_the_role() -> None:
    reply = Message(role=MessageRole.ASSISTANT, content="Done.")

    assert step_label(_step(reply, [])) == "assistant"
