"""Causes routes: list, get and count root cause groups."""

from typing import Annotated

from fastapi import APIRouter, Query

from fd_api import examples
from fd_api.auth.callers import PersonCaller
from fd_api.errors import error_responses
from fd_api.models.causes import (
    CountCausesRequest,
    CountCausesResponse,
    GetCauseRequest,
    GetCauseResponse,
    ListCausesRequest,
    ListCausesResponse,
)
from fd_shared.enums import ApiErrorCode

router = APIRouter(prefix="/v1", tags=["causes"])


@router.post(
    "/causes.list",
    operation_id="listCauses",
    summary="List causes",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def list_causes(body: ListCausesRequest, caller: PersonCaller) -> ListCausesResponse:
    """Lists root causes, most runs first."""
    return ListCausesResponse(items=[examples.CAUSE], next_cursor=None)


@router.get(
    "/causes.get",
    operation_id="getCause",
    summary="Get a cause",
    responses=error_responses(
        ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.NOT_FOUND, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def get_cause(
    request: Annotated[GetCauseRequest, Query()], caller: PersonCaller
) -> GetCauseResponse:
    """Returns one root cause. Its runs come from `listDiagnoses` with `cause_ids`."""
    return GetCauseResponse(cause=examples.CAUSE)


@router.post(
    "/causes.count",
    operation_id="countCauses",
    summary="Count causes",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def count_causes(body: CountCausesRequest, caller: PersonCaller) -> CountCausesResponse:
    """Counts the causes that match the same filters as `listCauses`."""
    return CountCausesResponse(count=1)
