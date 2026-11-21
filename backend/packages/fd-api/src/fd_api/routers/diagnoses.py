"""Diagnoses routes: start a diagnosis, get one, and list or count them."""

from typing import Annotated

from fastapi import APIRouter, Query

from fd_api import examples
from fd_api.auth.callers import AnyCaller, PersonCaller
from fd_api.errors import error_responses
from fd_api.models.diagnoses import (
    CountDiagnosesRequest,
    CountDiagnosesResponse,
    CreateDiagnosisRequest,
    CreateDiagnosisResponse,
    GetDiagnosisRequest,
    GetDiagnosisResponse,
    ListDiagnosesRequest,
    ListDiagnosesResponse,
)
from fd_shared.enums import ApiErrorCode, DiagnosisStatus

router = APIRouter(prefix="/v1", tags=["diagnoses"])


@router.post(
    "/diagnoses.create",
    operation_id="createDiagnosis",
    summary="Diagnose a failed run",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST,
        ApiErrorCode.UNAUTHENTICATED,
        ApiErrorCode.NOT_FOUND,
        ApiErrorCode.CONFLICT,
        ApiErrorCode.VALIDATION_FAILED,
    ),
)
async def create_diagnosis(
    body: CreateDiagnosisRequest, caller: AnyCaller
) -> CreateDiagnosisResponse:
    """Starts diagnosing a failed recorded run.

    Answers `409` when the run is not a failed recorded run or a diagnosis of it is running.
    """
    diagnosis = examples.DIAGNOSIS.model_copy(
        update={
            "run_id": body.run_id,
            "status": DiagnosisStatus.QUEUED,
            "verdict_kind": None,
            "first_domino_step": None,
            "search_low": None,
            "search_high": None,
            "verify_passes": None,
            "verify_samples": None,
            "fixed_output": None,
            "explanation": None,
            "cause_id": None,
            "check_count": 0,
            "replay_count": 0,
            "cost_usd": 0.0,
            "created_by_id": caller.actor_id,
            "finished_at": None,
        }
    )
    return CreateDiagnosisResponse(diagnosis=diagnosis)


@router.get(
    "/diagnoses.get",
    operation_id="getDiagnosis",
    summary="Get a diagnosis",
    responses=error_responses(
        ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.NOT_FOUND, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def get_diagnosis(
    request: Annotated[GetDiagnosisRequest, Query()], caller: AnyCaller
) -> GetDiagnosisResponse:
    """Returns one diagnosis. Poll it while `status` is not `done` or `failed`."""
    return GetDiagnosisResponse(diagnosis=examples.DIAGNOSIS)


@router.post(
    "/diagnoses.list",
    operation_id="listDiagnoses",
    summary="List diagnoses",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def list_diagnoses(body: ListDiagnosesRequest, caller: PersonCaller) -> ListDiagnosesResponse:
    """Lists diagnoses, newest first. The runs of a cause come from `cause_ids`."""
    return ListDiagnosesResponse(items=[examples.DIAGNOSIS], next_cursor=None)


@router.post(
    "/diagnoses.count",
    operation_id="countDiagnoses",
    summary="Count diagnoses",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def count_diagnoses(
    body: CountDiagnosesRequest, caller: PersonCaller
) -> CountDiagnosesResponse:
    """Counts the diagnoses that match the same filters as `listDiagnoses`."""
    return CountDiagnosesResponse(count=1)
