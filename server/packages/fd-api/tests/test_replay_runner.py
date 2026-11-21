"""What the engine reads from a replay job, and how unfinished jobs end when it stops waiting."""

import asyncio
from uuid import UUID, uuid4

from httpx import AsyncClient
from pydantic import SecretStr
from sqlalchemy import select, update

from fd_api.adapters.check_tracker import CheckTracker
from fd_api.adapters.replay_runner import QueueReplayRunner, result_of
from fd_api.settings import ApiSettings
from fd_database import tables
from fd_database.session import Database
from fd_shared.enums import ReplayJobStatus, ReplayOutcome
from fd_shared.models import ReplayDrift, ReplayResult

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


async def test_cancelling_a_replay_ends_its_queued_and_running_jobs(
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
            samples=2,
            model_override=MARKER_MODEL,
            replacement_output=None,
        )
    )
    for _ in range(100):
        if await _marked_jobs(database, diagnosis_id):
            break
        await asyncio.sleep(0.02)
    running = (await _marked_jobs(database, diagnosis_id))[0]
    async with database.transaction() as session:
        await session.execute(
            update(tables.ReplayJob)
            .where(tables.ReplayJob.id == running.id)
            .values(status=ReplayJobStatus.LEASED)
        )
    waiting.cancel()
    await asyncio.gather(waiting, return_exceptions=True)

    jobs = await _marked_jobs(database, diagnosis_id)
    assert [job.status for job in jobs] == [ReplayJobStatus.EXPIRED] * 2


async def _project_of(database: Database, run_id: str) -> UUID:
    async with database.transaction() as session:
        run = await session.get(tables.Run, UUID(run_id))
        assert run is not None
        return run.project_id


def _job(
    status: ReplayJobStatus, outcome: ReplayOutcome | None, drift_step: int | None
) -> tables.ReplayJob:
    return tables.ReplayJob(
        status=status, outcome=outcome, drift_step=drift_step, drift_tool_name="lookup"
    )


def test_a_finished_job_reports_its_drift() -> None:
    job = _job(ReplayJobStatus.SUCCEEDED, ReplayOutcome.PASSED, 2)

    assert result_of(job) == ReplayResult(
        outcome=ReplayOutcome.PASSED, drift=ReplayDrift(step=2, tool_name="lookup")
    )


def test_a_job_that_ended_without_a_result_is_errored_without_drift() -> None:
    job = _job(ReplayJobStatus.EXPIRED, None, 2)

    assert result_of(job) == ReplayResult(outcome=ReplayOutcome.ERRORED)


def test_an_open_job_has_no_result_yet() -> None:
    assert result_of(_job(ReplayJobStatus.LEASED, None, None)) is None


def test_a_finished_job_names_the_run_its_replay_recorded() -> None:
    replay_run_id = uuid4()
    job = _job(ReplayJobStatus.SUCCEEDED, ReplayOutcome.PASSED, None)
    job.replay_run_id = replay_run_id

    result = result_of(job)

    assert result is not None
    assert result.replay_run_id == replay_run_id
