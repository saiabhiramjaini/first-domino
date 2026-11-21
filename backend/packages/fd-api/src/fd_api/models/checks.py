"""Check contract models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from fd_api.pagination import PageRequest, PageResponse
from fd_shared.enums import CheckPhase, CheckResult


class Check(BaseModel):
    """One test inside a diagnosis: replay from a save point several times and count passes."""

    id: UUID
    diagnosis_id: UUID
    index: int = Field(ge=0, description="Order of the check within its diagnosis.")
    phase: CheckPhase
    save_point: int = Field(
        ge=0, description="Steps 1 to `save_point` are kept as recorded; the rest are replayed."
    )
    samples: int = Field(ge=0, description="Number of replays run.")
    passes: int = Field(ge=0, description="Number of replays that passed the success check.")
    result: CheckResult
    created_at: datetime = Field(description="Time the check started, in UTC RFC 3339 format.")
    finished_at: datetime | None = Field(
        description="Time the check finished, in UTC RFC 3339 format. Null while pending."
    )


class ListChecksRequest(PageRequest):
    """Lists the checks of a diagnosis, in order."""

    diagnosis_id: UUID


class ListChecksResponse(PageResponse[Check]):
    """A page of checks."""
