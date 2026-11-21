"""Read the world JSON shipped in this package and expand doctor schedules into slots."""

from datetime import date, time, timedelta
from functools import cache
from importlib.resources import files

from pydantic import TypeAdapter

from fd_demo_agent.world.models import (
    Calendar,
    Clinic,
    Doctor,
    Slot,
    SlotStatus,
    SlotStatusOverride,
    World,
)

_PACKAGE = "fd_demo_agent.world"
_DATA_DIR = "data"


def _read[T](name: str, adapter: TypeAdapter[T]) -> T:
    return adapter.validate_json(files(_PACKAGE).joinpath(_DATA_DIR, name).read_bytes())


def slot_id_for(doctor_id: str, day: date, at: time) -> str:
    """Build the stable id of a doctor's slot, such as `s-anil-mehta-kph-1122-1130`."""
    return f"s-{doctor_id.removeprefix('d-')}-{day:%m%d}-{at:%H%M}"


def _expand_slots(
    calendar: Calendar,
    doctors: list[Doctor],
    overrides: list[SlotStatusOverride],
) -> dict[str, Slot]:
    statuses = {slot_id_for(o.doctor_id, o.date, o.time): o.status for o in overrides}
    days = [calendar.today + timedelta(days=n) for n in range(1, calendar.days_ahead + 1)]
    slots: dict[str, Slot] = {}
    for doctor in doctors:
        for day in days:
            if day.isoweekday() not in doctor.weekdays:
                continue
            for at in doctor.times:
                slot_id = slot_id_for(doctor.doctor_id, day, at)
                status = statuses.pop(slot_id, SlotStatus.AVAILABLE)
                slots[slot_id] = Slot(
                    slot_id=slot_id, doctor_id=doctor.doctor_id, date=day, time=at, status=status
                )
    if statuses:
        msg = f"slot status overrides name slots that do not exist: {sorted(statuses)}"
        raise ValueError(msg)
    return slots


@cache
def load_world() -> World:
    """Load the mock world once per process.

    Example:
        >>> load_world().doctors["d-anil-mehta-kph"].consultation_fee_inr
        700
    """
    calendar = _read("calendar.json", TypeAdapter(Calendar))
    clinics = _read("clinics.json", TypeAdapter(list[Clinic]))
    doctors = _read("doctors.json", TypeAdapter(list[Doctor]))
    overrides = _read("slot_statuses.json", TypeAdapter(list[SlotStatusOverride]))
    unknown_clinics = {d.clinic_id for d in doctors} - {c.clinic_id for c in clinics}
    if unknown_clinics:
        msg = f"doctors name clinics that do not exist: {sorted(unknown_clinics)}"
        raise ValueError(msg)
    return World(
        calendar=calendar,
        clinics={c.clinic_id: c for c in clinics},
        doctors={d.doctor_id: d for d in doctors},
        slots=_expand_slots(calendar, doctors, overrides),
    )
