"""ORM table definitions. Importing this module registers every table on `Base.metadata`."""

from fd_database.tables.base import Base
from fd_database.tables.benchmark import Benchmark, BenchmarkResult
from fd_database.tables.diagnoses import Cause, Check, Diagnosis
from fd_database.tables.projects import ApiKey, Project, User
from fd_database.tables.replay_jobs import ReplayJob
from fd_database.tables.runs import Run, Step

__all__ = [
    "ApiKey",
    "Base",
    "Benchmark",
    "BenchmarkResult",
    "Cause",
    "Check",
    "Diagnosis",
    "Project",
    "ReplayJob",
    "Run",
    "Step",
    "User",
]
