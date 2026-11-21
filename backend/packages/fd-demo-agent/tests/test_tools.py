import json
from typing import Any

import pytest

from fd_demo_agent.sandbox import HANGUP_LINE
from fd_demo_agent.toolbox import ToolBox, ToolName, tool_specs
from fd_demo_agent.tools import ToolErrorCode
from fd_demo_agent.world import load_world, phone_key

CALLER_LINES = ("Hello, first line.", "Second line.", "Third line.")


def run(toolbox: ToolBox, tool: ToolName, **arguments: Any) -> Any:
    return json.loads(toolbox.execute(tool.value, json.dumps(arguments)))


@pytest.fixture
def toolbox() -> ToolBox:
    return ToolBox(load_world(), CALLER_LINES)


def test_world_loads_contacts_memory_calendar_and_spam() -> None:
    world = load_world()
    assert world.user.name == "Arjun Rao"
    assert str(world.today) == "2026-11-21"
    assert len(world.contacts) == 25
    assert len(world.calendar) == 7
    assert len(world.spam_numbers) == 3


def test_phone_key_ignores_country_code_and_spacing() -> None:
    assert phone_key("+91 98490 11223") == phone_key("9849011223") == "9849011223"


def test_lookup_finds_a_contact_by_number_in_any_format(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.LOOKUP_CONTACT, phone="98490-11232")
    assert result["contact"]["name"] == "Laxmi Narayana"
    assert result["spam_label"] is None


def test_lookup_flags_a_spam_number(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.LOOKUP_CONTACT, phone="+91 88001 23456")
    assert result["contact"] is None
    assert "fraud" in result["spam_label"]


def test_lookup_of_an_unknown_number_finds_nothing(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.LOOKUP_CONTACT, phone="+91 90000 45612")
    assert (result["contact"], result["spam_label"]) == (None, None)


def test_search_memory_matches_words_in_text_or_tags(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.SEARCH_MEMORY, query="Doctor appointment")
    ids = [item["memory_id"] for item in result["memories"]]
    assert ids == ["m01", "m02", "m03"]


def test_search_memory_ignores_short_words(toolbox: ToolBox) -> None:
    assert run(toolbox, ToolName.SEARCH_MEMORY, query="a to of")["memories"] == []


def test_check_calendar_lists_the_day_in_time_order(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.CHECK_CALENDAR, date="2026-11-27")
    assert [e["event_id"] for e in result["events"]] == ["ev-car-service", "ev-dentist"]


def test_the_caller_answers_by_turn_then_hangs_up(toolbox: ToolBox) -> None:
    replies = [run(toolbox, ToolName.REPLY_TO_CALLER, text=t)["caller"] for t in "abc"]
    assert replies == ["Second line.", "Third line.", HANGUP_LINE]
    assert toolbox.outcome().said == ["a", "b", "c"]


def test_the_caller_line_does_not_depend_on_what_was_said() -> None:
    first, second = ToolBox(load_world(), CALLER_LINES), ToolBox(load_world(), CALLER_LINES)
    assert run(first, ToolName.REPLY_TO_CALLER, text="yes") == run(
        second, ToolName.REPLY_TO_CALLER, text="something else entirely"
    )


def test_replying_after_the_call_ended_is_an_error(toolbox: ToolBox) -> None:
    run(toolbox, ToolName.END_CALL)
    result = run(toolbox, ToolName.REPLY_TO_CALLER, text="hello?")
    assert result["error"] == ToolErrorCode.CALL_ENDED
    assert toolbox.outcome().ended


def test_added_events_get_sequential_ids_and_show_on_the_calendar(toolbox: ToolBox) -> None:
    first = run(toolbox, ToolName.ADD_CALENDAR_EVENT, title="A", date="2026-11-22", time="10:00")
    second = run(toolbox, ToolName.ADD_CALENDAR_EVENT, title="B", date="2026-11-22", time="09:00")
    assert (first["event_id"], second["event_id"]) == ("ev-new-1", "ev-new-2")
    day = run(toolbox, ToolName.CHECK_CALENDAR, date="2026-11-22")
    assert [e["title"] for e in day["events"]] == [
        "Badminton with Srinivas",
        "B",
        "A",
        "Plumber visit: kitchen sink (Anand)",
    ]


def test_an_event_in_the_past_is_an_error(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.ADD_CALENDAR_EVENT, title="A", date="2026-11-20", time="10:00")
    assert result["error"] == ToolErrorCode.DATE_IN_PAST


def test_moving_an_existing_event_is_recorded_once(toolbox: ToolBox) -> None:
    for at in ("17:00", "18:00"):
        run(
            toolbox, ToolName.MOVE_CALENDAR_EVENT, event_id="ev-plumber", date="2026-11-23", time=at
        )
    moved = toolbox.outcome().moved_events
    assert [(e.event_id, str(e.time)) for e in moved] == [("ev-plumber", "18:00:00")]


def test_unknown_event_is_an_error(toolbox: ToolBox) -> None:
    result = run(toolbox, ToolName.SET_REMINDER, event_id="ev-nope", minutes_before=60)
    assert result["error"] == ToolErrorCode.UNKNOWN_EVENT


def callback(toolbox: ToolBox, contact: str) -> Any:
    return run(
        toolbox,
        ToolName.SCHEDULE_CALLBACK,
        contact=contact,
        date="2026-11-21",
        time="18:30",
        reason="Goa trip",
    )


def test_a_callback_resolves_a_contact_id_to_its_number(toolbox: ToolBox) -> None:
    result = callback(toolbox, "c-srinivas")
    assert (result["phone"], result["contact_name"]) == ("+91 99490 55621", "Srinivas")


def test_a_callback_to_an_unsaved_number_keeps_the_number(toolbox: ToolBox) -> None:
    assert callback(toolbox, "+91 90000 45612")["contact_name"] is None


def test_a_callback_to_an_unknown_name_is_an_error(toolbox: ToolBox) -> None:
    assert callback(toolbox, "Srini")["error"] == ToolErrorCode.UNKNOWN_CONTACT


@pytest.mark.parametrize("arguments", ["not json", '{"phone": 5}', '{"query": "x"}'])
def test_bad_arguments_become_a_readable_error(toolbox: ToolBox, arguments: str) -> None:
    result = json.loads(toolbox.execute(ToolName.LOOKUP_CONTACT.value, arguments))
    assert result["error"] == ToolErrorCode.INVALID_ARGUMENTS


def test_unknown_tool_is_an_error(toolbox: ToolBox) -> None:
    result = json.loads(toolbox.execute("transfer_money", "{}"))
    assert result["error"] == ToolErrorCode.UNKNOWN_TOOL


def test_runs_do_not_share_state() -> None:
    first = ToolBox(load_world(), CALLER_LINES)
    run(first, ToolName.BLOCK_CALLER, phone="+91 14045 67890", reason="spam")
    run(first, ToolName.ADD_CALENDAR_EVENT, title="A", date="2026-11-22", time="10:00")
    assert ToolBox(load_world(), CALLER_LINES).outcome().blocked == []
    assert len(load_world().calendar) == 7


def test_tool_specs_describe_every_tool() -> None:
    specs = tool_specs()
    assert [spec["function"]["name"] for spec in specs] == [name.value for name in ToolName]
    assert all(spec["function"].get("description") for spec in specs)
