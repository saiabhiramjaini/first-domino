"""Benchmark tables. Benchmarks score the product as a whole, so they belong to no project."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fd_database.tables.base import Base, IdMixin, TimestampMixin
from fd_database.tables.diagnoses import COST_PRECISION, COST_SCALE
from fd_database.tables.types import BENCHMARK_METHOD
from fd_shared.enums import BenchmarkMethod


class Benchmark(IdMixin, TimestampMixin, Base):
    """One benchmark run over the labelled dataset, written by `fd-scripts`."""

    __tablename__ = "benchmarks"


class BenchmarkResult(IdMixin, TimestampMixin, Base):
    """One method's answer for one labelled case."""

    __tablename__ = "benchmark_results"
    __table_args__ = (UniqueConstraint("benchmark_id", "method", "case_id"),)

    benchmark_id: Mapped[UUID] = mapped_column(ForeignKey("benchmarks.id"))
    method: Mapped[BenchmarkMethod] = mapped_column(BENCHMARK_METHOD)
    case_id: Mapped[str] = mapped_column(String(128))
    true_step: Mapped[int]
    predicted_step: Mapped[int | None]
    verified: Mapped[bool | None]
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(COST_PRECISION, COST_SCALE))
    seconds: Mapped[float]
