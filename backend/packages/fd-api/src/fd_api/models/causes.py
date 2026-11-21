"""Cause contract models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from fd_api.pagination import CountResponse, PageRequest, PageResponse
from fd_database import tables
from fd_shared.enums import CauseCategory


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
