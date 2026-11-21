"""Replay job contract models: the worker protocol."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from fd_shared.enums import ReplayJobStatus, ReplayOutcome
from fd_shared.models import Message, TaskInput

MAX_LEASE_WAIT_SECONDS = 20
DEFAULT_LEASE_WAIT_SECONDS = 10


class ReplayJob(BaseModel):
    """A request to replay a run from a save point on the customer's worker."""

    id: UUID
    run_id: UUID = Field(description="The recorded run to replay.")
    agent_name: str = Field(description="The agent the worker must run.")
    task_input: TaskInput
    from_step: int = Field(
        ge=0, description="Keep steps 1 to `from_step` as recorded. 0 means start fresh."
    )
    messages: list[Message] = Field(
        description="Messages to resume from, as saved after step `from_step`."
    )
    replacement_output: Message | None = Field(
        description="When set, use it as the next model output instead of calling the model."
    )
    model_override: str | None = Field(
        description="When set, run the rest of the replay with this model id."
    )
    status: ReplayJobStatus
    lease_expires_at: datetime | None = Field(
        description="Time the current lease ends, in UTC RFC 3339 format. Null unless leased."
    )
    attempt: int = Field(ge=0, description="Number of times the job has been leased.")


class LeaseReplayJobRequest(BaseModel):
    """Waits for a replay job for one of these agents and leases it."""

    agent_names: list[str] = Field(
        min_length=1, description="Agents this worker can run. Only their jobs are leased."
    )
    wait_seconds: int = Field(
        default=DEFAULT_LEASE_WAIT_SECONDS,
        ge=0,
        le=MAX_LEASE_WAIT_SECONDS,
        description="How long to wait for a job before answering with none.",
    )


class LeaseReplayJobResponse(BaseModel):
    """The leased job, or null when none arrived in time."""

    replay_job: ReplayJob | None


class SubmitReplayResultRequest(BaseModel):
    """Reports how a replay ended. A repeat, or a late result for a re-leased job, is ignored."""

    replay_job_id: UUID
    outcome: ReplayOutcome
    replay_run_id: UUID | None = Field(
        default=None, description="The run started for this replay, if one was started."
    )
    error_code: str | None = Field(
        default=None,
        max_length=128,
        description="The worker's own code for a crash, when `outcome` is `errored`.",
    )


class SubmitReplayResultResponse(BaseModel):
    """The job after the result."""

    replay_job: ReplayJob
