"""The new-cause Slack message, and that a Slack failure never stops a diagnosis."""

import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from fd_api.services.slack import SlackMessage, new_cause_message, send_slack_message
from fd_database import tables
from fd_shared.enums import CauseCategory

WEBHOOK = "https://hooks.slack.test/services/T/B/X"


def _cause() -> tables.Cause:
    now = datetime(2026, 11, 21, 10, 0, tzinfo=UTC)
    return tables.Cause(
        id=uuid4(),
        project_id=uuid4(),
        title="Converted AM appointment to PM",
        category=CauseCategory.WRONG_DATE,
        step_name="add_calendar_event",
        summary="The caller asked for 10 AM; the event was added at 22:00.",
        suggested_fix="Confirm AM or PM before adding the event.",
        run_count=1,
        verified_count=1,
        first_seen_at=now,
        last_seen_at=now,
    )


def test_message_names_the_cause_and_links_to_it() -> None:
    cause = _cause()

    text = new_cause_message(cause, web_app_url="https://app.test/").text

    assert "*Converted AM appointment to PM*" in text
    assert "`add_calendar_event`" in text
    assert "proven by replay" in text
    assert f"<https://app.test/causes/{cause.id}|Open in First Domino>" in text


async def test_message_is_posted_as_json() -> None:
    sent: list[dict[str, str]] = []

    def slack(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(200, text="ok")

    async with httpx.AsyncClient(transport=httpx.MockTransport(slack)) as http:
        await send_slack_message(http, WEBHOOK, SlackMessage(text="hi"), timeout_seconds=1)

    assert sent == [{"text": "hi"}]


async def test_slack_failure_does_not_raise() -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(broken)) as http:
        await send_slack_message(http, WEBHOOK, SlackMessage(text="hi"), timeout_seconds=1)
