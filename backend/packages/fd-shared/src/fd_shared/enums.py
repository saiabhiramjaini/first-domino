"""Status, kind and category enums used across packages."""

from enum import StrEnum


class RunStatus(StrEnum):
    """Where a run stands. `running` until the customer finishes it."""

    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"


class RunOutcome(StrEnum):
    """How a finished run ended: the customer's success check passed or failed, or it crashed."""

    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"


class RunSource(StrEnum):
    """Whether a run was recorded from real traffic or replayed for a diagnosis."""

    RECORDED = "recorded"
    REPLAY = "replay"


class MessageRole(StrEnum):
    """The author of a chat message, as in the OpenAI chat format."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class DiagnosisStatus(StrEnum):
    """The stage a diagnosis is in. `done` and `failed` are final."""

    QUEUED = "queued"
    BISECTING = "bisecting"
    VERIFYING = "verifying"
    EXPLAINING = "explaining"
    DONE = "done"
    FAILED = "failed"


class VerdictKind(StrEnum):
    """What a finished diagnosis concluded.

    `step_verified`: one step was found and fixing it flipped the outcome.
    `step_unverified`: one step was found but fixing it did not flip the outcome often enough.
    `multiple_causes`: no single step fix flipped the outcome.
    `task_or_tool_issue`: even a fresh run fails, so no agent step is to blame.
    """

    STEP_VERIFIED = "step_verified"
    STEP_UNVERIFIED = "step_unverified"
    MULTIPLE_CAUSES = "multiple_causes"
    TASK_OR_TOOL_ISSUE = "task_or_tool_issue"


class CheckPhase(StrEnum):
    """The part of a diagnosis a check belongs to."""

    PRECHECK = "precheck"
    BISECT = "bisect"
    VERIFY = "verify"
    FALLBACK = "fallback"


class CheckResult(StrEnum):
    """A check's finding: replays from its save point can still succeed, or all fail."""

    PENDING = "pending"
    CAN_SUCCEED = "can_succeed"
    DOOMED = "doomed"


class ReplayJobStatus(StrEnum):
    """Where a replay job stands in the queue. `succeeded`, `failed` and `expired` are final."""

    QUEUED = "queued"
    LEASED = "leased"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"


class ReplayOutcome(StrEnum):
    """The result of one replay, from the customer's success check."""

    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"


class CauseCategory(StrEnum):
    """The kind of mistake a root cause is."""

    WRONG_DATE = "wrong_date"
    WRONG_ENTITY = "wrong_entity"
    WRONG_FILTER = "wrong_filter"
    BAD_TOOL_ARGS = "bad_tool_args"
    HALLUCINATION = "hallucination"
    TOOL_ISSUE = "tool_issue"
    OTHER = "other"


class BenchmarkMethod(StrEnum):
    """A way of finding the first domino step that the benchmark scores."""

    FIRST_DOMINO = "first_domino"
    READ_TRACE_JUDGE = "read_trace_judge"


class ApiErrorCode(StrEnum):
    """The stable `code` of every API error body. Branch on this, never on the text."""

    BAD_REQUEST = "bad_request"
    UNAUTHENTICATED = "unauthenticated"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    VALIDATION_FAILED = "validation_failed"
    INTERNAL_ERROR = "internal_error"
