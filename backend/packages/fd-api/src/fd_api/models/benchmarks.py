"""Benchmark contract models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from fd_shared.enums import BenchmarkMethod


class BenchmarkScore(BaseModel):
    """How well one method found the labelled first domino step."""

    method: BenchmarkMethod
    runs_scored: int = Field(ge=0, description="Number of labelled runs the method was scored on.")
    exact_accuracy: float = Field(
        ge=0, le=1, description="Share of runs where it named the labelled step exactly."
    )
    within_one_accuracy: float = Field(
        ge=0, le=1, description="Share of runs where it was at most one step off."
    )
    verified_rate: float | None = Field(
        ge=0, le=1, description="Share of runs with a fix proven by replay. Null without proof."
    )
    mean_cost_usd: float = Field(ge=0, description="Mean model cost per run, in US dollars.")
    mean_seconds: float = Field(ge=0, description="Mean wall time per run, in seconds.")


class Benchmark(BaseModel):
    """One benchmark run over the labelled dataset."""

    id: UUID
    created_at: datetime = Field(description="Time the benchmark finished, in UTC RFC 3339 format.")
    scores: list[BenchmarkScore] = Field(description="One score per method.")


class GetLatestBenchmarkResponse(BaseModel):
    """The newest benchmark, or null when none has run."""

    benchmark: Benchmark | None
