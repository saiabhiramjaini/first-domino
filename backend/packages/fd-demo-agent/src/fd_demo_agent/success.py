"""Success check: compare the final booking with the expected booking."""

from enum import StrEnum

from pydantic import BaseModel

from fd_demo_agent.sandbox import Booking, BookingStatus
from fd_demo_agent.tasks import DemoTask


class FailureReason(StrEnum):
    """The first way a booking misses its task, checked in this order."""

    NO_BOOKING = "no_booking"
    WAITLISTED = "waitlisted"
    WRONG_DOCTOR = "wrong_doctor"
    WRONG_DATE = "wrong_date"
    WRONG_TIME = "wrong_time"
    WRONG_PATIENT = "wrong_patient"


class SuccessReport(BaseModel):
    """The verdict of the success check, with the reason when it failed."""

    failure: FailureReason | None

    @property
    def passed(self) -> bool:
        """True when the booking satisfies the task."""
        return self.failure is None


def _same_name(left: str, right: str) -> bool:
    return " ".join(left.casefold().split()) == " ".join(right.casefold().split())


def _first_failure(task: DemoTask, booking: Booking | None) -> FailureReason | None:
    expected = task.expected
    if booking is None:
        return FailureReason.NO_BOOKING
    checks = (
        (booking.status == BookingStatus.CONFIRMED, FailureReason.WAITLISTED),
        (booking.doctor_id in expected.doctor_ids, FailureReason.WRONG_DOCTOR),
        (booking.date == expected.date, FailureReason.WRONG_DATE),
        (expected.window.contains(booking.time), FailureReason.WRONG_TIME),
        (_same_name(booking.patient_name, expected.patient_name), FailureReason.WRONG_PATIENT),
    )
    return next((reason for ok, reason in checks if not ok), None)


def check_booking(task: DemoTask, booking: Booking | None) -> SuccessReport:
    """Check a run's final booking against its task. Plain code, no model call.

    Patient names match ignoring case and repeated spaces, never spelling.

    Example:
        >>> check_booking(get_task("t01"), toolbox.booking).passed
        True
    """
    return SuccessReport(failure=_first_failure(task, booking))
