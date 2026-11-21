"""Diagnoses routes: start a diagnosis, get one, and list or count them."""

from typing import Annotated

from fastapi import APIRouter, Query

from fd_api.auth.callers import AnyCaller, PersonCaller
from fd_api.database import DbSession
from fd_api.errors import error_responses
from fd_api.models.diagnoses import (
    CountDiagnosesRequest,
    CountDiagnosesResponse,
    CreateDiagnosisRequest,
    CreateDiagnosisResponse,
    Diagnosis,
    GetDiagnosisRequest,
    GetDiagnosisResponse,
    ListDiagnosesRequest,
    ListDiagnosesResponse,
)
from fd_api.pagination import decode_cursor, paginate
from fd_api.services.diagnoses import create_diagnosis
from fd_database.pages import TimeKey
from fd_database.repositories import DiagnosesRepository, RunsRepository
from fd_shared.enums import ApiErrorCode
from fd_shared.errors import NotFoundError

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
async def create_diagnosis_route(
    body: CreateDiagnosisRequest, caller: AnyCaller, session: DbSession
) -> CreateDiagnosisResponse:
    """Starts diagnosing a failed recorded run.

    Answers `409` when the run is not a failed recorded run or a diagnosis of it is running.
    """
    run = await RunsRepository(session).get(
        project_id=caller.project_id, run_id=body.run_id, for_update=True
    )
    if run is None:
        raise NotFoundError
    diagnosis = await create_diagnosis(session, run=run, created_by_id=caller.actor_id)
    return CreateDiagnosisResponse(diagnosis=Diagnosis.from_row(diagnosis))


@router.get(
    "/diagnoses.get",
    operation_id="getDiagnosis",
    summary="Get a diagnosis",
    responses=error_responses(
        ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.NOT_FOUND, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def get_diagnosis(
    request: Annotated[GetDiagnosisRequest, Query()], caller: AnyCaller, session: DbSession
) -> GetDiagnosisResponse:
    """Returns one diagnosis. Poll it while `status` is not `done` or `failed`."""
    diagnosis = await DiagnosesRepository(session).get(
        project_id=caller.project_id, diagnosis_id=request.diagnosis_id
    )
    if diagnosis is None:
        raise NotFoundError
    return GetDiagnosisResponse(diagnosis=Diagnosis.from_row(diagnosis))


@router.post(
    "/diagnoses.list",
    operation_id="listDiagnoses",
    summary="List diagnoses",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def list_diagnoses(
    body: ListDiagnosesRequest, caller: PersonCaller, session: DbSession
) -> ListDiagnosesResponse:
    """Lists diagnoses, newest first. The runs of a cause come from `cause_ids`."""
    rows = await DiagnosesRepository(session).list_filtered(
        project_id=caller.project_id,
        run_ids=body.run_ids,
        cause_ids=body.cause_ids,
        statuses=body.statuses,
        verdict_kinds=body.verdict_kinds,
        limit=body.limit + 1,
        after=decode_cursor(body.cursor, TimeKey),
    )
    page, next_cursor = paginate(
        rows, body.limit, lambda row: TimeKey(at=row.created_at, id=row.id)
    )
    return ListDiagnosesResponse(
        items=[Diagnosis.from_row(row) for row in page], next_cursor=next_cursor
    )


@router.post(
    "/diagnoses.count",
    operation_id="countDiagnoses",
    summary="Count diagnoses",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def count_diagnoses(
    body: CountDiagnosesRequest, caller: PersonCaller, session: DbSession
) -> CountDiagnosesResponse:
    """Counts the diagnoses that match the same filters as `listDiagnoses`."""
    count = await DiagnosesRepository(session).count_filtered(
        project_id=caller.project_id,
        run_ids=body.run_ids,
        cause_ids=body.cause_ids,
        statuses=body.statuses,
        verdict_kinds=body.verdict_kinds,
    )
    return CountDiagnosesResponse(count=count)
