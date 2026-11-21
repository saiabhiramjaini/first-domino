"""Errors the engine raises to stop a diagnosis.

They derive from a local base until `fd_shared.errors` ships `FirstDominoError`,
`RetryableError` and `UnretryableError`; then these subclass those instead.
"""

from typing import ClassVar


class EngineError(Exception):
    """Base for engine errors. `code` is stable; callers branch on it, never on the message."""

    code: ClassVar[str] = "engine_error"
    retryable: ClassVar[bool] = False


class ReplayUnavailableError(EngineError):
    """Every replay in a check errored or timed out, so the check has no verdict."""

    code: ClassVar[str] = "replay_unavailable"
    retryable: ClassVar[bool] = True


class CheckBudgetError(EngineError):
    """The diagnosis needed more checks than `max_checks` allows."""

    code: ClassVar[str] = "check_budget_exceeded"
