"""People sign in with the web session token; the SDK uses hashed project API keys."""

import pytest
from httpx import AsyncClient

from fd_shared.enums import ApiErrorCode

from .conftest import Headers, bearer, web_token


async def test_first_sign_in_creates_one_project(client: AsyncClient) -> None:
    headers = bearer(web_token("google-first-sign-in"))

    first = await client.get("/v1/projects.self", headers=headers)
    second = await client.get("/v1/projects.self", headers=headers)

    assert first.status_code == 200
    assert first.json()["project"]["id"] == second.json()["project"]["id"]


@pytest.mark.parametrize(
    "token",
    [
        web_token("google-x", secret="another-secret-that-is-long-enough-for-hs256"),
        web_token("google-x", aud="someone-else"),
        web_token("google-x", iss="someone-else"),
        web_token("google-x", lifetime=-10),
        "fd_live_not-a-real-key",
    ],
    ids=["signature", "audience", "issuer", "expired", "unknown-key"],
)
async def test_bad_credentials_are_unauthenticated(client: AsyncClient, token: str) -> None:
    response = await client.get("/v1/projects.self", headers=bearer(token))

    assert response.status_code == 401
    assert response.json()["code"] == ApiErrorCode.UNAUTHENTICATED


async def test_api_key_works_until_revoked(
    client: AsyncClient, person: Headers, api_key: Headers
) -> None:
    project = (await client.get("/v1/projects.self", headers=person)).json()["project"]
    by_key = (await client.get("/v1/projects.self", headers=api_key)).json()["project"]
    [listed] = (await client.post("/v1/api-keys.list", json={}, headers=person)).json()["items"]

    revoked = await client.post(
        "/v1/api-keys.revoke", json={"api_key_id": listed["id"]}, headers=person
    )
    after = await client.get("/v1/projects.self", headers=api_key)

    assert by_key["id"] == project["id"]
    assert listed["last_used_at"] is not None
    assert revoked.json()["api_key"]["revoked_at"] is not None
    assert after.status_code == 401


async def test_person_only_route_rejects_an_api_key(client: AsyncClient, api_key: Headers) -> None:
    response = await client.post("/v1/runs.list", json={}, headers=api_key)

    assert response.status_code == 401
