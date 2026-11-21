"""Diagnosis contract models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from fd_api.pagination import CountResponse, PageRequest, PageResponse
from fd_database import tables
from fd_database.repositories import WaitingReplays
from fd_shared.enums import DiagnosisErrorCode, DiagnosisStatus, VerdictKind
from fd_shared.models import Explanation, Message


class Diagnosis(BaseModel):
    """One search for the first domino step of a failed run, and its proof."""

    id: UUID
    run_id: UUID = Field(description="The failed recorded run being diagnosed.")
    status: DiagnosisStatus
    verdict_kind: VerdictKind | None = Field(description="The conclusion. Null until `done`.")
    first_domino_step: int | None = Field(
        description="Index of the step that doomed the run, once found."
    )
    search_low: int | None = Field(
        description="Lowest step still suspected. Null before the search starts."
    )
    search_high: int | None = Field(
        description="Highest step still suspected. Null before the search starts."
    )
    verify_passes: int | None = Field(
        description="Replays from the fixed step that passed. Null before verifying."
    )
    verify_samples: int | None = Field(
        description="Replays from the fixed step that ran. Null before verifying."
    )
    fixed_output: Message | None = Field(
        description="The rewritten first domino step used to verify the cause."
    )
    explanation: Explanation | None = Field(description="What went wrong, once explained.")
    cause_id: UUID | None = Field(description="The cause group this diagnosis joined.")
    check_count: int = Field(ge=0, description="Number of checks run so far.")
    replay_count: int = Field(ge=0, description="Number of replays asked for so far.")
    replays_waiting: int = Field(
        default=0,
        ge=0,
        description="Replays queued for your worker that no worker has picked up yet.",
    )
    waiting_since: datetime | None = Field(
        default=None,
        description="When the oldest waiting replay was queued, in UTC RFC 3339 format.",
    )
    cost_usd: float = Field(ge=0, description="Model cost of the diagnosis so far, in US dollars.")
    error_code: DiagnosisErrorCode | None = Field(
        description="Why the diagnosis failed. Null unless `failed`."
    )
    created_by_id: UUID | None = Field(
        description="Id of the person or API key that asked for it. Null for auto-diagnosis."
    )
    created_at: datetime = Field(description="Time of creation, in UTC RFC 3339 format.")
    finished_at: datetime | None = Field(
        description="Time it reached `done` or `failed`, in UTC RFC 3339 format."
    )

    @classmethod
    def from_row(cls, row: tables.Diagnosis, waiting: WaitingReplays | None = None) -> "Diagnosis":
        """Maps a stored diagnosis, and its replays still waiting for a worker, to the contract."""
        return cls(
            id=row.id,
            run_id=row.run_id,
            status=row.status,
            verdict_kind=row.verdict_kind,
            first_domino_step=row.first_domino_step,
            search_low=row.search_low,
            search_high=row.search_high,
            verify_passes=row.verify_passes,
            verify_samples=row.verify_samples,
            fixed_output=row.fixed_output,
            explanation=row.explanation,
            cause_id=row.cause_id,
            check_count=row.check_count,
            replay_count=row.replay_count,
            replays_waiting=waiting.count if waiting else 0,
            waiting_since=waiting.oldest_queued_at if waiting else None,
            cost_usd=float(row.cost_usd),
            error_code=row.error_code,
            created_by_id=row.created_by_id,
            created_at=row.created_at,
            finished_at=row.finished_at,
        )


class DiagnosisFilter(BaseModel):
    """Filters shared by `listDiagnoses` and `countDiagnoses`. Null means no filter."""

    run_ids: list[UUID] | None = Field(default=None, description="Only diagnoses of these runs.")
    cause_ids: list[UUID] | None = Field(
        default=None, description="Only diagnoses in these cause groups."
    )
    statuses: list[DiagnosisStatus] | None = Field(
        default=None, description="Only diagnoses with one of these statuses."
    )
    verdict_kinds: list[VerdictKind] | None = Field(
        default=None, description="Only diagnoses with one of these verdicts."
    )


class CreateDiagnosisRequest(BaseModel):
    """Starts diagnosing a failed recorded run."""

    run_id: UUID


class CreateDiagnosisResponse(BaseModel):
    """The new diagnosis, `queued`."""

    diagnosis: Diagnosis


class GetDiagnosisRequest(BaseModel):
    """Gets one diagnosis."""

    diagnosis_id: UUID


class GetDiagnosisResponse(BaseModel):
    """The diagnosis."""

    diagnosis: Diagnosis


class ListDiagnosesRequest(PageRequest, DiagnosisFilter):
    """Lists diagnoses, newest first."""


class ListDiagnosesResponse(PageResponse[Diagnosis]):
    """A page of diagnoses."""


class CountDiagnosesRequest(DiagnosisFilter):
    """Counts diagnoses."""


class CountDiagnosesResponse(CountResponse):
    """The number of matching diagnoses."""
