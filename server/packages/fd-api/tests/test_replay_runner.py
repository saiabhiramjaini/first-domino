"""When the engine stops waiting for a replay, the job nobody started is ended."""

import asyncio
from uuid import UUID

from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy import select

from fd_api.adapters.check_tracker import CheckTracker
from fd_api.adapters.replay_runner import QueueReplayRunner
from fd_api.settings import ApiSettings
from fd_database import tables
from fd_database.session import Database
from fd_shared.enums import ReplayJobStatus

from .conftest import TEST_WEB_SECRET, Headers
from .test_replay_jobs import _finished_run

MARKER_MODEL = "cancelled-check-marker"


async def _marked_jobs(database: Database, diagnosis_id: UUID) -> list[tables.ReplayJob]:
    async with database.transaction() as session:
        rows = await session.scalars(
            select(tables.ReplayJob).where(
                tables.ReplayJob.diagnosis_id == diagnosis_id,
                tables.ReplayJob.model_override == MARKER_MODEL,
            )
        )
        return list(rows)


async def test_cancelling_a_replay_ends_its_unstarted_job(
    client: AsyncClient, database: Database, api_key: Headers
) -> None:
    run = await _finished_run(client, api_key, "failed")
    diagnosis_id = UUID(run["latest_diagnosis_id"])
    runner = QueueReplayRunner(
        database,
        project_id=await _project_of(database, run["id"]),
        diagnosis_id=diagnosis_id,
        tracker=CheckTracker(),
        settings=ApiSettings(
            web_jwt_secret=SecretStr(TEST_WEB_SECRET), replay_poll_interval_seconds=0.05
        ),
    )

    waiting = asyncio.create_task(
        runner.replay(
            UUID(run["id"]),
            from_step=1,
            samples=1,
            model_override=MARKER_MODEL,
            replacement_output=None,
        )
    )
    for _ in range(100):
        if await _marked_jobs(database, diagnosis_id):
            break
        await asyncio.sleep(0.02)
    waiting.cancel()
    await asyncio.gather(waiting, return_exceptions=True)

    [job] = await _marked_jobs(database, diagnosis_id)
    assert job.status is ReplayJobStatus.EXPIRED


async def _project_of(database: Database, run_id: str) -> UUID:
    async with database.transaction() as session:
        run = await session.get(tables.Run, UUID(run_id))
        assert run is not None
        return run.project_id
