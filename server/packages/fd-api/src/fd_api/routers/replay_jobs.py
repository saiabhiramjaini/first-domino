"""Worker protocol routes: lease a replay job, check on it and submit its result."""

import asyncio
import time
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from fd_api.auth.callers import ApiKeyCaller, Caller, get_settings
from fd_api.database import DbSession, get_database
from fd_api.errors import error_responses
from fd_api.models.replay_jobs import (
    GetReplayJobRequest,
    GetReplayJobResponse,
    LeaseReplayJobRequest,
    LeaseReplayJobResponse,
    ReplayJob,
    SubmitReplayResultRequest,
    SubmitReplayResultResponse,
)
from fd_api.settings import ApiSettings
from fd_database import tables
from fd_database.repositories import ReplayJobsRepository, RunsRepository
from fd_database.session import Database
from fd_database.tables.base import utc_now
from fd_shared.enums import ApiErrorCode
from fd_shared.errors import NotFoundError
from fd_shared.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["replay-jobs"])


async def _try_lease(
    database: Database, caller: Caller, agent_names: list[str], settings: ApiSettings
) -> tables.ReplayJob | None:
    async with database.transaction() as session:
        jobs = ReplayJobsRepository(session)
        now = utc_now()
        await jobs.expire_leases(
            project_id=caller.project_id, now=now, max_attempts=settings.max_job_attempts
        )
        await RunsRepository(session).end_abandoned_replays(
            project_id=caller.project_id,
            now=now,
            ended_before=now - timedelta(seconds=settings.abandoned_replay_grace_seconds),
        )
        return await jobs.lease_next(
            project_id=caller.project_id,
            agent_names=agent_names,
            leased_by_id=caller.actor_id,
            now=now,
            lease_seconds=settings.lease_seconds,
        )


@router.post(
    "/replay-jobs.lease",
    operation_id="leaseReplayJob",
    summary="Lease a replay job",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def lease_replay_job(
    body: LeaseReplayJobRequest,
    caller: ApiKeyCaller,
    database: Annotated[Database, Depends(get_database)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> LeaseReplayJobResponse:
    """Waits up to `wait_seconds` for a queued job for one of `agent_names` and leases it.

    Answers with a null job when none arrived in time; lease again.
    """
    deadline = time.monotonic() + body.wait_seconds
    while True:
        job = await _try_lease(database, caller, body.agent_names, settings)
        if job is not None:
            log.info("replay_jobs.leased", replay_job_id=str(job.id), attempt=job.attempt)
            return LeaseReplayJobResponse(replay_job=ReplayJob.from_row(job))
        if time.monotonic() >= deadline:
            return LeaseReplayJobResponse(replay_job=None)
        await asyncio.sleep(settings.lease_poll_interval_seconds)


@router.get(
    "/replay-jobs.get",
    operation_id="getReplayJob",
    summary="Get a replay job",
    responses=error_responses(
        ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.NOT_FOUND, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def get_replay_job(
    request: Annotated[GetReplayJobRequest, Query()], caller: ApiKeyCaller, session: DbSession
) -> GetReplayJobResponse:
    """Returns one replay job of the caller's project.

    A worker polls it while replaying: once the job is `expired` (nobody waits for its result)
    or leased again by another worker, the replay can stop.
    """
    job = await ReplayJobsRepository(session).get(
        project_id=caller.project_id, replay_job_id=request.replay_job_id
    )
    if job is None:
        raise NotFoundError
    return GetReplayJobResponse(replay_job=ReplayJob.from_row(job))


@router.post(
    "/replay-jobs.submit",
    operation_id="submitReplayResult",
    summary="Submit a replay result",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST,
        ApiErrorCode.UNAUTHENTICATED,
        ApiErrorCode.NOT_FOUND,
        ApiErrorCode.VALIDATION_FAILED,
    ),
)
async def submit_replay_result(
    body: SubmitReplayResultRequest, caller: ApiKeyCaller, session: DbSession
) -> SubmitReplayResultResponse:
    """Reports how a replay ended.

    Idempotent by `replay_job_id`: the first result for a leased job counts, and any later
    one (a repeat, or a late result from an earlier lease) changes nothing.
    """
    job = await ReplayJobsRepository(session).submit(
        project_id=caller.project_id,
        replay_job_id=body.replay_job_id,
        outcome=body.outcome,
        replay_run_id=body.replay_run_id,
        error_code=body.error_code,
        drift=body.drift,
        now=utc_now(),
    )
    if job is None:
        raise NotFoundError
    log.info(
        "replay_jobs.submitted",
        replay_job_id=str(job.id),
        outcome=job.outcome,
        drift_step=job.drift_step,
    )
    return SubmitReplayResultResponse(replay_job=ReplayJob.from_row(job))
