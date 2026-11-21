"""Data the engine reads through its ports and the result it returns.

These mirror `docs/CONTRACT.md`. They live here only until `fd-shared` ships the same models
and enums; then the engine imports those and this module keeps only engine-only types.
"""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class MessageRole(StrEnum):
    """Who wrote a message in the agent's conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ReplayOutcome(StrEnum):
    """What the customer's success check said about one replay."""

    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"


class DiagnosisStatus(StrEnum):
    """Stage of a diagnosis, shown live in the web app."""

    QUEUED = "queued"
    BISECTING = "bisecting"
    VERIFYING = "verifying"
    EXPLAINING = "explaining"
    DONE = "done"
    FAILED = "failed"


class VerdictKind(StrEnum):
    """What a finished diagnosis concluded."""

    STEP_VERIFIED = "step_verified"
    STEP_UNVERIFIED = "step_unverified"
    MULTIPLE_CAUSES = "multiple_causes"
    TASK_OR_TOOL_ISSUE = "task_or_tool_issue"


class CheckPhase(StrEnum):
    """Which part of the diagnosis a check belongs to."""

    PRECHECK = "precheck"
    BISECT = "bisect"
    VERIFY = "verify"
    FALLBACK = "fallback"


class CheckResult(StrEnum):
    """Verdict of one check."""

    PENDING = "pending"
    CAN_SUCCEED = "can_succeed"
    DOOMED = "doomed"


class CauseCategory(StrEnum):
    """Kind of root cause, used to group causes."""

    WRONG_DATE = "wrong_date"
    WRONG_ENTITY = "wrong_entity"
    WRONG_FILTER = "wrong_filter"
    BAD_TOOL_ARGS = "bad_tool_args"
    HALLUCINATION = "hallucination"
    TOOL_ISSUE = "tool_issue"
    OTHER = "other"


class ToolCall(_Frozen):
    """One tool call the model asked for."""

    id: str
    name: str
    arguments: str


class Message(_Frozen):
    """One message in the agent's conversation."""

    role: MessageRole
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None


class TaskInput(_Frozen):
    """The task the agent was given."""

    prompt: str
    metadata: dict[str, str] = Field(default_factory=dict)


class RunView(_Frozen):
    """The failed run the engine diagnoses."""

    id: UUID
    agent_name: str
    task_input: TaskInput
    step_count: int = Field(ge=0)


class StepView(_Frozen):
    """One recorded step: the assistant turn and the tool results that followed it."""

    index: int = Field(ge=1)
    model: str
    output: Message
    tool_results: list[Message] = Field(default_factory=list)


class Check(_Frozen):
    """One bisect, verify or fallback check.

    A check is identified by (`diagnosis_id`, `index`): the sink receives the same check twice,
    first as `pending`, then with its passes and result.
    """

    diagnosis_id: UUID
    index: int = Field(ge=0)
    phase: CheckPhase
    save_point: int = Field(ge=0)
    samples: int = Field(ge=1)
    passes: int = Field(ge=0)
    result: CheckResult


class Explanation(_Frozen):
    """Plain-language description of a root cause."""

    title: str
    summary: str
    suggested_fix: str
    category: CauseCategory


class DiagnosisResult(_Frozen):
    """What one diagnosis concluded, for the API to store."""

    verdict_kind: VerdictKind
    first_domino_step: int | None
    verify_passes: int | None
    verify_samples: int | None
    fixed_output: Message | None
    explanation: Explanation | None
    check_count: int = Field(ge=0)
    replay_count: int = Field(ge=0)
    cost_usd: float = Field(ge=0)
