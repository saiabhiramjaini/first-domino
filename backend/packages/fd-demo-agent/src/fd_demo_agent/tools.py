"""Mock tools: pure functions over the world data and a per-run booking sandbox."""

from datetime import date, time
from enum import StrEnum

from pydantic import BaseModel, Field

from fd_demo_agent.sandbox import Booking, BookingSandbox, BookingStatus
from fd_demo_agent.world import City, Slot, SlotStatus, Speciality, World

_DOCTOR_TITLES = ("dr.", "dr ")


class ToolErrorCode(StrEnum):
    """Why a tool call did not succeed. The model reads these, so they are plain words."""

    INVALID_ARGUMENTS = "invalid_arguments"
    UNKNOWN_TOOL = "unknown_tool"
    UNKNOWN_DOCTOR = "unknown_doctor"
    UNKNOWN_SLOT = "unknown_slot"
    DATE_OUT_OF_RANGE = "date_out_of_range"
    SLOT_TAKEN = "slot_taken"
    REQUEST_EXISTS = "request_exists"


class ToolError(BaseModel):
    """A tool result that reports a failure instead of data."""

    error: ToolErrorCode
    detail: str


class SearchDoctorsArgs(BaseModel):
    """Find doctors. Every filter is optional; filters combine with AND."""

    name: str | None = Field(default=None, description="Part of the doctor's name, e.g. 'Mehta'.")
    speciality: Speciality | None = None
    city: City | None = None
    area: str | None = Field(default=None, description="Clinic area, e.g. 'Kukatpally'.")


class ListSlotsArgs(BaseModel):
    """List a doctor's open and waitlist slots on one date."""

    doctor_id: str
    date: date


class CheckFeeArgs(BaseModel):
    """Get a doctor's consultation and follow-up fees in rupees."""

    doctor_id: str


class BookAppointmentArgs(BaseModel):
    """Request an appointment in one slot. A run may make only one request."""

    slot_id: str
    patient_name: str = Field(min_length=1, description="The patient's full name.")


class DoctorSummary(BaseModel):
    """One search hit."""

    doctor_id: str
    name: str
    speciality: Speciality
    clinic: str
    area: str
    city: City


class DoctorSearchResult(BaseModel):
    """Doctors that match every filter, in a fixed order."""

    doctors: list[DoctorSummary]


class SlotView(BaseModel):
    """A slot as the booking site shows it."""

    slot_id: str
    time: time
    status: SlotStatus


class SlotList(BaseModel):
    """A doctor's slots on one date that are not fully booked."""

    doctor_id: str
    date: date
    slots: list[SlotView]


class FeeQuote(BaseModel):
    """A doctor's fees in Indian rupees."""

    doctor_id: str
    consultation_fee_inr: int
    follow_up_fee_inr: int


def _bare_name(name: str) -> str:
    lowered = name.casefold().strip()
    for title in _DOCTOR_TITLES:
        lowered = lowered.removeprefix(title)
    return " ".join(lowered.split())


def search_doctors(world: World, args: SearchDoctorsArgs) -> DoctorSearchResult:
    """Return doctors matching every given filter.

    Example:
        >>> search_doctors(world, SearchDoctorsArgs(name="Mehta", area="Kukatpally"))
    """
    hits: list[DoctorSummary] = []
    for doctor in world.doctors.values():
        clinic = world.clinics[doctor.clinic_id]
        checks = (
            args.name is None or _bare_name(args.name) in _bare_name(doctor.name),
            args.speciality is None or args.speciality == doctor.speciality,
            args.city is None or args.city == clinic.city,
            args.area is None or args.area.casefold().strip() in clinic.area.casefold(),
        )
        if all(checks):
            hits.append(
                DoctorSummary(
                    doctor_id=doctor.doctor_id,
                    name=doctor.name,
                    speciality=doctor.speciality,
                    clinic=clinic.name,
                    area=clinic.area,
                    city=clinic.city,
                )
            )
    return DoctorSearchResult(doctors=hits)


def list_slots(world: World, args: ListSlotsArgs) -> SlotList | ToolError:
    """Return a doctor's available and waitlist slots on one date, earliest first."""
    if args.doctor_id not in world.doctors:
        return ToolError(error=ToolErrorCode.UNKNOWN_DOCTOR, detail=args.doctor_id)
    calendar = world.calendar
    days_out = (args.date - calendar.today).days
    if not 1 <= days_out <= calendar.days_ahead:
        detail = f"slots are published for the {calendar.days_ahead} days after {calendar.today}"
        return ToolError(error=ToolErrorCode.DATE_OUT_OF_RANGE, detail=detail)
    open_slots = sorted(
        (
            slot
            for slot in world.slots.values()
            if slot.doctor_id == args.doctor_id
            and slot.date == args.date
            and slot.status != SlotStatus.BOOKED
        ),
        key=lambda slot: slot.time,
    )
    views = [SlotView(slot_id=s.slot_id, time=s.time, status=s.status) for s in open_slots]
    return SlotList(doctor_id=args.doctor_id, date=args.date, slots=views)


def check_fee(world: World, args: CheckFeeArgs) -> FeeQuote | ToolError:
    """Return a doctor's consultation and follow-up fees."""
    doctor = world.doctors.get(args.doctor_id)
    if doctor is None:
        return ToolError(error=ToolErrorCode.UNKNOWN_DOCTOR, detail=args.doctor_id)
    return FeeQuote(
        doctor_id=doctor.doctor_id,
        consultation_fee_inr=doctor.consultation_fee_inr,
        follow_up_fee_inr=doctor.follow_up_fee_inr,
    )


def _booking_for(world: World, slot: Slot, patient_name: str) -> Booking:
    status = (
        BookingStatus.WAITLISTED if slot.status == SlotStatus.WAITLIST else BookingStatus.CONFIRMED
    )
    return Booking(
        booking_id=f"bk-{slot.slot_id.removeprefix('s-')}",
        slot_id=slot.slot_id,
        doctor_id=slot.doctor_id,
        clinic_id=world.doctors[slot.doctor_id].clinic_id,
        date=slot.date,
        time=slot.time,
        patient_name=patient_name,
        status=status,
    )


def book_appointment(
    world: World, sandbox: BookingSandbox, args: BookAppointmentArgs
) -> Booking | ToolError:
    """Request an appointment and store it in the run's sandbox.

    A waitlist slot gives a `waitlisted` request, not a confirmed booking.
    """
    if sandbox.booking is not None:
        detail = f"this conversation already holds request {sandbox.booking.booking_id}"
        return ToolError(error=ToolErrorCode.REQUEST_EXISTS, detail=detail)
    slot = world.slots.get(args.slot_id)
    if slot is None:
        return ToolError(error=ToolErrorCode.UNKNOWN_SLOT, detail=args.slot_id)
    if slot.status == SlotStatus.BOOKED:
        return ToolError(error=ToolErrorCode.SLOT_TAKEN, detail=args.slot_id)
    booking = _booking_for(world, slot, args.patient_name.strip())
    sandbox.place(booking)
    return booking
