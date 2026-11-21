"""Run contract models."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from fd_api.pagination import CountResponse, PageRequest, PageResponse
from fd_database import tables
from fd_shared.enums import RunOutcome, RunSource, RunStatus
from fd_shared.models import TaskInput

AGENT_NAME_MAX_LENGTH = 128
MAX_TOOL_NAMES = 128


class Run(BaseModel):
    """One agent run: recorded from the customer's traffic, or replayed for a diagnosis."""

    id: UUID
    agent_name: str = Field(description="The customer's name for the agent, such as `booker`.")
    source: RunSource
    parent_run_id: UUID | None = Field(
        description="For a replay, the recorded run it replays. Null for a recorded run."
    )
    replay_job_id: UUID | None = Field(description="For a replay, the job that asked for it.")
    replay_from_step: int | None = Field(
        description="For a replay, the last step kept from the parent run (0 means none)."
    )
    check_id: UUID | None = Field(
        default=None,
        description="For a replay run for a diagnosis, the check it was replayed for.",
    )
    task_input: TaskInput
    tool_names: list[str] = Field(description="Names of the tools the agent was given.")
    status: RunStatus
    step_count: int = Field(ge=0, description="Number of steps recorded so far.")
    final_output: str | None = Field(description="The agent's final answer, if it gave one.")
    latest_diagnosis_id: UUID | None = Field(description="The newest diagnosis of this run.")
    created_by_id: UUID = Field(description="Id of the API key that recorded the run.")
    started_at: datetime = Field(description="Time the run started, in UTC RFC 3339 format.")
    finished_at: datetime | None = Field(
        description="Time the run finished, in UTC RFC 3339 format. Null while running."
    )

    @classmethod
    def from_row(cls, row: tables.Run) -> "Run":
        """Maps a stored run to the contract."""
        return cls(
            id=row.id,
            agent_name=row.agent_name,
            source=row.source,
            parent_run_id=row.parent_run_id,
            replay_job_id=row.replay_job_id,
            replay_from_step=row.replay_from_step,
            check_id=row.check_id,
            task_input=row.task_input,
            tool_names=row.tool_names,
            status=row.status,
            step_count=row.step_count,
            final_output=row.final_output,
            latest_diagnosis_id=row.latest_diagnosis_id,
            created_by_id=row.created_by_id,
            started_at=row.started_at,
            finished_at=row.finished_at,
        )


class RunFilter(BaseModel):
    """Filters shared by `listRuns` and `countRuns`. Null means no filter."""

    statuses: list[RunStatus] | None = Field(
        default=None, description="Only runs with one of these statuses."
    )
    sources: list[RunSource] | None = Field(
        default_factory=lambda: [RunSource.RECORDED],
        description=(
            "Only runs from one of these sources. Unless set: recorded runs only, or replay "
            "runs only when `check_id` is set."
        ),
    )
    agent_name: str | None = Field(
        default=None, max_length=AGENT_NAME_MAX_LENGTH, description="Only runs of this agent."
    )
    check_id: UUID | None = Field(
        default=None,
        description="Only the replay runs made for this check, oldest first.",
    )

    @model_validator(mode="after")
    def _replays_for_a_check(self) -> Self:
        if self.check_id is not None and "sources" not in self.model_fields_set:
            self.sources = [RunSource.REPLAY]
        return self


class StartRunRequest(BaseModel):
    """Starts recording a run, or a replay when `replay_job_id` is set."""

    agent_name: str = Field(
        min_length=1,
        max_length=AGENT_NAME_MAX_LENGTH,
        description="The customer's name for the agent. Replay jobs are routed by it.",
    )
    task_input: TaskInput
    tool_names: list[str] = Field(
        default_factory=list,
        max_length=MAX_TOOL_NAMES,
        description="Names of the tools the agent was given, for explaining its mistakes.",
    )
    replay_job_id: UUID | None = Field(
        default=None, description="The leased replay job this run carries out, if any."
    )


class StartRunResponse(BaseModel):
    """The new run."""

    run: Run


class FinishRunRequest(BaseModel):
    """Finishes a run with the customer's success check result."""

    run_id: UUID
    status: RunOutcome
    final_output: str | None = Field(default=None, description="The agent's final answer.")


class FinishRunResponse(BaseModel):
    """The finished run."""

    run: Run


class GetRunRequest(BaseModel):
    """Gets one run."""

    run_id: UUID


class GetRunResponse(BaseModel):
    """The run."""

    run: Run


class ListRunsRequest(PageRequest, RunFilter):
    """Lists runs, newest first."""


class ListRunsResponse(PageResponse[Run]):
    """A page of runs."""


class CountRunsRequest(RunFilter):
    """Counts runs."""


class CountRunsResponse(CountResponse):
    """The number of matching runs."""
