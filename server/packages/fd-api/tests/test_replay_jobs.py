"""The worker protocol: a failed run is diagnosed, its replay jobs are leased and answered."""

from uuid import UUID, uuid4

from httpx import AsyncClient

from fd_database.repositories import ReplayJobsRepository
from fd_database.session import Database
from fd_database.tables.base import utc_now
from fd_shared.enums import ApiErrorCode, MessageRole
from fd_shared.models import Message, TaskInput

from .conftest import Headers

TASK = {
    "prompt": "Call the clinic and add tomorrow at 10 to the calendar",
    "metadata": {"task_id": "t1"},
}
AGENT = "call-assistant-replays"


async def _finished_run(client: AsyncClient, api_key: Headers, status: str) -> dict:
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
    finished = await client.post(
        "/v1/runs.finish", json={"run_id": run_id, "status": status}, headers=api_key
    )
    return finished.json()["run"]


async def _enqueue(database: Database, run: dict, project_id: str) -> UUID:
    async with database.transaction() as session:
        [job] = await ReplayJobsRepository(session).enqueue(
            project_id=UUID(project_id),
            run_id=UUID(run["id"]),
            diagnosis_id=None,
            check_id=None,
            agent_name=AGENT,
            task_input=TaskInput.model_validate(TASK),
            from_step=0,
            messages=[Message(role=MessageRole.USER, content=TASK["prompt"])],
            replacement_output=None,
            model_override=None,
            samples=1,
        )
    return job.id


async def test_failed_run_is_diagnosed_once_at_a_time(
    client: AsyncClient, person: Headers, api_key: Headers
) -> None:
    run = await _finished_run(client, api_key, "failed")

    diagnosis = await client.get(
        "/v1/diagnoses.get", params={"diagnosis_id": run["latest_diagnosis_id"]}, headers=person
    )
    second = await client.post("/v1/diagnoses.create", json={"run_id": run["id"]}, headers=person)

    assert diagnosis.json()["diagnosis"]["status"] in {"queued", "bisecting"}
    assert diagnosis.json()["diagnosis"]["created_by_id"] is None
    assert second.json()["code"] == ApiErrorCode.CONFLICT


async def test_worker_leases_replays_and_submits_once(
    client: AsyncClient, database: Database, person: Headers, api_key: Headers
) -> None:
    run = await _finished_run(client, api_key, "passed")
    project = (await client.get("/v1/projects.self", headers=person)).json()["project"]
    job_id = await _enqueue(database, run, project["id"])
    lease = {"agent_names": [AGENT], "wait_seconds": 0}

    leased = (await client.post("/v1/replay-jobs.lease", json=lease, headers=api_key)).json()
    replay = await client.post(
        "/v1/runs.start",
        json={"agent_name": AGENT, "task_input": TASK, "replay_job_id": str(job_id)},
        headers=api_key,
    )
    result = {"replay_job_id": str(job_id), "outcome": "passed"}
    submitted = await client.post("/v1/replay-jobs.submit", json=result, headers=api_key)
    repeat = await client.post(
        "/v1/replay-jobs.submit", json={**result, "outcome": "failed"}, headers=api_key
    )
    nothing_left = await client.post("/v1/replay-jobs.lease", json=lease, headers=api_key)

    assert leased["replay_job"]["id"] == str(job_id)
    assert leased["replay_job"]["attempt"] == 1
    assert replay.json()["run"]["parent_run_id"] == run["id"]
    assert replay.json()["run"]["source"] == "replay"
    assert submitted.json()["replay_job"]["status"] == "succeeded"
    assert repeat.json()["replay_job"]["status"] == "succeeded"
    assert nothing_left.json() == {"replay_job": None}


async def test_replay_run_needs_a_leased_job(
    client: AsyncClient, database: Database, person: Headers, api_key: Headers
) -> None:
    run = await _finished_run(client, api_key, "passed")
    project = (await client.get("/v1/projects.self", headers=person)).json()["project"]
    job_id = await _enqueue(database, run, project["id"])

    response = await client.post(
        "/v1/runs.start",
        json={"agent_name": AGENT, "task_input": TASK, "replay_job_id": str(job_id)},
        headers=api_key,
    )

    assert response.json()["code"] == ApiErrorCode.CONFLICT


async def test_worker_sees_a_job_ended_while_it_runs(
    client: AsyncClient, database: Database, person: Headers, api_key: Headers
) -> None:
    run = await _finished_run(client, api_key, "passed")
    project = (await client.get("/v1/projects.self", headers=person)).json()["project"]
    job_id = await _enqueue(database, run, project["id"])
    lease = {"agent_names": [AGENT], "wait_seconds": 0}
    await client.post("/v1/replay-jobs.lease", json=lease, headers=api_key)
    params = {"replay_job_id": str(job_id)}

    running = await client.get("/v1/replay-jobs.get", params=params, headers=api_key)
    async with database.transaction() as session:
        await ReplayJobsRepository(session).expire_unfinished(
            project_id=UUID(project["id"]), replay_job_ids=[job_id], now=utc_now()
        )
    ended = await client.get("/v1/replay-jobs.get", params=params, headers=api_key)
    late = await client.post(
        "/v1/replay-jobs.submit", json={**params, "outcome": "passed"}, headers=api_key
    )
    unknown = await client.get(
        "/v1/replay-jobs.get", params={"replay_job_id": str(uuid4())}, headers=api_key
    )
    by_person = await client.get("/v1/replay-jobs.get", params=params, headers=person)

    assert running.json()["replay_job"]["status"] == "leased"
    assert ended.json()["replay_job"]["status"] == "expired"
    assert late.json()["replay_job"]["status"] == "expired"
    assert unknown.json()["code"] == ApiErrorCode.NOT_FOUND
    assert by_person.status_code == 401
