"""Retry, salvage and degrade in `llm`, and the calls built on it, on a scripted transport."""

import json
from uuid import uuid4

import pytest

from fd_engine.baseline import BaselineJudge
from fd_engine.explain import LlmExplainer, unexplained
from fd_engine.fix import LlmStepFixer
from fd_engine.group import CauseCandidate, CauseGrouper
from fd_engine.llm import Llm, ReplyQuality
from fd_shared.enums import CauseCategory, MessageRole
from fd_shared.models import Explanation

from .fakes import FakeReader, FakeTransport, settings

EXPLANATION = {
    "title": "Booked the wrong date",
    "summary": "The agent picked Tuesday. The visit needed Monday.",
    "suggested_fix": "Resolve relative dates before booking.",
    "category": "wrong_date",
}


def llm(*replies: str | None) -> tuple[Llm, FakeTransport]:
    transport = FakeTransport(replies=list(replies))
    return Llm(settings(), transport=transport), transport


async def test_valid_reply_is_parsed_and_costed() -> None:
    model, _ = llm(json.dumps(EXPLANATION))

    reply = await model.structured(
        system="s", user="u", schema=Explanation, fallback=unexplained(3)
    )

    assert reply.quality is ReplyQuality.PARSED
    assert reply.value.category is CauseCategory.WRONG_DATE
    assert reply.usage.tokens_in == 1000
    assert reply.usage.cost_usd == pytest.approx((1000 * 2.5 + 100 * 10.0) / 1_000_000)


async def test_bad_reply_is_retried_once() -> None:
    model, transport = llm("not json", json.dumps(EXPLANATION))

    reply = await model.structured(
        system="s", user="u", schema=Explanation, fallback=unexplained(3)
    )

    assert reply.quality is ReplyQuality.PARSED
    assert len(transport.prompts) == 2
    assert reply.usage.tokens_in == 2000


async def test_failed_call_is_retried() -> None:
    model, _ = llm(None, json.dumps(EXPLANATION))

    reply = await model.structured(
        system="s", user="u", schema=Explanation, fallback=unexplained(3)
    )

    assert reply.quality is ReplyQuality.PARSED


async def test_valid_fields_are_salvaged_over_the_fallback() -> None:
    partial = json.dumps({**EXPLANATION, "category": "not_a_category"})
    model, _ = llm(partial, "```json\n" + partial + "\n```")

    reply = await model.structured(
        system="s", user="u", schema=Explanation, fallback=unexplained(3)
    )

    assert reply.quality is ReplyQuality.SALVAGED
    assert reply.value.title == EXPLANATION["title"]
    assert reply.value.category is CauseCategory.OTHER


async def test_unusable_replies_degrade_to_the_fallback() -> None:
    model, _ = llm("nope", None)

    reply = await model.structured(
        system="s", user="u", schema=Explanation, fallback=unexplained(3)
    )

    assert reply.quality is ReplyQuality.DEGRADED
    assert reply.value == unexplained(3)


async def test_explainer_never_raises_on_garbage() -> None:
    model, _ = llm("[]", "{}")
    reader = FakeReader(step_count=4)
    run = await reader.get_run(reader.run_id)
    steps = await reader.get_steps(reader.run_id)

    explained = await LlmExplainer(model).explain(run, steps, 2, None)

    assert explained.explanation == unexplained(2)


async def test_fixer_builds_an_assistant_turn_with_tool_call_ids() -> None:
    fix = {"content": None, "tool_calls": [{"name": "book", "arguments": '{"day": "monday"}'}]}
    model, transport = llm(json.dumps(fix))
    reader = FakeReader(step_count=4)
    run = await reader.get_run(reader.run_id)
    steps = await reader.get_steps(reader.run_id)

    fixed = await LlmStepFixer(model).fix(run, steps, 3)

    assert fixed.output is not None
    assert fixed.output.role is MessageRole.ASSISTANT
    assert [call.name for call in fixed.output.tool_calls] == ["book"]
    assert fixed.output.tool_calls[0].id.startswith("call_fd_")
    assert "# The turn to rewrite\n\n## Step 3" in transport.prompts[0]


async def test_fixer_rejects_tool_arguments_that_are_not_a_json_object() -> None:
    bad = {"content": None, "tool_calls": [{"name": "book", "arguments": "monday"}]}
    model, _ = llm(json.dumps(bad), json.dumps(bad))
    reader = FakeReader(step_count=4)
    run = await reader.get_run(reader.run_id)

    fixed = await LlmStepFixer(model).fix(run, await reader.get_steps(reader.run_id), 3)

    assert fixed.output is None
    assert fixed.cost_usd > 0


async def test_fixer_lists_the_tools_the_run_used() -> None:
    model, transport = llm(json.dumps({"content": "ok", "tool_calls": []}))
    reader = FakeReader(step_count=3)
    run = await reader.get_run(reader.run_id)

    await LlmStepFixer(model).fix(run, await reader.get_steps(reader.run_id), 2)

    assert "Tools the run used: tool_1, tool_2, tool_3" in transport.prompts[0]


def candidates(count: int) -> list[CauseCandidate]:
    return [
        CauseCandidate(id=uuid4(), title=f"cause {n}", category=CauseCategory.OTHER, summary="s")
        for n in range(count)
    ]


async def test_group_without_candidates_makes_no_call() -> None:
    model, transport = llm()

    match = await CauseGrouper(model).match(Explanation.model_validate(EXPLANATION), [])

    assert match.cause_id is None
    assert transport.prompts == []


@pytest.mark.parametrize(("number", "expected_index"), [(2, 1), (5, None), (None, None)])
async def test_group_maps_the_number_to_a_candidate(
    number: int | None, expected_index: int | None
) -> None:
    model, _ = llm(json.dumps({"match": number}))
    existing = candidates(3)

    match = await CauseGrouper(model).match(Explanation.model_validate(EXPLANATION), existing)

    expected = existing[expected_index].id if expected_index is not None else None
    assert match.cause_id == expected


@pytest.mark.parametrize(("step", "expected"), [(3, 3), (9, None), (0, None)])
async def test_baseline_keeps_only_steps_of_the_run(step: int, expected: int | None) -> None:
    model, _ = llm(json.dumps({"step": step, "reason": "r"}))
    reader = FakeReader(step_count=4)
    run = await reader.get_run(reader.run_id)

    prediction = await BaselineJudge(model).predict(run, await reader.get_steps(reader.run_id))

    assert prediction.step == expected
