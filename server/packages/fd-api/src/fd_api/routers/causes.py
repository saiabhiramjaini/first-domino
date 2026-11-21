"""Causes routes: list, get and count root cause groups."""

from typing import Annotated

from fastapi import APIRouter, Query

from fd_api.auth.callers import PersonCaller
from fd_api.database import DbSession
from fd_api.errors import error_responses
from fd_api.models.causes import (
    Cause,
    CountCausesRequest,
    CountCausesResponse,
    GetCauseRequest,
    GetCauseResponse,
    ListCausesRequest,
    ListCausesResponse,
)
from fd_api.pagination import decode_cursor, paginate
from fd_database.pages import CountKey
from fd_database.repositories import CausesRepository
from fd_shared.enums import ApiErrorCode
from fd_shared.errors import NotFoundError

router = APIRouter(prefix="/v1", tags=["causes"])


@router.post(
    "/causes.list",
    operation_id="listCauses",
    summary="List causes",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def list_causes(
    body: ListCausesRequest, caller: PersonCaller, session: DbSession
) -> ListCausesResponse:
    """Lists root causes, most runs first."""
    rows = await CausesRepository(session).list_filtered(
        project_id=caller.project_id,
        categories=body.categories,
        limit=body.limit + 1,
        after=decode_cursor(body.cursor, CountKey),
    )
    page, next_cursor = paginate(
        rows, body.limit, lambda row: CountKey(count=row.run_count, id=row.id)
    )
    return ListCausesResponse(items=[Cause.from_row(row) for row in page], next_cursor=next_cursor)


@router.get(
    "/causes.get",
    operation_id="getCause",
    summary="Get a cause",
    responses=error_responses(
        ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.NOT_FOUND, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def get_cause(
    request: Annotated[GetCauseRequest, Query()], caller: PersonCaller, session: DbSession
) -> GetCauseResponse:
    """Returns one root cause. Its runs come from `listDiagnoses` with `cause_ids`."""
    cause = await CausesRepository(session).get(
        project_id=caller.project_id, cause_id=request.cause_id
    )
    if cause is None:
        raise NotFoundError
    return GetCauseResponse(cause=Cause.from_row(cause))


@router.post(
    "/causes.count",
    operation_id="countCauses",
    summary="Count causes",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def count_causes(
    body: CountCausesRequest, caller: PersonCaller, session: DbSession
) -> CountCausesResponse:
    """Counts the causes that match the same filters as `listCauses`."""
    count = await CausesRepository(session).count_filtered(
        project_id=caller.project_id, categories=body.categories
    )
    return CountCausesResponse(count=count)
