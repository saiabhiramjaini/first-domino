"""A second API process starting up never fails a diagnosis another live process is running."""

import httpx
from httpx import AsyncClient
from pydantic import SecretStr

from fd_api.services.diagnosis_runner import DiagnosisRunner
from fd_api.settings import ApiSettings
from fd_database.session import Database

from .conftest import TEST_WEB_SECRET, Headers
from .fake_engine import FakeEngine
from .test_replay_jobs import _finished_run


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
