"""Step contract models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from fd_api.pagination import PageRequest, PageResponse
from fd_shared.models import Message


class Step(BaseModel):
    """One step of a run: a model turn and the results of the tools it called."""

    id: UUID
    run_id: UUID
    index: int = Field(ge=1, description="Position in the run, starting at 1.")
    model: str = Field(description="Model id the step called, as the provider names it.")
    output: Message = Field(description="The assistant message the model returned.")
    tool_results: list[Message] = Field(
        description="The `tool` messages answering the output's tool calls."
    )
    tokens_in: int = Field(ge=0, description="Prompt tokens of the model call.")
    tokens_out: int = Field(ge=0, description="Completion tokens of the model call.")
    latency_ms: int = Field(ge=0, description="Duration of the model call, in milliseconds.")
    created_at: datetime = Field(description="Time the step was recorded, in UTC RFC 3339 format.")


class StepSnapshot(BaseModel):
    """The full message list after a step: the save point a replay resumes from."""

    step_id: UUID
    messages: list[Message] = Field(description="Every message in the run after this step.")


class RecordStepRequest(BaseModel):
    """Records one step. Repeating an index returns the stored step and changes nothing."""

    run_id: UUID
    index: int = Field(ge=1, description="Position in the run, starting at 1.")
    model: str = Field(min_length=1, max_length=128, description="Model id the step called.")
    output: Message = Field(description="The assistant message the model returned.")
    tool_results: list[Message] = Field(
        default_factory=list, description="The `tool` messages answering the output's tool calls."
    )
    messages: list[Message] = Field(description="Every message in the run after this step.")
    tokens_in: int = Field(ge=0, description="Prompt tokens of the model call.")
    tokens_out: int = Field(ge=0, description="Completion tokens of the model call.")
    latency_ms: int = Field(ge=0, description="Duration of the model call, in milliseconds.")


class RecordStepResponse(BaseModel):
    """The stored step."""

    step: Step


class ListStepsRequest(PageRequest):
    """Lists the steps of a run in order."""

    run_id: UUID


class ListStepsResponse(PageResponse[Step]):
    """A page of steps."""


class GetStepSnapshotRequest(BaseModel):
    """Gets the message list saved after a step."""

    step_id: UUID


class GetStepSnapshotResponse(BaseModel):
    """The snapshot."""

    snapshot: StepSnapshot
