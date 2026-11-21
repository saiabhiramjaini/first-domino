"""Worker protocol routes: lease a replay job and submit its result."""

from fastapi import APIRouter

from fd_api import examples
from fd_api.auth.callers import ApiKeyCaller
from fd_api.errors import error_responses
from fd_api.models.replay_jobs import (
    LeaseReplayJobRequest,
    LeaseReplayJobResponse,
    SubmitReplayResultRequest,
    SubmitReplayResultResponse,
)
from fd_shared.enums import ApiErrorCode, ReplayJobStatus, ReplayOutcome

router = APIRouter(prefix="/v1", tags=["replay-jobs"])


@router.post(
    "/replay-jobs.lease",
    operation_id="leaseReplayJob",
    summary="Lease a replay job",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def lease_replay_job(
    body: LeaseReplayJobRequest, caller: ApiKeyCaller
) -> LeaseReplayJobResponse:
    """Waits up to `wait_seconds` for a queued job for one of `agent_names` and leases it.

    Answers with a null job when none arrived in time; lease again.
    """
    return LeaseReplayJobResponse(replay_job=examples.REPLAY_JOB)


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
    body: SubmitReplayResultRequest, caller: ApiKeyCaller
) -> SubmitReplayResultResponse:
    """Reports how a replay ended.

    Idempotent by `replay_job_id`. A late result for a job that was leased again is ignored.
    """
    status = (
        ReplayJobStatus.SUCCEEDED
        if body.outcome is not ReplayOutcome.ERRORED
        else ReplayJobStatus.FAILED
    )
    replay_job = examples.REPLAY_JOB.model_copy(
        update={"id": body.replay_job_id, "status": status, "lease_expires_at": None}
    )
    return SubmitReplayResultResponse(replay_job=replay_job)
