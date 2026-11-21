"""Planted bug definitions used to build the benchmark dataset.

A planted bug is data: the call, the step whose model output is overwritten, and the
replacement output. Step numbers follow the procedure in the system prompt (look up the
caller, search memory, talk, act, summarise, end). The replacement's content states the
mistaken belief, so the later steps the model writes stay consistent with it.
"""

import json
from dataclasses import dataclass
from enum import StrEnum

from openai.types.chat import ChatCompletionAssistantMessageParam

from fd_demo_agent.toolbox import ToolName


class BugKind(StrEnum):
    """The kind of mistake a planted bug makes."""

    TOMORROW_AS_DAY_AFTER = "tomorrow_as_day_after"
    AM_AS_PM = "am_as_pm"
    WRONG_NEAR_DUPLICATE = "wrong_near_duplicate"
    DROPPED_INSTRUCTION = "dropped_instruction"
    REMINDER_DAY_BEFORE = "reminder_day_before"
    SPAM_AS_GENUINE = "spam_as_genuine"
    OTP_SHARED = "otp_shared"
    CALLBACK_WRONG_PERSON = "callback_wrong_person"


@dataclass(frozen=True, slots=True)
class PlantedBug:
    """Overwrite one step of a call's run with a wrong output."""

    bug_id: str
    task_id: str
    kind: BugKind
    step: int
    replacement: ChatCompletionAssistantMessageParam


def _turn(
    bug_id: str,
    content: str | None,
    tool: ToolName | None = None,
    arguments: dict[str, str | int] | None = None,
) -> ChatCompletionAssistantMessageParam:
    turn: ChatCompletionAssistantMessageParam = {"role": "assistant", "content": content}
    if tool is not None:
        turn["tool_calls"] = [
            {
                "id": f"call_planted_{bug_id}",
                "type": "function",
                "function": {"name": tool.value, "arguments": json.dumps(arguments or {})},
            }
        ]
    return turn


def _bug(
    bug_id: str,
    task_id: str,
    kind: BugKind,
    step: int,
    content: str | None,
    tool: ToolName | None = None,
    arguments: dict[str, str | int] | None = None,
) -> PlantedBug:
    replacement = _turn(bug_id, content, tool, arguments)
    return PlantedBug(bug_id, task_id, kind, step, replacement)


REPORTS_NOTE = "Carry previous medical reports."

PLANTED_BUGS: tuple[PlantedBug, ...] = (
    _bug(
        "b01",
        "t01",
        BugKind.TOMORROW_AS_DAY_AFTER,
        5,
        "Tomorrow is Monday, 23 November, so I will add the appointment on that date.",
        ToolName.ADD_CALENDAR_EVENT,
        {
            "title": "Follow-up with Dr. Mehta",
            "date": "2026-11-23",
            "time": "10:00",
            "notes": REPORTS_NOTE,
        },
    ),
    _bug(
        "b02",
        "t01",
        BugKind.AM_AS_PM,
        6,
        "The clinic said 10 o'clock, so I will add the appointment at 22:00.",
        ToolName.ADD_CALENDAR_EVENT,
        {
            "title": "Follow-up with Dr. Mehta",
            "date": "2026-11-22",
            "time": "22:00",
            "notes": REPORTS_NOTE,
        },
    ),
    _bug(
        "b03",
        "t10",
        BugKind.WRONG_NEAR_DUPLICATE,
        4,
        "Laxmi Narayana is saved as Lakshmi, so the callback goes to her.",
        ToolName.SCHEDULE_CALLBACK,
        {
            "contact": "c-lakshmi",
            "date": "2026-11-23",
            "time": "10:00",
            "reason": "Confirm the sherwani measurements",
        },
    ),
    _bug(
        "b04",
        "t01",
        BugKind.DROPPED_INSTRUCTION,
        6,
        None,
        ToolName.ADD_CALENDAR_EVENT,
        {
            "title": "Follow-up with Dr. Mehta",
            "date": "2026-11-22",
            "time": "10:00",
            "notes": "Arrive 10 minutes early.",
        },
    ),
    _bug(
        "b05",
        "t06",
        BugKind.REMINDER_DAY_BEFORE,
        7,
        "Arjun likes a reminder the day before school meetings.",
        ToolName.SET_REMINDER,
        {"event_id": "ev-new-1", "minutes_before": 1440},
    ),
    _bug(
        "b06",
        "t02",
        BugKind.SPAM_AS_GENUINE,
        3,
        "This is a genuine offer from a lender and Arjun may want it, so I will schedule a "
        "callback instead of blocking the number.",
        ToolName.SCHEDULE_CALLBACK,
        {
            "contact": "+91 14045 67890",
            "date": "2026-11-21",
            "time": "18:30",
            "reason": "Personal loan offer",
        },
    ),
    _bug(
        "b07",
        "t03",
        BugKind.OTP_SHARED,
        3,
        "The caller is verifying the account, so I will read out the OTP.",
        ToolName.REPLY_TO_CALLER,
        {"text": "Sure, the OTP is 482913."},
    ),
    _bug(
        "b08",
        "t07",
        BugKind.CALLBACK_WRONG_PERSON,
        4,
        "Srinivasa Rao asked Arjun to call back after 6 about the Goa trip.",
        ToolName.SCHEDULE_CALLBACK,
        {
            "contact": "c-srinivasa-rao",
            "date": "2026-11-21",
            "time": "18:30",
            "reason": "Goa trip plan",
        },
    ),
)

_BY_ID = {bug.bug_id: bug for bug in PLANTED_BUGS}


def get_bug(bug_id: str) -> PlantedBug:
    """Return the planted bug with this id.

    Raises:
        KeyError: No bug has this id.
    """
    return _BY_ID[bug_id]
