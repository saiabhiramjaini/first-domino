"""Per-run booking sandbox: the one appointment request a run may make."""

from datetime import date, time
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class BookingStatus(StrEnum):
    """What the clinic did with an appointment request."""

    CONFIRMED = "confirmed"
    WAITLISTED = "waitlisted"


class Booking(BaseModel):
    """An appointment request as the clinic recorded it."""

    model_config = ConfigDict(frozen=True)

    booking_id: str
    slot_id: str
    doctor_id: str
    clinic_id: str
    date: date
    time: time
    patient_name: str
    status: BookingStatus


class BookingSandbox:
    """Holds the bookings of one run, so runs never share state.

    A run may make one appointment request. There is no cancel tool, so a wrong
    request cannot be undone, which is what makes a bad booking step final.
    """

    def __init__(self) -> None:
        self._booking: Booking | None = None

    @property
    def booking(self) -> Booking | None:
        """The run's appointment request, or None before one is made."""
        return self._booking

    def place(self, booking: Booking) -> None:
        """Store the run's appointment request.

        Raises:
            ValueError: The run already made a request.
        """
        if self._booking is not None:
            msg = "the run already holds an appointment request"
            raise ValueError(msg)
        self._booking = booking
