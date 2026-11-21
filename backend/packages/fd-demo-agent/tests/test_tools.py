import json
from datetime import date, time
from typing import Any

import pytest

from fd_demo_agent.sandbox import BookingStatus
from fd_demo_agent.toolbox import ToolBox, ToolName, tool_specs
from fd_demo_agent.tools import ToolErrorCode
from fd_demo_agent.world import SlotStatus, load_world


def run(toolbox: ToolBox, tool: ToolName, **arguments: str) -> Any:
    return json.loads(toolbox.execute(tool.value, json.dumps(arguments)))


@pytest.fixture
def toolbox() -> ToolBox:
    return ToolBox(load_world())


def test_world_loads_every_clinic_doctor_and_slot() -> None:
    world = load_world()
    assert len(world.clinics) == 6
    assert len(world.doctors) == 15
    assert world.calendar.today == date(2026, 11, 21)
    assert all(world.calendar.today < slot.date for slot in world.slots.values())


def test_search_by_name_and_area_finds_one_branch(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.SEARCH_DOCTORS, name="Dr. Mehta", area="kukatpally")
    assert [d["doctor_id"] for d in result["doctors"]] == ["d-anil-mehta-kph"]


def test_search_by_name_alone_finds_both_branches(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.SEARCH_DOCTORS, name="Mehta")
    ids = {d["doctor_id"] for d in result["doctors"]}
    assert ids == {"d-anil-mehta-kph", "d-anil-mehta-mdp"}


def test_search_by_speciality_and_city(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.SEARCH_DOCTORS, speciality="dermatologist", city="Bengaluru")
    ids = {d["doctor_id"] for d in result["doctors"]}
    assert ids == {"d-priya-nair-ind", "d-sneha-kulkarni-ind"}


def test_list_slots_hides_booked_and_shows_waitlist_in_time_order(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.LIST_SLOTS, doctor_id="d-anil-mehta-kph", date="2026-11-22")
    slots = [(s["time"], s["status"]) for s in result["slots"]]
    assert slots == [
        ("10:30:00", SlotStatus.WAITLIST),
        ("11:30:00", SlotStatus.AVAILABLE),
        ("16:00:00", SlotStatus.AVAILABLE),
        ("18:00:00", SlotStatus.AVAILABLE),
    ]


def test_list_slots_on_a_day_off_is_empty(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.LIST_SLOTS, doctor_id="d-anil-mehta-kph", date="2026-11-23")
    assert result["slots"] == []


@pytest.mark.parametrize("day", ["2026-11-21", "2026-11-29"])
def test_list_slots_outside_the_published_days_is_an_error(toolbox: ToolBox, day: str) -> None:
    result = run(toolbox, ToolName.LIST_SLOTS, doctor_id="d-anil-mehta-kph", date=day)
    assert result["error"] == ToolErrorCode.DATE_OUT_OF_RANGE


def test_unknown_doctor_is_an_error(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.CHECK_FEE, doctor_id="d-rohan-shetty-jyn")
    assert result["error"] == ToolErrorCode.UNKNOWN_DOCTOR


def test_check_fee_returns_both_fees(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.CHECK_FEE, doctor_id="d-sneha-kulkarni-ind")
    assert (result["consultation_fee_inr"], result["follow_up_fee_inr"]) == (750, 450)


def test_booking_an_available_slot_confirms_it(toolbox: ToolBox) -> None:
    result = run(
        toolbox,
        ToolName.BOOK_APPOINTMENT,
        slot_id="s-anil-mehta-kph-1122-1130",
        patient_name=" Ramesh Rao ",
    )
    assert result["status"] == BookingStatus.CONFIRMED
    booking = toolbox.booking
    assert booking is not None
    assert (booking.clinic_id, booking.time) == ("c-arogya-kukatpally", time(11, 30))
    assert booking.patient_name == "Ramesh Rao"


def test_booking_a_waitlist_slot_only_waitlists(toolbox: ToolBox) -> None:
    run(toolbox, ToolName.BOOK_APPOINTMENT, slot_id="s-anil-mehta-kph-1122-1030", patient_name="R")
    assert toolbox.booking is not None
    assert toolbox.booking.status == BookingStatus.WAITLISTED


def test_booking_a_booked_slot_is_an_error(toolbox: ToolBox) -> None:
    result = run(
        toolbox, ToolName.BOOK_APPOINTMENT, slot_id="s-anil-mehta-kph-1122-0930", patient_name="R"
    )
    assert result["error"] == ToolErrorCode.SLOT_TAKEN
    assert toolbox.booking is None


def test_a_run_can_make_only_one_request(toolbox: ToolBox) -> None:
    run(toolbox, ToolName.BOOK_APPOINTMENT, slot_id="s-anil-mehta-kph-1122-1030", patient_name="R")
    result = run(
        toolbox, ToolName.BOOK_APPOINTMENT, slot_id="s-anil-mehta-kph-1122-1130", patient_name="R"
    )
    assert result["error"] == ToolErrorCode.REQUEST_EXISTS
    assert toolbox.booking is not None
    assert toolbox.booking.slot_id == "s-anil-mehta-kph-1122-1030"


def test_unknown_slot_is_an_error(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.BOOK_APPOINTMENT, slot_id="s-nobody-1122-1130", patient_name="R")
    assert result["error"] == ToolErrorCode.UNKNOWN_SLOT


@pytest.mark.parametrize("arguments", ["not json", '{"doctor_id": 5}', "{}"])
def test_bad_arguments_become_a_readable_error(toolbox: ToolBox, arguments: str) -> None:
    result = json.loads(toolbox.execute(ToolName.CHECK_FEE.value, arguments))
    assert result["error"] == ToolErrorCode.INVALID_ARGUMENTS


def test_unknown_tool_is_an_error(toolbox: ToolBox) -> None:
    result = json.loads(toolbox.execute("cancel_appointment", "{}"))
    assert result["error"] == ToolErrorCode.UNKNOWN_TOOL


def test_tools_are_deterministic_and_runs_do_not_share_bookings() -> None:
    first, second = ToolBox(load_world()), ToolBox(load_world())
    arguments = json.dumps({"slot_id": "s-anil-mehta-kph-1122-1130", "patient_name": "Ramesh Rao"})
    assert first.execute("book_appointment", arguments) == second.execute(
        "book_appointment", arguments
    )
    assert ToolBox(load_world()).booking is None


def test_tool_specs_describe_every_tool() -> None:
    specs = tool_specs()
    assert [spec["function"]["name"] for spec in specs] == [name.value for name in ToolName]
    assert all(spec["function"].get("description") for spec in specs)
