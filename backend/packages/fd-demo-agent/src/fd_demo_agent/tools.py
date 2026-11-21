"""Mock tools: pure functions over the world data and a per-call sandbox."""

import datetime as dt
import re
from enum import StrEnum

from pydantic import BaseModel, Field

from fd_demo_agent.sandbox import (
    BlockedCaller,
    Callback,
    CallSandbox,
    CallSummary,
    Reminder,
)
from fd_demo_agent.world import PHONE_DIGITS, CalendarEvent, Contact, MemoryItem, World, phone_key

_MIN_QUERY_WORD = 3
_WORD = re.compile(r"[a-z0-9]+")


class ToolErrorCode(StrEnum):
    """Why a tool call did not succeed. The model reads these, so they are plain words."""

    INVALID_ARGUMENTS = "invalid_arguments"
    UNKNOWN_TOOL = "unknown_tool"
    UNKNOWN_EVENT = "unknown_event"
    UNKNOWN_CONTACT = "unknown_contact"
    DATE_IN_PAST = "date_in_past"
    CALL_ENDED = "call_ended"


class ToolError(BaseModel):
    """A tool result that reports a failure instead of data."""

    error: ToolErrorCode
    detail: str


class Done(BaseModel):
    """A tool result that only confirms the action."""

    ok: bool = True


class LookupContactArgs(BaseModel):
    """Look up a phone number in the user's contacts and the known spam list."""

    phone: str


class SearchMemoryArgs(BaseModel):
    """Search what the user has told you: preferences, rules, address, people."""

    query: str = Field(description="A few keywords, e.g. 'doctor appointment'.")


class CheckCalendarArgs(BaseModel):
    """List the user's events on one date."""

    date: dt.date


class ReplyToCallerArgs(BaseModel):
    """Say something to the caller. Returns what the caller says next."""

    text: str = Field(min_length=1)


class AddCalendarEventArgs(BaseModel):
    """Add an event to the user's calendar."""

    title: str = Field(min_length=1)
    date: dt.date
    time: dt.time = Field(description="24-hour time, e.g. '14:30'.")
    notes: str = ""


class MoveCalendarEventArgs(BaseModel):
    """Move an existing event to a new date and time."""

    event_id: str
    date: dt.date
    time: dt.time = Field(description="24-hour time, e.g. '18:00'.")


class SetReminderArgs(BaseModel):
    """Remind the user before an event."""

    event_id: str
    minutes_before: int = Field(ge=1)


class ScheduleCallbackArgs(BaseModel):
    """Ask the user to call someone back at a given time."""

    contact: str = Field(description="A contact_id from lookup_contact, or a phone number.")
    date: dt.date
    time: dt.time = Field(description="24-hour time, e.g. '18:30'.")
    reason: str


class BlockCallerArgs(BaseModel):
    """Block a phone number so it cannot call the user again."""

    phone: str
    reason: str


class SendCallSummaryArgs(BaseModel):
    """Send the user a summary of the call and what to do next."""

    summary: str = Field(min_length=1)
    action_items: list[str] = Field(default_factory=list)


class EndCallArgs(BaseModel):
    """Hang up the call."""


class ContactLookup(BaseModel):
    """What is known about a phone number."""

    phone: str
    contact: Contact | None
    spam_label: str | None


class MemoryHits(BaseModel):
    """Memory items that share a keyword with the query, in a fixed order."""

    memories: list[MemoryItem]


class DaySchedule(BaseModel):
    """The user's events on one date."""

    date: dt.date
    events: list[CalendarEvent]


class CallerLine(BaseModel):
    """What the caller said next."""

    caller: str


def lookup_contact(world: World, args: LookupContactArgs) -> ContactLookup:
    """Match a number against contacts and spam numbers by its last 10 digits."""
    key = phone_key(args.phone)
    contact = next((c for c in world.contacts.values() if phone_key(c.phone) == key), None)
    spam = next((s.label for s in world.spam_numbers if phone_key(s.phone) == key), None)
    return ContactLookup(phone=args.phone, contact=contact, spam_label=spam)


def search_memory(world: World, args: SearchMemoryArgs) -> MemoryHits:
    """Return memory items whose text or tags contain any query word of 3 letters or more."""
    words = {w for w in _WORD.findall(args.query.casefold()) if len(w) >= _MIN_QUERY_WORD}
    hits = [
        item
        for item in world.memory
        if any(word in item.text.casefold() or word in item.tags for word in words)
    ]
    return MemoryHits(memories=hits)


def check_calendar(sandbox: CallSandbox, args: CheckCalendarArgs) -> DaySchedule:
    """Return the run's calendar for one date, including changes made during the call."""
    return DaySchedule(date=args.date, events=sandbox.events_on(args.date))


def reply_to_caller(sandbox: CallSandbox, args: ReplyToCallerArgs) -> CallerLine | ToolError:
    """Speak to the caller and return their next scripted line."""
    if sandbox.ended:
        return ToolError(error=ToolErrorCode.CALL_ENDED, detail="the call has ended")
    return CallerLine(caller=sandbox.say(args.text))


def _past(world: World, day: dt.date) -> ToolError | None:
    if day < world.today:
        return ToolError(error=ToolErrorCode.DATE_IN_PAST, detail=f"today is {world.today}")
    return None


def add_calendar_event(
    world: World, sandbox: CallSandbox, args: AddCalendarEventArgs
) -> CalendarEvent | ToolError:
    """Add an event to the run's calendar."""
    return _past(world, args.date) or sandbox.add_event(
        args.title, args.date, args.time, args.notes
    )


def move_calendar_event(
    world: World, sandbox: CallSandbox, args: MoveCalendarEventArgs
) -> CalendarEvent | ToolError:
    """Move an event in the run's calendar."""
    event = sandbox.event(args.event_id)
    if event is None:
        return ToolError(error=ToolErrorCode.UNKNOWN_EVENT, detail=args.event_id)
    return _past(world, args.date) or sandbox.move_event(event, args.date, args.time)


def set_reminder(sandbox: CallSandbox, args: SetReminderArgs) -> Reminder | ToolError:
    """Add a reminder before an event."""
    if sandbox.event(args.event_id) is None:
        return ToolError(error=ToolErrorCode.UNKNOWN_EVENT, detail=args.event_id)
    reminder = Reminder(event_id=args.event_id, minutes_before=args.minutes_before)
    sandbox.add_reminder(reminder)
    return reminder


def _resolve_contact(world: World, contact: str) -> tuple[str, str | None] | None:
    saved = world.contacts.get(contact)
    if saved is not None:
        return saved.phone, saved.name
    found = lookup_contact(world, LookupContactArgs(phone=contact)).contact
    if found is not None:
        return found.phone, found.name
    if len(phone_key(contact)) == PHONE_DIGITS:
        return contact, None
    return None


def schedule_callback(
    world: World, sandbox: CallSandbox, args: ScheduleCallbackArgs
) -> Callback | ToolError:
    """Add a callback for a contact id or phone number."""
    resolved = _resolve_contact(world, args.contact)
    if resolved is None:
        return ToolError(error=ToolErrorCode.UNKNOWN_CONTACT, detail=args.contact)
    past = _past(world, args.date)
    if past is not None:
        return past
    phone, name = resolved
    callback = Callback(
        phone=phone, contact_name=name, date=args.date, time=args.time, reason=args.reason
    )
    sandbox.add_callback(callback)
    return callback


def block_caller(sandbox: CallSandbox, args: BlockCallerArgs) -> BlockedCaller:
    """Block a number."""
    blocked = BlockedCaller(phone=args.phone, reason=args.reason)
    sandbox.block(blocked)
    return blocked


def send_call_summary(sandbox: CallSandbox, args: SendCallSummaryArgs) -> Done:
    """Send the user the call summary. A later summary replaces an earlier one."""
    sandbox.send_summary(CallSummary(summary=args.summary, action_items=args.action_items))
    return Done()


def end_call(sandbox: CallSandbox) -> Done:
    """Hang up."""
    sandbox.end()
    return Done()
