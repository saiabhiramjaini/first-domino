import pytest

from fd_demo_agent.bugs import PLANTED_BUGS, BugKind, PlantedBug
from fd_demo_agent.messages import function_calls
from fd_demo_agent.success import FailureReason, check_booking
from fd_demo_agent.tasks import get_task
from fd_demo_agent.toolbox import TOOL_ARGUMENTS, ToolBox, ToolName
from fd_demo_agent.world import load_world

BOOKING_BUG_FAILURES = {
    "b03": FailureReason.WRONG_TIME,
    "b05": FailureReason.WRONG_PATIENT,
    "b07": FailureReason.WAITLISTED,
    "b08": FailureReason.WRONG_PATIENT,
}


def test_there_is_one_bug_of_each_kind() -> None:
    assert sorted(bug.kind for bug in PLANTED_BUGS) == sorted(BugKind)
    assert len({bug.bug_id for bug in PLANTED_BUGS}) == len(PLANTED_BUGS)


@pytest.mark.parametrize("bug", PLANTED_BUGS, ids=lambda bug: bug.bug_id)
def test_each_bug_names_a_task_and_valid_tool_arguments(bug: PlantedBug) -> None:
    get_task(bug.task_id)
    assert bug.step >= 1
    for call in function_calls(bug.replacement):
        args_model = TOOL_ARGUMENTS[ToolName(call["function"]["name"])]
        args_model.model_validate_json(call["function"]["arguments"])


@pytest.mark.parametrize("bug_id", sorted(BOOKING_BUG_FAILURES))
def test_a_bug_that_books_fails_the_success_check(bug_id: str) -> None:
    bug = next(bug for bug in PLANTED_BUGS if bug.bug_id == bug_id)
    toolbox = ToolBox(load_world())
    toolbox.replay_history([bug.replacement])
    report = check_booking(get_task(bug.task_id), toolbox.booking)
    assert report.failure == BOOKING_BUG_FAILURES[bug_id]


def test_the_invented_doctor_bug_ends_the_run_without_a_booking() -> None:
    bug = next(bug for bug in PLANTED_BUGS if bug.kind == BugKind.INVENTED_DOCTOR)
    assert function_calls(bug.replacement) == []
