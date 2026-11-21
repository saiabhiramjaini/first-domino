"""Steps routes: record a step, list the steps of a run and read a save point."""

from typing import Annotated

from fastapi import APIRouter, Query

from fd_api.auth.callers import AnyCaller, ApiKeyCaller
from fd_api.database import DbSession
from fd_api.errors import error_responses
from fd_api.models.steps import (
    GetStepSnapshotRequest,
    GetStepSnapshotResponse,
    ListStepsRequest,
    ListStepsResponse,
    RecordStepRequest,
    RecordStepResponse,
    Step,
    StepSnapshot,
)
from fd_api.pagination import decode_cursor, paginate
from fd_database.pages import IndexKey
from fd_database.repositories import RunsRepository, StepsRepository
from fd_shared.enums import ApiErrorCode, RunStatus
from fd_shared.errors import ConflictError, NotFoundError

router = APIRouter(prefix="/v1", tags=["steps"])


@router.post(
    "/steps.record",
    operation_id="recordStep",
    summary="Record a step",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST,
        ApiErrorCode.UNAUTHENTICATED,
        ApiErrorCode.NOT_FOUND,
        ApiErrorCode.CONFLICT,
        ApiErrorCode.VALIDATION_FAILED,
    ),
)
async def record_step(
    body: RecordStepRequest, caller: ApiKeyCaller, session: DbSession
) -> RecordStepResponse:
    """Records one step of a running run (`409` when the run is finished).

    Idempotent on (`run_id`, `index`): a repeat returns the stored step and changes nothing,
    even after the run finished.
    """
    runs, steps = RunsRepository(session), StepsRepository(session)
    run = await runs.get(project_id=caller.project_id, run_id=body.run_id, for_update=True)
    if run is None:
        raise NotFoundError
    stored = await steps.get_by_index(project_id=run.project_id, run_id=run.id, index=body.index)
    if stored is not None:
        return RecordStepResponse(step=Step.from_row(stored))
    if run.status is not RunStatus.RUNNING:
        raise ConflictError
    step = await steps.record(
        project_id=run.project_id,
        run_id=run.id,
        index=body.index,
        model=body.model,
        output=body.output,
        tool_results=body.tool_results,
        messages=body.messages,
        tokens_in=body.tokens_in,
        tokens_out=body.tokens_out,
        latency_ms=body.latency_ms,
    )
    await runs.set_step_count(run=run, step_count=step.index)
    return RecordStepResponse(step=Step.from_row(step))


@router.post(
    "/steps.list",
    operation_id="listSteps",
    summary="List the steps of a run",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST,
        ApiErrorCode.UNAUTHENTICATED,
        ApiErrorCode.NOT_FOUND,
        ApiErrorCode.VALIDATION_FAILED,
    ),
)
async def list_steps(
    body: ListStepsRequest, caller: AnyCaller, session: DbSession
) -> ListStepsResponse:
    """Lists the steps of a run in index order."""
    run = await RunsRepository(session).get(project_id=caller.project_id, run_id=body.run_id)
    if run is None:
        raise NotFoundError
    rows = await StepsRepository(session).list_page(
        project_id=caller.project_id,
        run_id=run.id,
        limit=body.limit + 1,
        after=decode_cursor(body.cursor, IndexKey),
    )
    page, next_cursor = paginate(rows, body.limit, lambda row: IndexKey(index=row.index))
    return ListStepsResponse(items=[Step.from_row(row) for row in page], next_cursor=next_cursor)


@router.get(
    "/steps.getSnapshot",
    operation_id="getStepSnapshot",
    summary="Get the save point after a step",
    responses=error_responses(
        ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.NOT_FOUND, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def get_step_snapshot(
    request: Annotated[GetStepSnapshotRequest, Query()], caller: AnyCaller, session: DbSession
) -> GetStepSnapshotResponse:
    """Returns the full message list saved after a step."""
    step = await StepsRepository(session).get(project_id=caller.project_id, step_id=request.step_id)
    if step is None:
        raise NotFoundError
    return GetStepSnapshotResponse(snapshot=StepSnapshot(step_id=step.id, messages=step.messages))
