"""Checks routes: the checks of a diagnosis, for the live search view."""

from fastapi import APIRouter

from fd_api import examples
from fd_api.auth.callers import PersonCaller
from fd_api.errors import error_responses
from fd_api.models.checks import ListChecksRequest, ListChecksResponse
from fd_shared.enums import ApiErrorCode

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
async def list_checks(body: ListChecksRequest, caller: PersonCaller) -> ListChecksResponse:
    """Lists the checks of a diagnosis in `index` order."""
    return ListChecksResponse(items=examples.CHECKS, next_cursor=None)
