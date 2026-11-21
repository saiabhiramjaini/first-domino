"""Per-call sandbox: the scripted caller and every change the assistant makes during one run."""

from collections.abc import Sequence
from datetime import date, time

from pydantic import BaseModel, ConfigDict

from fd_demo_agent.world import CalendarEvent, World

HANGUP_LINE = "[caller hung up]"


class _Record(BaseModel):
    model_config = ConfigDict(frozen=True)


class Reminder(_Record):
    """A reminder before a calendar event."""

    event_id: str
    minutes_before: int


class Callback(_Record):
    """A call the user should make back."""

    phone: str
    contact_name: str | None
    date: date
    time: time
    reason: str


class BlockedCaller(_Record):
    """A number the assistant blocked."""

    phone: str
    reason: str


class CallSummary(_Record):
    """The note the user gets after the call."""

    summary: str
    action_items: list[str]


class CallOutcome(_Record):
    """Everything a run changed, which is what the success check reads."""

    added_events: list[CalendarEvent]
    moved_events: list[CalendarEvent]
    reminders: list[Reminder]
    callbacks: list[Callback]
    blocked: list[BlockedCaller]
    said: list[str]
    summary: CallSummary | None
    ended: bool


class CallSandbox:
    """Holds one run's calendar copy, records and the scripted caller.

    The caller's next line depends only on how many times the assistant has spoken,
    never on what it said, so replays of the same steps hear the same lines.
    """

    def __init__(self, world: World, caller_lines: Sequence[str]) -> None:
        self._calendar = dict(world.calendar)
        self._original_ids = frozenset(world.calendar)
        self._added_ids: list[str] = []
        self._moved_ids: list[str] = []
        self._caller_lines = tuple(caller_lines)
        self._said: list[str] = []
        self._reminders: list[Reminder] = []
        self._callbacks: list[Callback] = []
        self._blocked: list[BlockedCaller] = []
        self._summary: CallSummary | None = None
        self._ended = False

    @property
    def ended(self) -> bool:
        """Whether the assistant has ended the call."""
        return self._ended

    @property
    def summary(self) -> CallSummary | None:
        """The call summary, once sent."""
        return self._summary

    def event(self, event_id: str) -> CalendarEvent | None:
        """Return an event as it stands in this run, or None."""
        return self._calendar.get(event_id)

    def events_on(self, day: date) -> list[CalendarEvent]:
        """Return the events on one date, earliest first."""
        return sorted((e for e in self._calendar.values() if e.date == day), key=lambda e: e.time)

    def say(self, text: str) -> str:
        """Record what the assistant told the caller and return the caller's next line."""
        self._said.append(text)
        turn = len(self._said)
        return self._caller_lines[turn] if turn < len(self._caller_lines) else HANGUP_LINE

    def add_event(self, title: str, day: date, at: time, notes: str) -> CalendarEvent:
        """Add an event with the next sequential id, such as `ev-new-1`."""
        event_id = f"ev-new-{len(self._added_ids) + 1}"
        event = CalendarEvent(event_id=event_id, title=title, date=day, time=at, notes=notes)
        self._calendar[event_id] = event
        self._added_ids.append(event_id)
        return event

    def move_event(self, event: CalendarEvent, day: date, at: time) -> CalendarEvent:
        """Move an event to a new date and time."""
        moved = event.model_copy(update={"date": day, "time": at})
        self._calendar[event.event_id] = moved
        if event.event_id in self._original_ids and event.event_id not in self._moved_ids:
            self._moved_ids.append(event.event_id)
        return moved

    def add_reminder(self, reminder: Reminder) -> None:
        """Store a reminder."""
        self._reminders.append(reminder)

    def add_callback(self, callback: Callback) -> None:
        """Store a callback."""
        self._callbacks.append(callback)

    def block(self, blocked: BlockedCaller) -> None:
        """Store a blocked number."""
        self._blocked.append(blocked)

    def send_summary(self, summary: CallSummary) -> None:
        """Store the call summary."""
        self._summary = summary

    def end(self) -> None:
        """Mark the call as ended."""
        self._ended = True

    def outcome(self) -> CallOutcome:
        """Return a snapshot of everything this run changed."""
        return CallOutcome(
            added_events=[self._calendar[event_id] for event_id in self._added_ids],
            moved_events=[self._calendar[event_id] for event_id in self._moved_ids],
            reminders=list(self._reminders),
            callbacks=list(self._callbacks),
            blocked=list(self._blocked),
            said=list(self._said),
            summary=self._summary,
            ended=self._ended,
        )
