"""Loads the mock world data into typed models."""

from fd_demo_agent.world.loader import load_world, slot_id_for
from fd_demo_agent.world.models import (
    Calendar,
    City,
    Clinic,
    Doctor,
    Slot,
    SlotStatus,
    Speciality,
    World,
)

__all__ = [
    "Calendar",
    "City",
    "Clinic",
    "Doctor",
    "Slot",
    "SlotStatus",
    "Speciality",
    "World",
    "load_world",
    "slot_id_for",
]
