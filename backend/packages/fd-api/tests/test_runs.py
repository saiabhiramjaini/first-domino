"""Recording a run: start, record steps, finish, then read it back."""

from collections.abc import Awaitable, Callable
from typing import Any

from httpx import AsyncClient

from fd_shared.enums import ApiErrorCode

from .conftest import Headers, bearer, web_token

TOOLS = ["get_caller_details", "add_calendar_event"]
TASK = {
    "prompt": "Call the clinic and add tomorrow at 10 to the calendar",
    "metadata": {"task_id": "t1"},
}


def _step(run_id: str, index: int) -> dict[str, Any]:
    message = {"role": "assistant", "content": f"step {index}", "tool_calls": []}
    return {
        "run_id": run_id,
        "index": index,
        "model": "test-model",
        "output": message,
        "tool_results": [],
        "messages": [{"role": "user", "content": "hi"}, message],
        "tokens_in": 10,
        "tokens_out": 5,
        "latency_ms": 100,
    }


async def _start(client: AsyncClient, api_key: Headers) -> str:
    response = await client.post(
        "/v1/runs.start",
        json={"agent_name": "call-assistant", "task_input": TASK, "tool_names": TOOLS},
        headers=api_key,
    )
    assert response.status_code == 200, response.text
    return response.json()["run"]["id"]


async def test_record_and_read_a_failed_run(
    client: AsyncClient, person: Headers, api_key: Headers
) -> None:
    run_id = await _start(client, api_key)
    for index in (1, 2):
        recorded = await client.post("/v1/steps.record", json=_step(run_id, index), headers=api_key)
        assert recorded.status_code == 200, recorded.text
    repeat = await client.post("/v1/steps.record", json=_step(run_id, 1), headers=api_key)
    finish = {
        "run_id": run_id,
        "status": "failed",
        "final_output": "Added the event for the wrong day",
    }
    finished = await client.post("/v1/runs.finish", json=finish, headers=api_key)
    again = await client.post("/v1/runs.finish", json=finish, headers=api_key)

    run = finished.json()["run"]
    assert (run["status"], run["step_count"], run["finished_at"] is not None) == ("failed", 2, True)
    assert repeat.json()["step"]["output"]["content"] == "step 1"
    assert run["tool_names"] == TOOLS
    assert again.json()["code"] == ApiErrorCode.CONFLICT

    first_page = await client.post(
        "/v1/steps.list", json={"run_id": run_id, "limit": 1}, headers=person
    )
    second_page = await client.post(
        "/v1/steps.list",
        json={"run_id": run_id, "limit": 1, "cursor": first_page.json()["next_cursor"]},
        headers=person,
    )
    assert [step["index"] for step in first_page.json()["items"]] == [1]
    assert [step["index"] for step in second_page.json()["items"]] == [2]
    assert second_page.json()["next_cursor"] is None

    step_id = second_page.json()["items"][0]["id"]
    snapshot = await client.get(
        "/v1/steps.getSnapshot", params={"step_id": step_id}, headers=person
    )
    assert len(snapshot.json()["snapshot"]["messages"]) == 2

    listed = await client.post("/v1/runs.list", json={"statuses": ["failed"]}, headers=person)
    counted = await client.post("/v1/runs.count", json={"statuses": ["failed"]}, headers=person)
    assert [item["id"] for item in listed.json()["items"]] == [run_id]
    assert counted.json()["count"] == 1


async def test_another_projects_run_is_not_found(
    client: AsyncClient,
    api_key: Headers,
    make_api_key: Callable[[Headers], Awaitable[Headers]],
) -> None:
    run_id = await _start(client, api_key)
    stranger = bearer(web_token("google-stranger"))

    response = await client.get("/v1/runs.get", params={"run_id": run_id}, headers=stranger)

    assert response.status_code == 404
    assert response.json()["code"] == ApiErrorCode.NOT_FOUND


async def test_steps_cannot_be_added_to_a_finished_run(
    client: AsyncClient, api_key: Headers
) -> None:
    run_id = await _start(client, api_key)
    await client.post(
        "/v1/runs.finish", json={"run_id": run_id, "status": "passed"}, headers=api_key
    )

    response = await client.post("/v1/steps.record", json=_step(run_id, 1), headers=api_key)

    assert response.status_code == 409
