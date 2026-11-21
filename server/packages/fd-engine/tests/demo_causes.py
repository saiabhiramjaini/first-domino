"""The demo's planted bug causes, filed one by one the way the API files them."""

from uuid import uuid4

from fd_engine.group import CauseCandidate, CauseGrouper
from fd_shared.enums import CauseCategory
from fd_shared.models import Explanation

DEMO_CAUSES: dict[str, tuple[Explanation, str]] = {
    "b01": (
        Explanation(
            title="Resolved 'tomorrow' one day late",
            summary="The caller asked for tomorrow at 10:00; the agent booked the day after.",
            suggested_fix="Resolve relative dates from the call's date before booking.",
            category=CauseCategory.WRONG_DATE,
        ),
        "add_calendar_event",
    ),
    "b02": (
        Explanation(
            title="Booked 22:00 instead of 10:00",
            summary="The caller asked for 10 AM; the agent saved the event at 22:00.",
            suggested_fix="Convert AM and PM times to 24-hour time explicitly.",
            category=CauseCategory.WRONG_DATE,
        ),
        "add_calendar_event",
    ),
    "b04": (
        Explanation(
            title="Left the reports note off the booking",
            summary="The caller asked to bring previous reports; the event had no note.",
            suggested_fix="Copy every caller instruction into the event notes.",
            category=CauseCategory.BAD_TOOL_ARGS,
        ),
        "add_calendar_event",
    ),
    "b06": (
        Explanation(
            title="Scheduled a callback for a spam caller",
            summary="A known spam number offered a loan; the agent scheduled a callback.",
            suggested_fix="Check the spam list before offering a callback.",
            category=CauseCategory.OTHER,
        ),
        "schedule_callback",
    ),
    "b07": (
        Explanation(
            title="Read the OTP aloud to a scam caller",
            summary="A caller asked for the bank OTP; the agent read it out.",
            suggested_fix="Never share one-time codes with a caller.",
            category=CauseCategory.OTHER,
        ),
        "reply_to_caller",
    ),
}


async def file_all(grouper: CauseGrouper) -> dict[str, str]:
    """Files the demo causes in order, as the API does, and returns the group of each."""
    causes: list[CauseCandidate] = []
    group_of: dict[str, str] = {}
    for bug, (explanation, step_name) in DEMO_CAUSES.items():
        match = await grouper.match(explanation, causes, step_name=step_name)
        found = next((cause for cause in causes if cause.id == match.cause_id), None)
        if found is None:
            found = CauseCandidate(
                id=uuid4(),
                title=explanation.title,
                category=explanation.category,
                step_name=step_name,
                summary=explanation.summary,
            )
            causes.append(found)
        group_of[bug] = found.title
    return group_of
