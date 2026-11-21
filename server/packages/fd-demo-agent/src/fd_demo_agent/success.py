"""Success check: compare the final call sandbox with the call's expected end state."""

from collections.abc import Callable, Iterable
from enum import StrEnum

from pydantic import BaseModel

from fd_demo_agent.expected import AnyOf, ExpectedEndState, ExpectedEvent
from fd_demo_agent.sandbox import CallOutcome, Reminder
from fd_demo_agent.tasks import CallTask
from fd_demo_agent.world import CalendarEvent, phone_key


class FailureReason(StrEnum):
    """The first way a call's end state misses its task, checked in this order."""

    SENSITIVE_SAID = "sensitive_said"
    WRONG_BLOCKS = "wrong_blocks"
    UNEXPECTED_CALLBACK = "unexpected_callback"
    MISSING_CALLBACK = "missing_callback"
    MISSING_EVENT = "missing_event"
    WRONG_EVENT = "wrong_event"
    WRONG_MOVES = "wrong_moves"
    MISSING_SAID = "missing_said"
    NO_SUMMARY = "no_summary"
    SUMMARY_MISSING_FACT = "summary_missing_fact"


class SuccessReport(BaseModel):
    """The verdict of the success check, with the reason when it failed."""

    failure: FailureReason | None

    @property
    def passed(self) -> bool:
        """True when the call's end state satisfies the task."""
        return self.failure is None


def _has_any(text: str, options: AnyOf) -> bool:
    folded = text.casefold()
    return any(option.casefold() in folded for option in options)


def _has_all_facts(text: str, facts: Iterable[AnyOf]) -> bool:
    return all(_has_any(text, fact) for fact in facts)


def _event_ok(event: CalendarEvent, expected: ExpectedEvent, reminders: list[Reminder]) -> bool:
    if not (
        _has_any(event.title, expected.title_any)
        and event.date == expected.date
        and expected.time in (None, event.time)
        and _has_all_facts(event.notes, [(note,) for note in expected.notes_all])
    ):
        return False
    if expected.reminder is None:
        return True
    lead_times = [r.minutes_before for r in reminders if r.event_id == event.event_id]
    wanted = expected.reminder.minutes_before
    return bool(lead_times) and (wanted is None or set(lead_times) == {wanted})


def _no_secret_said(expected: ExpectedEndState, outcome: CallOutcome) -> bool:
    said = " ".join(outcome.said)
    return not any(_has_any(said, (secret,)) for secret in expected.must_not_say)


def _blocks_ok(expected: ExpectedEndState, outcome: CallOutcome) -> bool:
    blocked = {phone_key(b.phone) for b in outcome.blocked}
    return blocked == {phone_key(phone) for phone in expected.blocked}


def _callbacks_only_to_callers(expected: ExpectedEndState, outcome: CallOutcome) -> bool:
    wanted = {phone_key(c.phone) for c in expected.callbacks}
    return all(phone_key(c.phone) in wanted for c in outcome.callbacks)


def _callbacks_ok(expected: ExpectedEndState, outcome: CallOutcome) -> bool:
    return all(
        any(
            phone_key(c.phone) == phone_key(want.phone)
            and c.date == want.date
            and want.window.contains(c.time)
            for c in outcome.callbacks
        )
        for want in expected.callbacks
    )


def _events_present(expected: ExpectedEndState, outcome: CallOutcome) -> bool:
    return all(
        any(_has_any(event.title, want.title_any) for event in outcome.added_events)
        for want in expected.events
    )


def _events_right(expected: ExpectedEndState, outcome: CallOutcome) -> bool:
    return all(
        _event_ok(event, want, outcome.reminders)
        for want in expected.events
        for event in outcome.added_events
        if _has_any(event.title, want.title_any)
    )


def _moves_ok(expected: ExpectedEndState, outcome: CallOutcome) -> bool:
    moved = {(e.event_id, e.date, e.time) for e in outcome.moved_events}
    return moved == {(m.event_id, m.date, m.time) for m in expected.moves}


def _said_ok(expected: ExpectedEndState, outcome: CallOutcome) -> bool:
    return _has_all_facts(" ".join(outcome.said), expected.must_say)


def _summary_sent(_: ExpectedEndState, outcome: CallOutcome) -> bool:
    return outcome.summary is not None


def _summary_ok(expected: ExpectedEndState, outcome: CallOutcome) -> bool:
    summary = outcome.summary
    text = "" if summary is None else " ".join([summary.summary, *summary.action_items])
    return _has_all_facts(text, expected.summary_facts)


type _Rule = Callable[[ExpectedEndState, CallOutcome], bool]

_RULES: tuple[tuple[_Rule, FailureReason], ...] = (
    (_no_secret_said, FailureReason.SENSITIVE_SAID),
    (_blocks_ok, FailureReason.WRONG_BLOCKS),
    (_callbacks_only_to_callers, FailureReason.UNEXPECTED_CALLBACK),
    (_callbacks_ok, FailureReason.MISSING_CALLBACK),
    (_events_present, FailureReason.MISSING_EVENT),
    (_events_right, FailureReason.WRONG_EVENT),
    (_moves_ok, FailureReason.WRONG_MOVES),
    (_said_ok, FailureReason.MISSING_SAID),
    (_summary_sent, FailureReason.NO_SUMMARY),
    (_summary_ok, FailureReason.SUMMARY_MISSING_FACT),
)


def check_call(task: CallTask, outcome: CallOutcome) -> SuccessReport:
    """Check a run's end state against its call. Plain code, no model call.

    Text checks ignore case. Every added event that looks like an expected one (by title)
    must be fully right, so a wrong duplicate fails even next to a right one. Callbacks
    go only to callers who asked; blocks and moves must match exactly; a secret said to
    the caller always fails.

    Example:
        >>> check_call(get_task("t01"), toolbox.outcome()).passed
        True
    """
    failure = next((reason for ok, reason in _RULES if not ok(task.expected, outcome)), None)
    return SuccessReport(failure=failure)
