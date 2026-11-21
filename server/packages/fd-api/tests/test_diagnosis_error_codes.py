"""Every error the engine stops a diagnosis with maps to a contract code."""

from fd_api.services.diagnosis_runner import diagnosis_error_code
from fd_engine.errors import (
    CheckBudgetError,
    CheckInconsistentError,
    LlmCallError,
    LlmNotConfiguredError,
    ReplayNotFaithfulError,
    ReplayUnavailableError,
)
from fd_shared.enums import DiagnosisErrorCode
from fd_shared.errors import NotFoundError


def test_engine_errors_keep_their_code() -> None:
    errors = [
        ReplayUnavailableError(),
        CheckBudgetError(),
        LlmNotConfiguredError(),
        LlmCallError(),
        CheckInconsistentError(),
        ReplayNotFaithfulError(),
    ]

    assert [diagnosis_error_code(error) for error in errors] == [
        DiagnosisErrorCode.REPLAY_UNAVAILABLE,
        DiagnosisErrorCode.CHECK_BUDGET_EXCEEDED,
        DiagnosisErrorCode.LLM_NOT_CONFIGURED,
        DiagnosisErrorCode.LLM_CALL_FAILED,
        DiagnosisErrorCode.CHECK_INCONSISTENT,
        DiagnosisErrorCode.REPLAY_NOT_FAITHFUL,
    ]


def test_other_errors_are_internal() -> None:
    assert diagnosis_error_code(NotFoundError()) is DiagnosisErrorCode.INTERNAL_ERROR
