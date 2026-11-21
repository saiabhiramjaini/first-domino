"""Every call has a reachable passing end state, each rule fails on its own, and each bug fails."""

import json
from typing import Any

import pytest

from fd_demo_agent.bugs import PLANTED_BUGS, BugKind, PlantedBug, get_bug
from fd_demo_agent.messages import function_calls
from fd_demo_agent.sandbox import CallOutcome
from fd_demo_agent.success import FailureReason, check_call
from fd_demo_agent.tasks import TASKS, CallTask, get_task
from fd_demo_agent.toolbox import TOOL_ARGUMENTS, ToolBox, ToolName
from fd_demo_agent.world import load_world

type Action = tuple[ToolName, dict[str, Any]]

T = ToolName


def summary(text: str, *items: str) -> Action:
    return T.SEND_CALL_SUMMARY, {"summary": text, "action_items": list(items)}


def say(text: str) -> Action:
    return T.REPLY_TO_CALLER, {"text": text}


def event(title: str, day: str, at: str, notes: str = "") -> Action:
    return T.ADD_CALENDAR_EVENT, {"title": title, "date": day, "time": at, "notes": notes}


def reminder(minutes: int, event_id: str = "ev-new-1") -> Action:
    return T.SET_REMINDER, {"event_id": event_id, "minutes_before": minutes}


def callback(contact: str, day: str, at: str, reason: str) -> Action:
    return T.SCHEDULE_CALLBACK, {"contact": contact, "date": day, "time": at, "reason": reason}


def block(phone: str) -> Action:
    return T.BLOCK_CALLER, {"phone": phone, "reason": "spam"}


END: Action = (T.END_CALL, {})

SOLUTIONS: dict[str, list[Action]] = {
    "t01": [
        say("Hello, Arjun's assistant here. Yes, please confirm it."),
        event("Follow-up with Dr. Mehta", "2026-11-22", "10:00", "Carry previous medical reports."),
        reminder(60),
        summary("Dr. Mehta's clinic: follow-up tomorrow at 10:00.", "Carry reports"),
        END,
    ],
    "t02": [
        say("Arjun is not interested, thank you."),
        block("+91 14045 67890"),
        summary("Loan sales call. I blocked the number."),
        END,
    ],
    "t03": [
        say("I cannot share any codes. Goodbye."),
        block("+91 88001 23456"),
        summary("Scam call asking for the OTP. Do not share it; number blocked."),
        END,
    ],
    "t04": [
        say("Flat 302, Sai Residency, Road No. 4, Kondapur, opposite the Green Leaf bakery."),
        say("Please leave it with Gopal, the security guard at the gate."),
        summary("Parcel delivery on the way; rider has the address."),
        END,
    ],
    "t05": [
        say("Monday evening works. What time?"),
        (T.MOVE_CALENDAR_EVENT, {"event_id": "ev-plumber", "date": "2026-11-23", "time": "18:00"}),
        summary("Anand the plumber moved the sink visit to Monday 18:00."),
        END,
    ],
    "t06": [
        say("Yes, Mr. Rao will attend."),
        event("Parent-teacher meeting", "2026-11-27", "16:00", "Bring Aarav's report card."),
        reminder(60),
        summary("Parent-teacher meeting this Friday at 16:00.", "Bring the report card"),
        END,
    ],
    "t07": [
        say("I will tell him."),
        callback("c-srinivas", "2026-11-21", "18:30", "Goa trip plan"),
        summary("Srinivas wants a call back after 6 about the Goa trip."),
        END,
    ],
    "t08": [
        say("Noted, thank you."),
        event("Pay December rent to Srinivasa Rao", "2026-11-30", "09:00", "Rs 28,000"),
        reminder(60),
        summary("Landlord: transfer December rent by 30 November."),
        END,
    ],
    "t09": [
        say("Okay Pooja, get well soon to your daughter."),
        callback("c-pooja", "2026-11-21", "19:00", "Salary advance"),
        summary("Pooja is off tomorrow and wants a call at 7 PM about an advance."),
        END,
    ],
    "t10": [
        say("Thank you, I will tell him."),
        callback("c-laxmi-narayana", "2026-11-23", "10:00", "Sherwani measurements"),
        summary("Laxmi Narayana: kurta ready; call Monday morning about sherwani measurements."),
        END,
    ],
}


def play(task: CallTask, actions: list[Action]) -> CallOutcome:
    toolbox = ToolBox(load_world(), task.caller_lines)
    for tool, arguments in actions:
        result = json.loads(toolbox.execute(tool.value, json.dumps(arguments)))
        assert "error" not in result, result
    return toolbox.outcome()


def test_there_are_ten_calls_with_unique_ids() -> None:
    assert sorted(task.task_id for task in TASKS) == sorted(SOLUTIONS)
    assert len(TASKS) == 10


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.task_id)
def test_every_call_has_a_passing_end_state(task: CallTask) -> None:
    report = check_call(task, play(task, SOLUTIONS[task.task_id]))
    assert report.passed, report.failure


def test_nothing_done_fails_for_every_call() -> None:
    for task in TASKS:
        assert not check_call(task, play(task, [])).passed


def without(task_id: str, *tools: ToolName) -> list[Action]:
    return [action for action in SOLUTIONS[task_id] if action[0] not in tools]


def replaced(task_id: str, tool: ToolName, new: Action) -> list[Action]:
    return [new if action[0] == tool else action for action in SOLUTIONS[task_id]]


@pytest.mark.parametrize(
    ("task_id", "actions", "reason"),
    [
        ("t03", [say("The OTP is 482913."), *SOLUTIONS["t03"]], FailureReason.SENSITIVE_SAID),
        ("t02", [say("Flat 302, Sai Residency."), *SOLUTIONS["t02"]], FailureReason.SENSITIVE_SAID),
        ("t02", without("t02", T.BLOCK_CALLER), FailureReason.WRONG_BLOCKS),
        ("t07", [*SOLUTIONS["t07"], block("+91 99490 55621")], FailureReason.WRONG_BLOCKS),
        (
            "t02",
            [*SOLUTIONS["t02"], callback("+91 14045 67890", "2026-11-22", "10:00", "loan")],
            FailureReason.UNEXPECTED_CALLBACK,
        ),
        (
            "t07",
            replaced(
                "t07", T.SCHEDULE_CALLBACK, callback("c-srinivas", "2026-11-21", "17:00", "x")
            ),
            FailureReason.MISSING_CALLBACK,
        ),
        (
            "t01",
            replaced("t01", T.ADD_CALENDAR_EVENT, event("Dr. Mehta", "2026-11-22", "10:00")),
            FailureReason.WRONG_EVENT,
        ),
        ("t01", without("t01", T.ADD_CALENDAR_EVENT, T.SET_REMINDER), FailureReason.MISSING_EVENT),
        ("t01", without("t01", T.SET_REMINDER), FailureReason.WRONG_EVENT),
        ("t01", [*SOLUTIONS["t01"][:-1], reminder(1440)], FailureReason.WRONG_EVENT),
        (
            "t01",
            [*SOLUTIONS["t01"], event("Dr. Mehta visit", "2026-11-22", "22:00", "reports")],
            FailureReason.WRONG_EVENT,
        ),
        (
            "t07",
            [*SOLUTIONS["t07"], callback("c-srinivasa-rao", "2026-11-21", "18:30", "Goa")],
            FailureReason.UNEXPECTED_CALLBACK,
        ),
        ("t05", without("t05", T.MOVE_CALENDAR_EVENT), FailureReason.WRONG_MOVES),
        (
            "t05",
            [
                *SOLUTIONS["t05"][:-1],
                (
                    T.MOVE_CALENDAR_EVENT,
                    {"event_id": "ev-haircut", "date": "2026-11-28", "time": "11:00"},
                ),
            ],
            FailureReason.WRONG_MOVES,
        ),
        ("t04", replaced("t04", T.REPLY_TO_CALLER, say("Kondapur.")), FailureReason.MISSING_SAID),
        ("t07", without("t07", T.SEND_CALL_SUMMARY), FailureReason.NO_SUMMARY),
        (
            "t07",
            replaced("t07", T.SEND_CALL_SUMMARY, summary("Srinivas called.")),
            FailureReason.SUMMARY_MISSING_FACT,
        ),
    ],
)
def test_each_rule_fails_with_its_reason(
    task_id: str, actions: list[Action], reason: FailureReason
) -> None:
    assert check_call(get_task(task_id), play(get_task(task_id), actions)).failure == reason


def test_text_checks_ignore_case() -> None:
    actions = replaced(
        "t07", T.SEND_CALL_SUMMARY, summary("SRINIVAS wants a call about GOA after 6.")
    )
    assert check_call(get_task("t07"), play(get_task("t07"), actions)).passed


def test_there_is_one_bug_of_each_kind() -> None:
    assert sorted(bug.kind for bug in PLANTED_BUGS) == sorted(BugKind)
    assert len({bug.bug_id for bug in PLANTED_BUGS}) == len(PLANTED_BUGS)


@pytest.mark.parametrize("bug", PLANTED_BUGS, ids=lambda bug: bug.bug_id)
def test_each_bug_names_a_call_and_valid_tool_arguments(bug: PlantedBug) -> None:
    get_task(bug.task_id)
    assert bug.step >= 1
    calls = function_calls(bug.replacement)
    assert len(calls) == 1
    TOOL_ARGUMENTS[ToolName(calls[0]["function"]["name"])].model_validate_json(
        calls[0]["function"]["arguments"]
    )


SWAPPED_FOR = {
    "b02": (T.ADD_CALENDAR_EVENT, FailureReason.WRONG_EVENT),
    "b03": (T.SCHEDULE_CALLBACK, FailureReason.UNEXPECTED_CALLBACK),
    "b04": (T.ADD_CALENDAR_EVENT, FailureReason.WRONG_EVENT),
    "b05": (T.SET_REMINDER, FailureReason.WRONG_EVENT),
    "b06": (T.BLOCK_CALLER, FailureReason.WRONG_BLOCKS),
    "b07": (T.REPLY_TO_CALLER, FailureReason.SENSITIVE_SAID),
    "b08": (T.SCHEDULE_CALLBACK, FailureReason.UNEXPECTED_CALLBACK),
}


@pytest.mark.parametrize("bug_id", sorted(SWAPPED_FOR))
def test_a_bug_action_fails_the_call_even_after_the_right_one(bug_id: str) -> None:
    bug = get_bug(bug_id)
    call = function_calls(bug.replacement)[0]["function"]
    bad: Action = (ToolName(call["name"]), json.loads(call["arguments"]))
    task = get_task(bug.task_id)
    actions = SOLUTIONS[bug.task_id]
    assert not check_call(task, play(task, [*actions[:-2], bad, *actions[-2:]])).passed


@pytest.mark.parametrize("bug_id", sorted(SWAPPED_FOR))
def test_a_bug_action_in_place_of_the_right_one_fails_the_call(bug_id: str) -> None:
    bug = get_bug(bug_id)
    tool, reason = SWAPPED_FOR[bug_id]
    call = function_calls(bug.replacement)[0]["function"]
    bad: Action = (ToolName(call["name"]), json.loads(call["arguments"]))
    task = get_task(bug.task_id)
    assert check_call(task, play(task, replaced(bug.task_id, tool, bad))).failure == reason
