"""Typed models of the mock world: clinics, doctors and appointment slots."""

from datetime import date, time
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class City(StrEnum):
    """Cities the mock world covers."""

    HYDERABAD = "Hyderabad"
    BENGALURU = "Bengaluru"


class Speciality(StrEnum):
    """Medical specialities a doctor can have."""

    GENERAL_PHYSICIAN = "general_physician"
    CARDIOLOGIST = "cardiologist"
    DERMATOLOGIST = "dermatologist"
    PEDIATRICIAN = "pediatrician"
    ORTHOPEDIST = "orthopedist"
    ENT_SPECIALIST = "ent_specialist"
    GYNECOLOGIST = "gynecologist"


class SlotStatus(StrEnum):
    """Whether a slot can still be booked."""

    AVAILABLE = "available"
    BOOKED = "booked"
    WAITLIST = "waitlist"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Calendar(_Frozen):
    """The fixed today and how many days ahead the clinics publish slots."""

    today: date
    days_ahead: int = Field(ge=1)


class Clinic(_Frozen):
    """One clinic branch."""

    clinic_id: str
    name: str
    area: str
    city: City


class Doctor(_Frozen):
    """One doctor at one clinic branch, with fees and a weekly schedule.

    A doctor who works at two branches appears once per branch, with a separate id.
    """

    doctor_id: str
    name: str
    speciality: Speciality
    clinic_id: str
    consultation_fee_inr: int = Field(gt=0)
    follow_up_fee_inr: int = Field(gt=0)
    weekdays: frozenset[int] = Field(description="ISO weekdays the doctor works, 1 is Monday.")
    times: tuple[time, ...]


class SlotStatusOverride(_Frozen):
    """A slot whose status is not the default `available`."""

    doctor_id: str
    date: date
    time: time
    status: SlotStatus


class Slot(_Frozen):
    """One bookable appointment time."""

    slot_id: str
    doctor_id: str
    date: date
    time: time
    status: SlotStatus


class World(_Frozen):
    """The whole mock world, indexed by id."""

    calendar: Calendar
    clinics: dict[str, Clinic]
    doctors: dict[str, Doctor]
    slots: dict[str, Slot]
