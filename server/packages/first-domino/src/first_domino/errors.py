"""SDK errors. Recording never raises them into the agent; the worker raises them at start-up."""

from first_domino._generated.models import ApiErrorCode


class FirstDominoError(Exception):
    """Root of every error the SDK raises on purpose."""


class ConfigurationError(FirstDominoError):
    """The SDK is not configured to do what was asked, such as a worker without an API key."""


class ApiRequestError(FirstDominoError):
    """A call to the First Domino API failed.

    Attributes:
        status_code: The HTTP status, or None when the request never got an answer.
        code: The API's stable error code, when the body carried one.
    """

    def __init__(self, message: str, *, status_code: int | None, code: ApiErrorCode | None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code

    @property
    def retryable(self) -> bool:
        """True for network failures and server errors, which may pass on a later try."""
        return self.status_code is None or self.status_code >= 500
