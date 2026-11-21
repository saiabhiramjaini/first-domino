"""Benchmarks routes: the latest benchmark scores."""

from fastapi import APIRouter

from fd_api.auth.callers import PersonCaller
from fd_api.database import DbSession
from fd_api.errors import error_responses
from fd_api.models.benchmarks import Benchmark, GetLatestBenchmarkResponse
from fd_database.repositories import BenchmarkRepository
from fd_shared.enums import ApiErrorCode

router = APIRouter(prefix="/v1", tags=["benchmarks"])


@router.get(
    "/benchmarks.latest",
    operation_id="getLatestBenchmark",
    summary="Get the latest benchmark",
    responses=error_responses(ApiErrorCode.UNAUTHENTICATED),
)
async def get_latest_benchmark(
    caller: PersonCaller, session: DbSession
) -> GetLatestBenchmarkResponse:
    """Returns the newest benchmark scores, or null when none has run."""
    benchmarks = BenchmarkRepository(session)
    benchmark = await benchmarks.latest()
    if benchmark is None:
        return GetLatestBenchmarkResponse(benchmark=None)
    scores = await benchmarks.scores(benchmark_id=benchmark.id)
    return GetLatestBenchmarkResponse(benchmark=Benchmark.from_row(benchmark, scores))
