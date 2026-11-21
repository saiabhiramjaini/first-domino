"""A second API process starting up never fails a diagnosis another live process is running."""

import asyncio
from uuid import UUID

import httpx
from httpx import AsyncClient
from pydantic import SecretStr

from fd_api.services.diagnosis_runner import DiagnosisRunner
from fd_api.settings import ApiSettings
from fd_database import tables
from fd_database.repositories import DiagnosesRepository
from fd_database.session import Database

from .conftest import TEST_WEB_SECRET, Headers
from .fake_engine import FakeEngine
from .test_replay_jobs import AGENT, _finished_run


async def test_another_process_starting_spares_a_live_diagnosis(
    client: AsyncClient, database: Database, person: Headers, api_key: Headers
) -> None:
    run = await _finished_run(client, api_key, "failed")
    settings = ApiSettings(web_jwt_secret=SecretStr(TEST_WEB_SECRET))
    async with httpx.AsyncClient() as http:
        second_process = DiagnosisRunner(database, FakeEngine(), http, settings)
        await second_process.fail_abandoned()

    diagnosis = await client.get(
        "/v1/diagnoses.get", params={"diagnosis_id": run["latest_diagnosis_id"]}, headers=person
    )

    assert diagnosis.json()["diagnosis"]["status"] in {"queued", "bisecting"}
    assert diagnosis.json()["diagnosis"]["error_code"] is None


async def _answer_replays(client: AsyncClient, api_key: Headers, outcome: str) -> int:
    """Act as the customer's worker: answer every queued replay job. Returns how many."""
    answered = 0
    while True:
        lease = {"agent_names": [AGENT], "wait_seconds": 0}
        job = (await client.post("/v1/replay-jobs.lease", json=lease, headers=api_key)).json()
        if job["replay_job"] is None:
            return answered
        result = {"replay_job_id": job["replay_job"]["id"], "outcome": outcome}
        await client.post("/v1/replay-jobs.submit", json=result, headers=api_key)
        answered += 1


async def test_a_new_process_restarts_an_interrupted_diagnosis_and_finishes_it(
    client: AsyncClient, database: Database, person: Headers, api_key: Headers
) -> None:
    run = await _finished_run(client, api_key, "failed")
    diagnosis_id = UUID(run["latest_diagnosis_id"])
    first_owner = None
    for _ in range(100):
        async with database.transaction() as session:
            first = await session.get(tables.Diagnosis, diagnosis_id)
            first_owner = first.runner_id if first else None
        if first_owner is not None:
            break
        await asyncio.sleep(0.02)
    assert first_owner is not None
    async with database.transaction() as session:
        await DiagnosesRepository(session).release(runner_id=first_owner)
    settings = ApiSettings(
        web_jwt_secret=SecretStr(TEST_WEB_SECRET), replay_poll_interval_seconds=0.05
    )
    async with httpx.AsyncClient() as http:
        second_process = DiagnosisRunner(database, FakeEngine(), http, settings)
        await second_process.restart_abandoned()
        for _ in range(200):
            await _answer_replays(client, api_key, "passed")
            if not second_process.busy:
                break
            await asyncio.sleep(0.05)
        await second_process.shutdown()

    diagnosis = await client.get(
        "/v1/diagnoses.get", params={"diagnosis_id": str(diagnosis_id)}, headers=person
    )
    body = diagnosis.json()["diagnosis"]
    assert (body["status"], body["verdict_kind"], body["first_domino_step"]) == (
        "done",
        "step_verified",
        1,
    )
