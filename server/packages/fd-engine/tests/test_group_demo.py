"""Grouping the demo's planted bugs: a different tool or category is always a new cause."""

import json

from fd_engine.group import CauseGrouper
from fd_engine.llm import Llm

from .demo_causes import DEMO_CAUSES, file_all
from .fakes import FakeTransport, settings


async def test_only_the_same_category_and_tool_reach_the_model() -> None:
    """A model that matches everything can only merge b02 into b01, the one cause it is shown."""
    transport = FakeTransport(replies=[json.dumps({"match": 1})])

    group_of = await file_all(CauseGrouper(Llm(settings(), transport=transport)))

    assert len(transport.prompts) == 1
    assert "Booked 22:00 instead of 10:00" in transport.prompts[0]
    assert "Left the reports note" not in transport.prompts[0]
    assert group_of["b02"] == group_of["b01"]
    assert len({group_of[bug] for bug in ("b01", "b04", "b06", "b07")}) == 4


async def test_a_model_that_says_no_match_keeps_all_five_apart() -> None:
    transport = FakeTransport(replies=[json.dumps({"match": None})])

    group_of = await file_all(CauseGrouper(Llm(settings(), transport=transport)))

    assert len(set(group_of.values())) == len(DEMO_CAUSES)
