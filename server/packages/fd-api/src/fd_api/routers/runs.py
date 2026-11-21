"""Runs routes: start and finish a run, get one, and list or count them."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fd_api.auth.callers import AnyCaller, ApiKeyCaller, Caller, PersonCaller
from fd_api.database import DbSession
from fd_api.errors import error_responses
from fd_api.models.runs import (
    CountRunsRequest,
    CountRunsResponse,
    FinishRunRequest,
    FinishRunResponse,
    GetRunRequest,
    GetRunResponse,
    ListRunsRequest,
    ListRunsResponse,
    Run,
    StartRunRequest,
    StartRunResponse,
)
from fd_api.pagination import decode_cursor, paginate
from fd_api.services.diagnoses import can_diagnose, create_diagnosis
from fd_api.services.diagnosis_runner import DiagnosisRunner, get_diagnosis_runner
from fd_database import tables
from fd_database.pages import TimeKey
from fd_database.repositories import ReplayJobsRepository, RunsRepository
from fd_database.tables.base import utc_now
from fd_shared.enums import ApiErrorCode, ReplayJobStatus, RunSource, RunStatus
from fd_shared.errors import ConflictError, NotFoundError
from fd_shared.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["runs"])


async def _start_replay(
    session: AsyncSession, caller: Caller, body: StartRunRequest, replay_job_id: UUID
) -> tables.Run:
    job = await ReplayJobsRepository(session).get(
        project_id=caller.project_id, replay_job_id=replay_job_id
    )
    if job is None:
        raise NotFoundError
    if job.status is not ReplayJobStatus.LEASED:
        raise ConflictError
    return await RunsRepository(session).create(
        project_id=caller.project_id,
        agent_name=body.agent_name,
        task_input=body.task_input,
        tool_names=body.tool_names,
        created_by_id=caller.actor_id,
        started_at=utc_now(),
        source=RunSource.REPLAY,
        parent_run_id=job.run_id,
        replay_job_id=job.id,
        replay_from_step=job.from_step,
        check_id=job.check_id,
    )


@router.post(
    "/runs.start",
    operation_id="startRun",
    summary="Start a run",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST,
        ApiErrorCode.UNAUTHENTICATED,
        ApiErrorCode.NOT_FOUND,
        ApiErrorCode.CONFLICT,
        ApiErrorCode.VALIDATION_FAILED,
    ),
)
async def start_run(
    body: StartRunRequest, caller: ApiKeyCaller, session: DbSession
) -> StartRunResponse:
    """Starts recording a run.

    With `replay_job_id`, the run is a replay linked to the job's original run. The job must
    be leased (`404` when the project has no such job, `409` when it is not leased).
    """
    if body.replay_job_id is not None:
        run = await _start_replay(session, caller, body, body.replay_job_id)
    else:
        run = await RunsRepository(session).create(
            project_id=caller.project_id,
            agent_name=body.agent_name,
            task_input=body.task_input,
            tool_names=body.tool_names,
            created_by_id=caller.actor_id,
            started_at=utc_now(),
        )
    log.info("runs.started", run_id=str(run.id), source=run.source)
    return StartRunResponse(run=Run.from_row(run))


@router.post(
    "/runs.finish",
    operation_id="finishRun",
    summary="Finish a run",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST,
        ApiErrorCode.UNAUTHENTICATED,
        ApiErrorCode.NOT_FOUND,
        ApiErrorCode.CONFLICT,
        ApiErrorCode.VALIDATION_FAILED,
    ),
)
async def finish_run(
    body: FinishRunRequest,
    caller: ApiKeyCaller,
    session: DbSession,
    background: BackgroundTasks,
    runner: Annotated[DiagnosisRunner, Depends(get_diagnosis_runner)],
) -> FinishRunResponse:
    """Finishes a running run (`409` when already finished).

    A recorded run that finishes `failed` is diagnosed automatically.
    """
    runs = RunsRepository(session)
    run = await runs.get(project_id=caller.project_id, run_id=body.run_id, for_update=True)
    if run is None:
        raise NotFoundError
    if run.status is not RunStatus.RUNNING:
        raise ConflictError
    run = await runs.finish(
        run=run,
        status=RunStatus(body.status),
        final_output=body.final_output,
        finished_at=utc_now(),
    )
    log.info("runs.finished", run_id=str(run.id), status=run.status)
    if can_diagnose(run):
        diagnosis = await create_diagnosis(session, run=run, created_by_id=None)
        background.add_task(
            runner.start, project_id=caller.project_id, run_id=run.id, diagnosis_id=diagnosis.id
        )
    return FinishRunResponse(run=Run.from_row(run))


@router.get(
    "/runs.get",
    operation_id="getRun",
    summary="Get a run",
    responses=error_responses(
        ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.NOT_FOUND, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def get_run(
    request: Annotated[GetRunRequest, Query()], caller: AnyCaller, session: DbSession
) -> GetRunResponse:
    """Returns one run of the caller's project."""
    run = await RunsRepository(session).get(project_id=caller.project_id, run_id=request.run_id)
    if run is None:
        raise NotFoundError
    return GetRunResponse(run=Run.from_row(run))


@router.post(
    "/runs.list",
    operation_id="listRuns",
    summary="List runs",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def list_runs(
    body: ListRunsRequest, caller: PersonCaller, session: DbSession
) -> ListRunsResponse:
    """Lists runs, newest first, or a check's replay runs oldest first when `check_id` is set."""
    rows = await RunsRepository(session).list_filtered(
        project_id=caller.project_id,
        statuses=body.statuses,
        sources=body.sources,
        agent_name=body.agent_name,
        check_id=body.check_id,
        limit=body.limit + 1,
        after=decode_cursor(body.cursor, TimeKey),
        oldest_first=body.check_id is not None,
    )
    page, next_cursor = paginate(
        rows, body.limit, lambda row: TimeKey(at=row.started_at, id=row.id)
    )
    return ListRunsResponse(items=[Run.from_row(row) for row in page], next_cursor=next_cursor)


@router.post(
    "/runs.count",
    operation_id="countRuns",
    summary="Count runs",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def count_runs(
    body: CountRunsRequest, caller: PersonCaller, session: DbSession
) -> CountRunsResponse:
    """Counts the runs that match the same filters as `listRuns`."""
    count = await RunsRepository(session).count_filtered(
        project_id=caller.project_id,
        statuses=body.statuses,
        sources=body.sources,
        agent_name=body.agent_name,
        check_id=body.check_id,
    )
    return CountRunsResponse(count=count)
