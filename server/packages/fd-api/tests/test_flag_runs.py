"""Flagging a passed run as failed, and the failure reason a finished run keeps."""

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

from fd_database.session import Database
from fd_shared.enums import ApiErrorCode

from .conftest import Headers, bearer, web_token
from .test_replay_jobs import AGENT, TASK, _enqueue

REASON = "The user said the agent ignored their request."


async def _run(client: AsyncClient, api_key: Headers, status: str | None, **finish: Any) -> str:
    """A recorded run with one step, finished with `status`, or still running when None."""
    started = await client.post(
        "/v1/runs.start", json={"agent_name": AGENT, "task_input": TASK}, headers=api_key
    )
    run_id = started.json()["run"]["id"]
    message = {"role": "assistant", "content": "On it."}
    step = {
        "run_id": run_id,
        "index": 1,
        "model": "agent-model",
        "output": message,
        "messages": [{"role": "user", "content": TASK["prompt"]}, message],
        "tokens_in": 1,
        "tokens_out": 1,
        "latency_ms": 1,
    }
    await client.post("/v1/steps.record", json=step, headers=api_key)
    if status is not None:
        await client.post(
            "/v1/runs.finish",
            json={"run_id": run_id, "status": status, **finish},
            headers=api_key,
        )
    return run_id


async def _flag(client: AsyncClient, caller: Headers, run_id: str) -> Any:
    return await client.post(
        "/v1/runs.flag", json={"run_id": run_id, "reason": REASON}, headers=caller
    )


async def _actor_ids(client: AsyncClient, person: Headers) -> tuple[str, str]:
    """The person's user id and the id of the API key they made."""
    [key] = (await client.post("/v1/api-keys.list", json={}, headers=person)).json()["items"]
    return key["created_by_id"], key["id"]


@pytest.mark.parametrize("caller_kind", ["person", "api_key"])
async def test_a_passed_run_is_flagged_failed_and_diagnosed(
    client: AsyncClient, person: Headers, api_key: Headers, caller_kind: str
) -> None:
    run_id = await _run(client, api_key, "passed")
    caller = person if caller_kind == "person" else api_key

    flagged = await _flag(client, caller, run_id)

    run = flagged.json()["run"]
    user_id, api_key_id = await _actor_ids(client, person)
    assert flagged.status_code == 200, flagged.text
    assert (run["status"], run["failure_reason"]) == ("failed", REASON)
    assert run["flagged_at"] is not None
    assert run["flagged_by_id"] == (user_id if caller_kind == "person" else api_key_id)
    diagnosis = await client.get(
        "/v1/diagnoses.get", params={"diagnosis_id": run["latest_diagnosis_id"]}, headers=person
    )
    assert diagnosis.json()["diagnosis"]["run_id"] == run_id
    assert diagnosis.json()["diagnosis"]["status"] in {"queued", "bisecting"}


@pytest.mark.parametrize("status", [None, "failed", "errored"])
async def test_only_a_finished_passed_run_can_be_flagged(
    client: AsyncClient, person: Headers, api_key: Headers, status: str | None
) -> None:
    run_id = await _run(client, api_key, status)

    flagged = await _flag(client, person, run_id)

    assert flagged.status_code == 409
    assert flagged.json()["code"] == ApiErrorCode.CONFLICT


async def test_a_replay_run_cannot_be_flagged(
    client: AsyncClient, database: Database, person: Headers, api_key: Headers
) -> None:
    original_id = await _run(client, api_key, "passed")
    project = (await client.get("/v1/projects.self", headers=person)).json()["project"]
    job_id = await _enqueue(database, {"id": original_id}, project["id"])
    await client.post(
        "/v1/replay-jobs.lease", json={"agent_names": [AGENT], "wait_seconds": 0}, headers=api_key
    )
    started = await client.post(
        "/v1/runs.start",
        json={"agent_name": AGENT, "task_input": TASK, "replay_job_id": str(job_id)},
        headers=api_key,
    )
    replay_id = started.json()["run"]["id"]
    await client.post(
        "/v1/runs.finish", json={"run_id": replay_id, "status": "passed"}, headers=api_key
    )

    flagged = await _flag(client, person, replay_id)

    assert flagged.status_code == 409


async def test_flagging_an_unknown_or_another_projects_run_is_not_found(
    client: AsyncClient, api_key: Headers
) -> None:
    run_id = await _run(client, api_key, "passed")
    stranger = bearer(web_token(f"google-{uuid4()}"))

    theirs = await _flag(client, stranger, run_id)
    unknown = await _flag(client, api_key, str(uuid4()))

    assert theirs.status_code == unknown.status_code == 404
    assert theirs.json()["code"] == ApiErrorCode.NOT_FOUND


@pytest.mark.parametrize(("status", "kept"), [("failed", REASON), ("passed", None)])
async def test_finish_keeps_the_failure_reason_only_on_a_failed_run(
    client: AsyncClient, person: Headers, api_key: Headers, status: str, kept: str | None
) -> None:
    run_id = await _run(client, api_key, status, failure_reason=REASON)

    run = await client.get("/v1/runs.get", params={"run_id": run_id}, headers=person)

    assert run.json()["run"]["failure_reason"] == kept
    assert run.json()["run"]["flagged_at"] is None
