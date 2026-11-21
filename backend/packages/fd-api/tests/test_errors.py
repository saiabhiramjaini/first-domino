"""Every error answers with a stable `code`, `title` and `detail`."""

from httpx import AsyncClient

from fd_shared.enums import ApiErrorCode

from .conftest import Headers


async def test_missing_token_is_unauthenticated(bare_client: AsyncClient) -> None:
    response = await bare_client.get("/v1/projects.self")

    assert response.status_code == 401
    assert response.json()["code"] == ApiErrorCode.UNAUTHENTICATED


async def test_unknown_route_is_not_found(bare_client: AsyncClient) -> None:
    response = await bare_client.get("/v1/nothing.here")

    assert response.status_code == 404
    assert set(response.json()) == {"code", "title", "detail"}


async def test_health_needs_no_auth(bare_client: AsyncClient) -> None:
    response = await bare_client.get("/health")

    assert response.json() == {"ok": True}


async def test_malformed_json_is_bad_request(client: AsyncClient, person: Headers) -> None:
    response = await client.post(
        "/v1/runs.list",
        content=b"{not json",
        headers={**person, "Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == ApiErrorCode.BAD_REQUEST


async def test_invalid_field_lists_the_field(client: AsyncClient, person: Headers) -> None:
    response = await client.post("/v1/runs.list", json={"limit": 0}, headers=person)

    body = response.json()
    assert response.status_code == 422
    assert body["code"] == ApiErrorCode.VALIDATION_FAILED
    assert [error["field"] for error in body["errors"]] == ["limit"]


async def test_foreign_cursor_is_a_validation_error(client: AsyncClient, person: Headers) -> None:
    response = await client.post(
        "/v1/runs.list", json={"cursor": "bm90LWEtY3Vyc29y"}, headers=person
    )

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["errors"]] == ["cursor"]
