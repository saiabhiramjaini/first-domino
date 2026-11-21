"""Benchmarks routes: the latest benchmark scores."""

from fastapi import APIRouter

from fd_api import examples
from fd_api.auth.callers import PersonCaller
from fd_api.errors import error_responses
from fd_api.models.benchmarks import GetLatestBenchmarkResponse
from fd_shared.enums import ApiErrorCode

router = APIRouter(prefix="/v1", tags=["benchmarks"])


@router.get(
    "/benchmarks.latest",
    operation_id="getLatestBenchmark",
    summary="Get the latest benchmark",
    responses=error_responses(ApiErrorCode.UNAUTHENTICATED),
)
async def get_latest_benchmark(caller: PersonCaller) -> GetLatestBenchmarkResponse:
    """Returns the newest benchmark scores, or null when none has run."""
    return GetLatestBenchmarkResponse(benchmark=examples.BENCHMARK)
