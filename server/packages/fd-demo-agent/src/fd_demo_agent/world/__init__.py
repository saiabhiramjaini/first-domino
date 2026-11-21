"""Loads the mock world data into typed models."""

from fd_demo_agent.world.loader import PHONE_DIGITS, load_world, phone_key
from fd_demo_agent.world.models import (
    CalendarEvent,
    Contact,
    MemoryItem,
    SpamNumber,
    UserProfile,
    World,
)

__all__ = [
    "PHONE_DIGITS",
    "CalendarEvent",
    "Contact",
    "MemoryItem",
    "SpamNumber",
    "UserProfile",
    "World",
    "load_world",
    "phone_key",
]
