"""Errors the engine raises to stop a diagnosis. Store `code` as the diagnosis `error_code`."""

from typing import ClassVar

from fd_shared.errors import RetryableError, UnretryableError


class ReplayUnavailableError(RetryableError):
    """Every replay in a check errored or timed out, so the check has no verdict."""

    code: ClassVar[str] = "replay_unavailable"


class ReplayNotFaithfulError(UnretryableError):
    """No replay in a check reproduced the steps it kept, and at least one drifted from them."""

    code: ClassVar[str] = "replay_not_faithful"


class CheckInconsistentError(UnretryableError):
    """The success check passed a replay that kept every recorded step of the failed run."""

    code: ClassVar[str] = "check_inconsistent"


class CheckBudgetError(UnretryableError):
    """The diagnosis needed more checks than `max_checks` allows."""

    code: ClassVar[str] = "check_budget_exceeded"


class LlmNotConfiguredError(UnretryableError):
    """The engine needs a model call but `OPENAI_API_KEY` is not set."""

    code: ClassVar[str] = "llm_not_configured"


class LlmCallError(RetryableError):
    """One model call failed before it returned any text."""

    code: ClassVar[str] = "llm_call_failed"
