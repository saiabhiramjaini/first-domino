"""Benchmark results repository."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import ColumnElement, Float, Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.tables import Benchmark, BenchmarkResult
from fd_shared.enums import BenchmarkMethod


def _hit(condition: ColumnElement[bool]) -> ColumnElement[int]:
    """1 when the condition holds, else 0. A missing prediction counts as a miss."""
    return func.coalesce(cast(condition, Integer), 0)


class BenchmarkScoreRow(BaseModel):
    """One method's scores over a benchmark, aggregated in the database."""

    model_config = ConfigDict(frozen=True)

    method: BenchmarkMethod
    runs_scored: int
    exact_accuracy: float
    within_one_accuracy: float
    verified_rate: float | None
    mean_cost_usd: float
    mean_seconds: float


class NewBenchmarkResult(BaseModel):
    """One method's answer for one labelled case, as `fd-scripts` reports it."""

    model_config = ConfigDict(frozen=True)

    method: BenchmarkMethod
    case_id: str
    true_step: int
    predicted_step: int | None
    verified: bool | None
    cost_usd: Decimal
    seconds: float


class BenchmarkRepository:
    """Benchmarks and their per-case results. They belong to no project."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, results: list[NewBenchmarkResult]) -> Benchmark:
        """Stores a finished benchmark with every result."""
        benchmark = Benchmark()
        self._session.add(benchmark)
        await self._session.flush()
        self._session.add_all(
            BenchmarkResult(benchmark_id=benchmark.id, **result.model_dump()) for result in results
        )
        await self._session.flush()
        return benchmark

    async def latest(self) -> Benchmark | None:
        """The newest benchmark."""
        statement = select(Benchmark).order_by(Benchmark.created_at.desc()).limit(1)
        return await self._session.scalar(statement)

    async def scores(self, *, benchmark_id: UUID) -> list[BenchmarkScoreRow]:
        """Per-method scores of one benchmark."""
        result = BenchmarkResult
        error = func.abs(result.predicted_step - result.true_step)
        statement = (
            select(
                result.method,
                func.count().label("runs_scored"),
                func.avg(_hit(result.predicted_step == result.true_step)),
                func.avg(_hit(error <= 1)),
                func.avg(cast(result.verified, Integer)),
                func.avg(result.cost_usd),
                func.avg(cast(result.seconds, Float)),
            )
            .where(result.benchmark_id == benchmark_id)
            .group_by(result.method)
            .order_by(result.method)
        )
        rows = await self._session.execute(statement)
        return [
            BenchmarkScoreRow(
                method=method,
                runs_scored=runs_scored,
                exact_accuracy=float(exact or 0),
                within_one_accuracy=float(within_one or 0),
                verified_rate=None if verified is None else float(verified),
                mean_cost_usd=float(cost or 0),
                mean_seconds=float(seconds or 0),
            )
            for method, runs_scored, exact, within_one, verified, cost, seconds in rows
        ]
