"""How one replay ended, and where it stopped matching the recording."""

from pydantic import BaseModel, ConfigDict, Field

from fd_shared.enums import ReplayOutcome


class ReplayDrift(BaseModel):
    """The first kept step a replay could not reproduce.

    A replay keeps steps 1 to `from_step` as recorded. When a tool gives a different result
    there than it did in the recording, the replay is no longer the run being diagnosed, so
    its outcome says nothing about the save point.
    """

    model_config = ConfigDict(frozen=True)

    step: int = Field(ge=1, description="The kept step whose tool results came back different.")
    tool_name: str | None = Field(
        default=None,
        max_length=128,
        description="The tool whose result differed or was not sent back. Null when unknown.",
    )


class ReplayResult(BaseModel):
    """One replay's outcome and, when it drifted from the recording, where."""

    model_config = ConfigDict(frozen=True)

    outcome: ReplayOutcome
    drift: ReplayDrift | None = None

    @property
    def is_evidence(self) -> bool:
        """Whether the outcome can decide a check: the replay ran and matched the recording."""
        return self.outcome is not ReplayOutcome.ERRORED and self.drift is None
