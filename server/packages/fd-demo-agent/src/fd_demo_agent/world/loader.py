"""Read the world JSON shipped in this package into typed models."""

from functools import cache
from importlib.resources import files

from pydantic import TypeAdapter

from fd_demo_agent.world.models import (
    CalendarEvent,
    Contact,
    MemoryItem,
    SpamNumber,
    UserProfile,
    World,
)

_PACKAGE = "fd_demo_agent.world"
_DATA_DIR = "data"
PHONE_DIGITS = 10


def phone_key(phone: str) -> str:
    """Return the last 10 digits of a phone number, so `+91 98490 11223` matches `9849011223`."""
    digits = "".join(char for char in phone if char.isdigit())
    return digits[-PHONE_DIGITS:]


def _read[T](name: str, adapter: TypeAdapter[T]) -> T:
    return adapter.validate_json(files(_PACKAGE).joinpath(_DATA_DIR, name).read_bytes())


@cache
def load_world() -> World:
    """Load the mock world once per process.

    Example:
        >>> load_world().user.name
        'Arjun Rao'
    """
    contacts = _read("contacts.json", TypeAdapter(list[Contact]))
    phones = [phone_key(contact.phone) for contact in contacts]
    if len(set(phones)) != len(phones):
        msg = "two contacts share a phone number"
        raise ValueError(msg)
    calendar = _read("calendar.json", TypeAdapter(list[CalendarEvent]))
    return World(
        user=_read("user.json", TypeAdapter(UserProfile)),
        contacts={contact.contact_id: contact for contact in contacts},
        memory=_read("memory.json", TypeAdapter(tuple[MemoryItem, ...])),
        calendar={event.event_id: event for event in calendar},
        spam_numbers=_read("spam_numbers.json", TypeAdapter(tuple[SpamNumber, ...])),
    )
