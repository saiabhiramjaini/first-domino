"""Tells a project's Slack channel about a new root cause."""

import httpx
from pydantic import BaseModel

from fd_database import tables
from fd_shared.logging import get_logger

log = get_logger(__name__)


class SlackMessage(BaseModel):
    """The body of a Slack incoming webhook call."""

    text: str


def new_cause_message(cause: tables.Cause) -> SlackMessage:
    """The message for a cause group seen for the first time."""
    return SlackMessage(
        text=(
            f"New root cause found by First Domino: *{cause.title}* "
            f"({cause.category.value}, at `{cause.step_name}`)\n"
            f"{cause.summary}\nSuggested fix: {cause.suggested_fix}"
        )
    )


async def send_slack_message(
    http: httpx.AsyncClient, webhook_url: str, message: SlackMessage, *, timeout_seconds: float
) -> None:
    """Posts the message. A failure is logged and never stops the caller."""
    try:
        response = await http.post(webhook_url, json=message.model_dump(), timeout=timeout_seconds)
        response.raise_for_status()
    except httpx.HTTPError as error:
        log.warning("slack.send_failed", error_type=type(error).__name__)
