"""Planted bug definitions used to build the benchmark dataset.

A planted bug is data: the task, the step whose model output is overwritten, and the
replacement output. Step numbers follow the procedure in the system prompt (1 search,
2 check the fee, 3 list slots, 4 book, 5 confirm). The replacement's content states the
mistaken belief, so the later steps the model writes stay consistent with it.
"""

import json
from dataclasses import dataclass
from enum import StrEnum

from openai.types.chat import ChatCompletionAssistantMessageParam

from fd_demo_agent.toolbox import ToolName


class BugKind(StrEnum):
    """The kind of mistake a planted bug makes."""

    WRONG_DATE = "wrong_date"
    WRONG_BRANCH = "wrong_branch"
    WRONG_TIME_WINDOW = "wrong_time_window"
    WRONG_FEE = "wrong_fee"
    SWAPPED_ARGUMENTS = "swapped_arguments"
    INVENTED_DOCTOR = "invented_doctor"
    WAITLIST_AS_BOOKED = "waitlist_as_booked"
    MISSPELLED_NAME = "misspelled_name"


@dataclass(frozen=True, slots=True)
class PlantedBug:
    """Overwrite one step of a task's run with a wrong output."""

    bug_id: str
    task_id: str
    kind: BugKind
    step: int
    replacement: ChatCompletionAssistantMessageParam


def _turn(
    bug_id: str,
    content: str | None,
    tool: ToolName | None = None,
    arguments: dict[str, str] | None = None,
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
    arguments: dict[str, str] | None = None,
) -> PlantedBug:
    replacement = _turn(bug_id, content, tool, arguments)
    return PlantedBug(bug_id, task_id, kind, step, replacement)


PLANTED_BUGS: tuple[PlantedBug, ...] = (
    _bug(
        "b01",
        "t07",
        BugKind.WRONG_DATE,
        3,
        "Tomorrow is Monday, 23 November, so I will look at that day.",
        ToolName.LIST_SLOTS,
        {"doctor_id": "d-kiran-goud-mdp", "date": "2026-11-23"},
    ),
    _bug(
        "b02",
        "t01",
        BugKind.WRONG_BRANCH,
        2,
        "Dr. Anil Mehta at Arogya Clinic Madhapur is the doctor the user asked for.",
        ToolName.CHECK_FEE,
        {"doctor_id": "d-anil-mehta-mdp"},
    ),
    _bug(
        "b03",
        "t05",
        BugKind.WRONG_TIME_WINDOW,
        4,
        "15:00 is the closest slot to the evening, so I will book it.",
        ToolName.BOOK_APPOINTMENT,
        {"slot_id": "s-venkat-rao-wfd-1123-1500", "patient_name": "Ramesh Babu"},
    ),
    _bug(
        "b04",
        "t02",
        BugKind.WRONG_FEE,
        3,
        "Dr. Sneha Kulkarni's fee is ₹450, within the ₹600 budget.",
        ToolName.LIST_SLOTS,
        {"doctor_id": "d-sneha-kulkarni-ind", "date": "2026-11-27"},
    ),
    _bug(
        "b05",
        "t09",
        BugKind.SWAPPED_ARGUMENTS,
        4,
        None,
        ToolName.BOOK_APPOINTMENT,
        {"slot_id": "s-farhan-qureshi-bjh-1127-1030", "patient_name": "Farhan Qureshi"},
    ),
    _bug(
        "b06",
        "t06",
        BugKind.INVENTED_DOCTOR,
        2,
        "Booked Dr. Rohan Shetty, orthopaedist at Nandi Health Centre Jayanagar, on "
        "Wednesday 25 November at 09:30 for Akhilesh Sharma.",
    ),
    _bug(
        "b07",
        "t03",
        BugKind.WAITLIST_AS_BOOKED,
        4,
        "13:00 is open, so I will book it.",
        ToolName.BOOK_APPOINTMENT,
        {"slot_id": "s-anjali-varma-bjh-1126-1300", "patient_name": "Akhilesh Kumar"},
    ),
    _bug(
        "b08",
        "t08",
        BugKind.MISSPELLED_NAME,
        4,
        None,
        ToolName.BOOK_APPOINTMENT,
        {"slot_id": "s-kavitha-murthy-jyn-1124-1030", "patient_name": "Laxmi Narayanan"},
    ),
)

_BY_ID = {bug.bug_id: bug for bug in PLANTED_BUGS}


def get_bug(bug_id: str) -> PlantedBug:
    """Return the planted bug with this id.

    Raises:
        KeyError: No bug has this id.
    """
    return _BY_ID[bug_id]
