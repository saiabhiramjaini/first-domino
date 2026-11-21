"""Cause contract models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from fd_api.pagination import CountResponse, PageRequest, PageResponse
from fd_database import tables
from fd_shared.enums import CauseCategory
from fd_shared.models import Message, TaskInput


class Cause(BaseModel):
    """A root cause shared by one or more diagnosed runs."""

    id: UUID
    title: str = Field(max_length=256, description="Short name of the mistake.")
    category: CauseCategory
    step_name: str = Field(
        max_length=128, description="The tool the first domino step called, or its role label."
    )
    summary: str = Field(description="What goes wrong and why it dooms the run.")
    suggested_fix: str = Field(description="What to change in the agent so it stops happening.")
    run_count: int = Field(ge=0, description="Number of diagnosed runs with this cause.")
    verified_count: int = Field(
        ge=0, description="Number of those runs where a fix was proven by replay."
    )
    first_seen_at: datetime = Field(
        description="Time of the first diagnosis with this cause, in UTC RFC 3339 format."
    )
    last_seen_at: datetime = Field(
        description="Time of the latest diagnosis with this cause, in UTC RFC 3339 format."
    )

    @classmethod
    def from_row(cls, row: tables.Cause) -> "Cause":
        """Maps a stored cause to the contract."""
        return cls(
            id=row.id,
            title=row.title,
            category=row.category,
            step_name=row.step_name,
            summary=row.summary,
            suggested_fix=row.suggested_fix,
            run_count=row.run_count,
            verified_count=row.verified_count,
            first_seen_at=row.first_seen_at,
            last_seen_at=row.last_seen_at,
        )


class CauseFilter(BaseModel):
    """Filters shared by `listCauses` and `countCauses`. Null means no filter."""

    categories: list[CauseCategory] | None = Field(
        default=None, description="Only causes in one of these categories."
    )


class ListCausesRequest(PageRequest, CauseFilter):
    """Lists causes, most runs first."""


class ListCausesResponse(PageResponse[Cause]):
    """A page of causes."""


class GetCauseRequest(BaseModel):
    """Gets one cause."""

    cause_id: UUID


class GetCauseResponse(BaseModel):
    """The cause."""

    cause: Cause


class CountCausesRequest(CauseFilter):
    """Counts causes."""


class CountCausesResponse(CountResponse):
    """The number of matching causes."""


class RegressionCase(BaseModel):
    """One failed run of a cause, as a test the fixed agent must pass.

    Replay the agent from `messages`: the original run failed after `original_output`, and
    passed in replays that used `fixed_output` instead.
    """

    run_id: UUID = Field(description="The failed recorded run.")
    diagnosis_id: UUID = Field(description="The diagnosis that proved the cause on this run.")
    agent_name: str = Field(description="The agent the case is for.")
    task_input: TaskInput
    first_domino_step: int = Field(ge=1, description="The step where the run became doomed.")
    messages: list[Message] = Field(
        description="The conversation just before the first domino step: the test's input."
    )
    original_output: Message = Field(description="What the agent did at that step and failed.")
    fixed_output: Message | None = Field(
        description="The corrected step that replays passed with, when one was found."
    )
    verified: bool = Field(description="Whether replays proved the fix flips the run to passing.")


class CauseExport(BaseModel):
    """A cause's failed runs as regression tests for the customer's eval suite."""

    cause_id: UUID
    exported_at: datetime = Field(description="Time of the export, in UTC RFC 3339 format.")
    cases: list[RegressionCase] = Field(description="Newest first, at most one per run.")


class ExportCauseRequest(BaseModel):
    """Exports a cause's diagnosed runs as regression test cases."""

    cause_id: UUID


class ExportCauseResponse(BaseModel):
    """The export."""

    export: CauseExport
