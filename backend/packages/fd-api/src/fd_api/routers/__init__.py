"""One router per resource."""

from fastapi import APIRouter

from fd_api.routers import (
    api_keys,
    benchmarks,
    causes,
    checks,
    diagnoses,
    health,
    projects,
    replay_jobs,
    runs,
    steps,
)

ROUTERS: list[APIRouter] = [
    health.router,
    projects.router,
    api_keys.router,
    runs.router,
    steps.router,
    diagnoses.router,
    checks.router,
    causes.router,
    benchmarks.router,
    replay_jobs.router,
]
