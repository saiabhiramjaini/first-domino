"""Runs routes: start and finish a run, get one, and list or count them."""

from typing import Annotated

from fastapi import APIRouter, Query

from fd_api import examples
from fd_api.auth.callers import AnyCaller, ApiKeyCaller, PersonCaller
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
    StartRunRequest,
    StartRunResponse,
)
from fd_shared.enums import ApiErrorCode, RunStatus

router = APIRouter(prefix="/v1", tags=["runs"])


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
async def start_run(body: StartRunRequest, caller: ApiKeyCaller) -> StartRunResponse:
    """Starts recording a run.

    With `replay_job_id`, the run is a replay linked to the job's original run. The job must
    be leased (`404` when the project has no such job, `409` when it is not leased).
    """
    run = examples.RUN.model_copy(
        update={
            "agent_name": body.agent_name,
            "task_input": body.task_input,
            "status": RunStatus.RUNNING,
            "step_count": 0,
            "final_output": None,
            "latest_diagnosis_id": None,
            "finished_at": None,
        }
    )
    return StartRunResponse(run=run)


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
async def finish_run(body: FinishRunRequest, caller: ApiKeyCaller) -> FinishRunResponse:
    """Finishes a running run (`409` when already finished).

    A recorded run that finishes `failed` is diagnosed automatically.
    """
    run = examples.RUN.model_copy(
        update={
            "id": body.run_id,
            "status": RunStatus(body.status),
            "final_output": body.final_output,
        }
    )
    return FinishRunResponse(run=run)


@router.get(
    "/runs.get",
    operation_id="getRun",
    summary="Get a run",
    responses=error_responses(
        ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.NOT_FOUND, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def get_run(request: Annotated[GetRunRequest, Query()], caller: AnyCaller) -> GetRunResponse:
    """Returns one run of the caller's project."""
    return GetRunResponse(run=examples.RUN)


@router.post(
    "/runs.list",
    operation_id="listRuns",
    summary="List runs",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def list_runs(body: ListRunsRequest, caller: PersonCaller) -> ListRunsResponse:
    """Lists runs, newest first. Recorded runs only unless `sources` says otherwise."""
    return ListRunsResponse(items=[examples.RUN], next_cursor=None)


@router.post(
    "/runs.count",
    operation_id="countRuns",
    summary="Count runs",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def count_runs(body: CountRunsRequest, caller: PersonCaller) -> CountRunsResponse:
    """Counts the runs that match the same filters as `listRuns`."""
    return CountRunsResponse(count=1)
