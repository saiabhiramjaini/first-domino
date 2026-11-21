"""Typed models of the mock world: the user, contacts, memory, calendar and spam numbers."""

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class UserProfile(_Frozen):
    """The person the assistant answers calls for, and the fixed current time."""

    name: str
    city: str
    now: datetime


class Contact(_Frozen):
    """A saved contact."""

    contact_id: str
    name: str
    phone: str
    relationship: str


class MemoryItem(_Frozen):
    """One fact or preference the user has told the assistant."""

    memory_id: str
    text: str
    tags: tuple[str, ...]


class CalendarEvent(_Frozen):
    """One event on the user's calendar."""

    event_id: str
    title: str
    date: date
    time: time
    notes: str = ""


class SpamNumber(_Frozen):
    """A number known to make spam or scam calls."""

    phone: str
    label: str


class World(_Frozen):
    """The whole mock world, indexed by id."""

    user: UserProfile
    contacts: dict[str, Contact]
    memory: tuple[MemoryItem, ...]
    calendar: dict[str, CalendarEvent]
    spam_numbers: tuple[SpamNumber, ...]

    @property
    def today(self) -> date:
        """The fixed current date."""
        return self.user.now.date()
