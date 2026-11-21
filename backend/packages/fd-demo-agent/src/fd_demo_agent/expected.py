"""The end state a call should leave, which the success check compares against."""

import datetime as dt

from pydantic import BaseModel, ConfigDict

type AnyOf = tuple[str, ...]
"""Alternatives for one fact: text passes when it contains any of them, ignoring case."""


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class TimeWindow(_Frozen):
    """A part of the day: `start` is inclusive, `end` exclusive."""

    start: dt.time
    end: dt.time

    def contains(self, at: dt.time) -> bool:
        """Return whether a time falls inside the window."""
        return self.start <= at < self.end


class ExpectedReminder(_Frozen):
    """A reminder the event must have. `None` minutes accepts any lead time."""

    minutes_before: int | None = None


class ExpectedEvent(_Frozen):
    """A new event the call must add. Every reminder on it must match `reminder`."""

    title_any: AnyOf
    date: dt.date
    time: dt.time | None = None
    notes_all: tuple[str, ...] = ()
    reminder: ExpectedReminder | None = None


class ExpectedMove(_Frozen):
    """An existing event the call must move. Events not listed must not move."""

    event_id: str
    date: dt.date
    time: dt.time


class ExpectedCallback(_Frozen):
    """A callback the call must schedule."""

    phone: str
    date: dt.date
    window: TimeWindow


class ExpectedEndState(_Frozen):
    """Everything a correct run leaves behind."""

    events: tuple[ExpectedEvent, ...] = ()
    moves: tuple[ExpectedMove, ...] = ()
    callbacks: tuple[ExpectedCallback, ...] = ()
    blocked: tuple[str, ...] = ()
    summary_facts: tuple[AnyOf, ...] = ()
    must_say: tuple[AnyOf, ...] = ()
    must_not_say: tuple[str, ...] = ()
