"""Task input and the run as the engine reads it."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from fd_shared.enums import RunStatus


class TaskInput(BaseModel):
    """What the agent was asked to do."""

    model_config = ConfigDict(frozen=True)

    prompt: str = Field(description="The task given to the agent.")
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Customer data the success check needs, such as a `task_id`.",
    )


class RunView(BaseModel):
    """A recorded run as the engine reads it."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    agent_name: str
    task_input: TaskInput
    tool_names: list[str] = Field(default_factory=list)
    status: RunStatus
    step_count: int = Field(ge=0)
    final_output: str | None
    failure_reason: str | None = None
    """Why the run failed, in words: from `fd.set_outcome` or from a person who flagged it."""
    flagged: bool = False
    """A person or the customer's code flagged the run as failed after it passed its check.

    A flagged run has no code check that knows its failure, so the engine judges its replays
    against `failure_reason` with a model.
    """
