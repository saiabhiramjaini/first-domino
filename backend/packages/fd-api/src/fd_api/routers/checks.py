"""Checks routes: the checks of a diagnosis, for the live search view."""

from fastapi import APIRouter

from fd_api.auth.callers import PersonCaller
from fd_api.database import DbSession
from fd_api.errors import error_responses
from fd_api.models.checks import Check, ListChecksRequest, ListChecksResponse
from fd_api.pagination import decode_cursor, paginate
from fd_database.pages import IndexKey
from fd_database.repositories import DiagnosesRepository
from fd_shared.enums import ApiErrorCode
from fd_shared.errors import NotFoundError

router = APIRouter(prefix="/v1", tags=["checks"])


@router.post(
    "/checks.list",
    operation_id="listChecks",
    summary="List the checks of a diagnosis",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST,
        ApiErrorCode.UNAUTHENTICATED,
        ApiErrorCode.NOT_FOUND,
        ApiErrorCode.VALIDATION_FAILED,
    ),
)
async def list_checks(
    body: ListChecksRequest, caller: PersonCaller, session: DbSession
) -> ListChecksResponse:
    """Lists the checks of a diagnosis in `index` order."""
    diagnoses = DiagnosesRepository(session)
    diagnosis = await diagnoses.get(project_id=caller.project_id, diagnosis_id=body.diagnosis_id)
    if diagnosis is None:
        raise NotFoundError
    rows = await diagnoses.list_checks(
        project_id=caller.project_id,
        diagnosis_id=diagnosis.id,
        limit=body.limit + 1,
        after=decode_cursor(body.cursor, IndexKey),
    )
    page, next_cursor = paginate(rows, body.limit, lambda row: IndexKey(index=row.index))
    return ListChecksResponse(items=[Check.from_row(row) for row in page], next_cursor=next_cursor)
