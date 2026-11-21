"""Asks the web app to email a project's owner about a new root cause.

The web app owns the mail account and the wording; the API only says what happened and to
whom. The call carries a short HS256 token signed with the secret the two already share.
"""

from datetime import datetime, timedelta
from uuid import UUID

import httpx
import jwt
from pydantic import BaseModel

from fd_database import tables
from fd_shared.enums import CauseCategory
from fd_shared.logging import get_logger

log = get_logger(__name__)

ALERT_TOKEN_ISSUER = "first-domino-api"
ALERT_TOKEN_AUDIENCE = "first-domino-web-alerts"
ALERT_TOKEN_LIFETIME = timedelta(minutes=5)
NEW_CAUSE_PATH = "/api/alerts/new-cause"


class NewCauseAlert(BaseModel):
    """The body of `POST /api/alerts/new-cause` on the web app."""

    to: str
    cause_id: UUID
    title: str
    category: CauseCategory
    step_name: str
    summary: str
    suggested_fix: str
    proven: bool


def new_cause_alert(cause: tables.Cause, *, to: str) -> NewCauseAlert:
    """The alert for a cause group seen for the first time."""
    return NewCauseAlert(
        to=to,
        cause_id=cause.id,
        title=cause.title,
        category=cause.category,
        step_name=cause.step_name,
        summary=cause.summary,
        suggested_fix=cause.suggested_fix,
        proven=cause.verified_count > 0,
    )


def alert_token(secret: str, *, now: datetime) -> str:
    """A token the web app accepts only as an alert from this API."""
    claims = {
        "iss": ALERT_TOKEN_ISSUER,
        "aud": ALERT_TOKEN_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + ALERT_TOKEN_LIFETIME).timestamp()),
    }
    return jwt.encode(claims, secret, algorithm="HS256")


async def send_new_cause_alert(
    http: httpx.AsyncClient,
    alert: NewCauseAlert,
    *,
    web_app_url: str,
    token: str,
    timeout_seconds: float,
) -> None:
    """Posts the alert. A failure is logged and never stops the caller."""
    try:
        response = await http.post(
            f"{web_app_url.rstrip('/')}{NEW_CAUSE_PATH}",
            json=alert.model_dump(mode="json"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        log.warning("email_alert.send_failed", error_type=type(error).__name__)
        return
    log.info("email_alert.sent", cause_id=str(alert.cause_id))
