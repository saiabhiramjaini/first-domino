"""Error hierarchy: FirstDominoError, RetryableError, UnretryableError, each with a stable code."""

from typing import ClassVar

from fd_shared.enums import ApiErrorCode


class FirstDominoError(Exception):
    """Root of every error First Domino raises on purpose.

    The message is for logs only. Callers branch on the class or on `code`.
    """

    code: ClassVar[str] = "first_domino_error"


class RetryableError(FirstDominoError):
    """A failure that may succeed if tried again, such as a timeout."""

    code: ClassVar[str] = "retryable_error"


class UnretryableError(FirstDominoError):
    """A failure that will fail the same way if tried again."""

    code: ClassVar[str] = "unretryable_error"


class NotFoundError(UnretryableError):
    """The project does not have the object, including another project's object."""

    code: ClassVar[str] = ApiErrorCode.NOT_FOUND


class PermissionDeniedError(UnretryableError):
    """The project has the object, but this caller may not use it."""

    code: ClassVar[str] = ApiErrorCode.PERMISSION_DENIED


class ConflictError(UnretryableError):
    """The object's state does not allow the action, such as finishing a finished run."""

    code: ClassVar[str] = ApiErrorCode.CONFLICT


class UnauthenticatedError(UnretryableError):
    """The token or API key is missing, expired or revoked."""

    code: ClassVar[str] = ApiErrorCode.UNAUTHENTICATED
