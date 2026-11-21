"""Checks, explanations and the engine's diagnosis result."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from fd_shared.enums import CauseCategory, CheckPhase, CheckResult, VerdictKind
from fd_shared.models.steps import Message


class Explanation(BaseModel):
    """A plain-language account of a root cause."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(description="Short name of the mistake.")
    summary: str = Field(description="What went wrong at the step and why it doomed the run.")
    suggested_fix: str = Field(description="What to change in the agent so it stops happening.")
    category: CauseCategory


class CheckView(BaseModel):
    """One check: replay from a save point `samples` times and count the passes.

    A check is identified by `diagnosis_id` and `index`; reporting the same pair again updates it.
    """

    model_config = ConfigDict(frozen=True)

    diagnosis_id: UUID
    index: int = Field(ge=0)
    phase: CheckPhase
    save_point: int = Field(ge=0)
    samples: int = Field(ge=0)
    passes: int = Field(ge=0)
    result: CheckResult


class DiagnosisResult(BaseModel):
    """What the engine concludes about a failed run. The API stores it on the diagnosis."""

    model_config = ConfigDict(frozen=True)

    verdict_kind: VerdictKind
    first_domino_step: int | None = Field(ge=1)
    verify_passes: int | None = Field(ge=0)
    verify_samples: int | None = Field(ge=0)
    fixed_output: Message | None
    explanation: Explanation | None
    check_count: int = Field(ge=0)
    replay_count: int = Field(ge=0)
    cost_usd: float = Field(ge=0)
