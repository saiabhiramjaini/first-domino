"""The new-cause email alert: what the web app is told, how it is signed, and that a failure
never stops a diagnosis."""

import json
from datetime import UTC, datetime

import httpx
import jwt
import pytest

from fd_api.services.email_alerts import (
    ALERT_TOKEN_AUDIENCE,
    ALERT_TOKEN_ISSUER,
    alert_token,
    new_cause_alert,
    send_new_cause_alert,
)

from .test_slack import _cause

SECRET = "alert-test-secret-that-is-long-enough"
NOW = datetime(2026, 11, 21, 10, 0, tzinfo=UTC)


def test_alert_carries_the_cause_and_the_owner() -> None:
    cause = _cause()

    alert = new_cause_alert(cause, to="owner@example.com")

    assert alert.to == "owner@example.com"
    assert alert.cause_id == cause.id
    assert alert.title == "Converted AM appointment to PM"
    assert alert.proven is True


def test_token_is_only_good_as_an_alert_and_expires() -> None:
    token = alert_token(SECRET, now=NOW)

    claims = jwt.decode(
        token,
        SECRET,
        algorithms=["HS256"],
        audience=ALERT_TOKEN_AUDIENCE,
        issuer=ALERT_TOKEN_ISSUER,
        options={"verify_exp": False},
    )
    with pytest.raises(jwt.InvalidAudienceError):
        jwt.decode(
            token,
            SECRET,
            algorithms=["HS256"],
            audience="first-domino-api",
            options={"verify_exp": False},
        )

    assert claims["exp"] - claims["iat"] == 300


async def test_alert_is_posted_to_the_web_app_with_the_token() -> None:
    seen: list[httpx.Request] = []

    def web(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(204)

    alert = new_cause_alert(_cause(), to="owner@example.com")
    async with httpx.AsyncClient(transport=httpx.MockTransport(web)) as http:
        await send_new_cause_alert(
            http, alert, web_app_url="https://app.test/", token="t0ken", timeout_seconds=1
        )

    [request] = seen
    assert str(request.url) == "https://app.test/api/alerts/new-cause"
    assert request.headers["Authorization"] == "Bearer t0ken"
    assert json.loads(request.content)["cause_id"] == str(alert.cause_id)


async def test_a_failed_alert_does_not_raise() -> None:
    alert = new_cause_alert(_cause(), to="owner@example.com")
    broken = httpx.MockTransport(lambda _: httpx.Response(503))
    async with httpx.AsyncClient(transport=broken) as http:
        await send_new_cause_alert(
            http, alert, web_app_url="https://app.test", token="t", timeout_seconds=1
        )
