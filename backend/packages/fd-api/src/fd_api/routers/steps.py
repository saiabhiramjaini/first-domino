"""Steps routes: record a step, list the steps of a run and read a save point."""

from typing import Annotated

from fastapi import APIRouter, Query

from fd_api import examples
from fd_api.auth.callers import AnyCaller, ApiKeyCaller
from fd_api.errors import error_responses
from fd_api.models.steps import (
    GetStepSnapshotRequest,
    GetStepSnapshotResponse,
    ListStepsRequest,
    ListStepsResponse,
    RecordStepRequest,
    RecordStepResponse,
)
from fd_shared.enums import ApiErrorCode

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
async def record_step(body: RecordStepRequest, caller: ApiKeyCaller) -> RecordStepResponse:
    """Records one step of a running run (`409` when the run is finished).

    Idempotent on (`run_id`, `index`): a repeat returns the stored step and changes nothing.
    """
    step = examples.STEPS[0].model_copy(
        update={
            "run_id": body.run_id,
            "index": body.index,
            "model": body.model,
            "output": body.output,
            "tool_results": body.tool_results,
            "tokens_in": body.tokens_in,
            "tokens_out": body.tokens_out,
            "latency_ms": body.latency_ms,
        }
    )
    return RecordStepResponse(step=step)


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
async def list_steps(body: ListStepsRequest, caller: AnyCaller) -> ListStepsResponse:
    """Lists the steps of a run in index order."""
    return ListStepsResponse(items=examples.STEPS, next_cursor=None)


@router.get(
    "/steps.getSnapshot",
    operation_id="getStepSnapshot",
    summary="Get the save point after a step",
    responses=error_responses(
        ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.NOT_FOUND, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def get_step_snapshot(
    request: Annotated[GetStepSnapshotRequest, Query()], caller: AnyCaller
) -> GetStepSnapshotResponse:
    """Returns the full message list saved after a step."""
    snapshot = examples.SNAPSHOT.model_copy(update={"step_id": request.step_id})
    return GetStepSnapshotResponse(snapshot=snapshot)
