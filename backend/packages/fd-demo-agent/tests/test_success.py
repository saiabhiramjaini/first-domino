from datetime import date, time

import pytest

from fd_demo_agent.sandbox import Booking, BookingStatus
from fd_demo_agent.success import FailureReason, check_booking
from fd_demo_agent.tasks import TASKS, get_task
from fd_demo_agent.toolbox import ToolBox
from fd_demo_agent.world import SlotStatus, load_world

T01_GOOD = Booking(
    booking_id="bk-anil-mehta-kph-1122-1130",
    slot_id="s-anil-mehta-kph-1122-1130",
    doctor_id="d-anil-mehta-kph",
    clinic_id="c-arogya-kukatpally",
    date=date(2026, 11, 22),
    time=time(11, 30),
    patient_name="Ramesh Rao",
    status=BookingStatus.CONFIRMED,
)


def test_the_expected_booking_passes() -> None:
    assert check_booking(get_task("t01"), T01_GOOD).passed


def test_patient_name_ignores_case_and_spacing() -> None:
    booking = T01_GOOD.model_copy(update={"patient_name": "ramesh   RAO"})
    assert check_booking(get_task("t01"), booking).passed


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"status": BookingStatus.WAITLISTED}, FailureReason.WAITLISTED),
        ({"doctor_id": "d-anil-mehta-mdp"}, FailureReason.WRONG_DOCTOR),
        ({"date": date(2026, 11, 23)}, FailureReason.WRONG_DATE),
        ({"time": time(16)}, FailureReason.WRONG_TIME),
        ({"time": time(12)}, FailureReason.WRONG_TIME),
        ({"patient_name": "Ramesh Raoo"}, FailureReason.WRONG_PATIENT),
    ],
)
def test_each_mismatch_fails_with_its_reason(
    change: dict[str, object], reason: FailureReason
) -> None:
    report = check_booking(get_task("t01"), T01_GOOD.model_copy(update=change))
    assert not report.passed
    assert report.failure == reason


def test_no_booking_fails() -> None:
    assert check_booking(get_task("t01"), None).failure == FailureReason.NO_BOOKING


def test_there_are_ten_tasks_with_unique_ids() -> None:
    assert len({task.task_id for task in TASKS}) == len(TASKS) == 10


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.task_id)
def test_every_task_can_be_booked_in_the_world(task) -> None:
    world = load_world()
    expected = task.expected
    slots = [
        slot
        for slot in world.slots.values()
        if slot.doctor_id in expected.doctor_ids
        and slot.date == expected.date
        and expected.window.contains(slot.time)
        and slot.status == SlotStatus.AVAILABLE
    ]
    assert slots, f"{task.task_id} has no bookable slot"
    toolbox = ToolBox(world)
    arguments = f'{{"slot_id": "{slots[0].slot_id}", "patient_name": "{expected.patient_name}"}}'
    toolbox.execute("book_appointment", arguments)
    assert check_booking(task, toolbox.booking).passed
