"""Maps typed errors to stable HTTP error responses."""

from http import HTTPStatus
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from fd_shared.enums import ApiErrorCode
from fd_shared.errors import (
    ConflictError,
    FirstDominoError,
    NotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
)
from fd_shared.logging import get_logger

log = get_logger(__name__)

JSON_INVALID_ERROR_TYPE = "json_invalid"


class ApiError(BaseModel):
    """The body of every error response."""

    code: ApiErrorCode
    title: str = Field(description="Short summary of the error. Do not branch on it.")
    detail: str = Field(description="What went wrong and what to do. Do not branch on it.")


class FieldError(BaseModel):
    """One invalid field in a request."""

    field: str = Field(description="Dotted path of the field, such as `task_input.prompt`.")
    message: str = Field(description="Why the value was rejected.")


class ApiValidationError(ApiError):
    """The body of a `422` response."""

    errors: list[FieldError] = Field(description="Each invalid field.")


class ApiInternalError(ApiError):
    """The body of a `500` response."""

    request_id: str = Field(description="Id to quote when reporting the error.")


_STATUS_BY_CODE: dict[ApiErrorCode, HTTPStatus] = {
    ApiErrorCode.BAD_REQUEST: HTTPStatus.BAD_REQUEST,
    ApiErrorCode.UNAUTHENTICATED: HTTPStatus.UNAUTHORIZED,
    ApiErrorCode.PERMISSION_DENIED: HTTPStatus.FORBIDDEN,
    ApiErrorCode.NOT_FOUND: HTTPStatus.NOT_FOUND,
    ApiErrorCode.CONFLICT: HTTPStatus.CONFLICT,
    ApiErrorCode.VALIDATION_FAILED: HTTPStatus.UNPROCESSABLE_ENTITY,
    ApiErrorCode.INTERNAL_ERROR: HTTPStatus.INTERNAL_SERVER_ERROR,
}

_TITLE_BY_CODE: dict[ApiErrorCode, str] = {
    ApiErrorCode.BAD_REQUEST: "Bad request",
    ApiErrorCode.UNAUTHENTICATED: "Not authenticated",
    ApiErrorCode.PERMISSION_DENIED: "Permission denied",
    ApiErrorCode.NOT_FOUND: "Not found",
    ApiErrorCode.CONFLICT: "Conflict",
    ApiErrorCode.VALIDATION_FAILED: "Validation failed",
    ApiErrorCode.INTERNAL_ERROR: "Internal error",
}

_DETAIL_BY_CODE: dict[ApiErrorCode, str] = {
    ApiErrorCode.BAD_REQUEST: "The request body is not valid JSON.",
    ApiErrorCode.UNAUTHENTICATED: "Send a valid session token or API key as a Bearer token.",
    ApiErrorCode.PERMISSION_DENIED: "This caller may not use the object.",
    ApiErrorCode.NOT_FOUND: "The project has no such object.",
    ApiErrorCode.CONFLICT: "The object's current state does not allow this action.",
    ApiErrorCode.VALIDATION_FAILED: "One or more fields are invalid. See `errors`.",
    ApiErrorCode.INTERNAL_ERROR: "Something went wrong on our side. Quote `request_id`.",
}

_CODE_BY_ERROR: dict[type[FirstDominoError], ApiErrorCode] = {
    NotFoundError: ApiErrorCode.NOT_FOUND,
    PermissionDeniedError: ApiErrorCode.PERMISSION_DENIED,
    ConflictError: ApiErrorCode.CONFLICT,
    UnauthenticatedError: ApiErrorCode.UNAUTHENTICATED,
}

_MODEL_BY_CODE: dict[ApiErrorCode, type[ApiError]] = {
    ApiErrorCode.VALIDATION_FAILED: ApiValidationError,
    ApiErrorCode.INTERNAL_ERROR: ApiInternalError,
}


def error_responses(*codes: ApiErrorCode) -> dict[int | str, dict[str, Any]]:
    """Declares the error responses of an operation for the OpenAPI schema.

    Every operation can fail with `internal_error`, so it is always included.
    """
    declared = {*codes, ApiErrorCode.INTERNAL_ERROR}
    return {
        int(_STATUS_BY_CODE[code]): {
            "model": _MODEL_BY_CODE.get(code, ApiError),
            "description": _TITLE_BY_CODE[code],
        }
        for code in sorted(declared, key=lambda code: _STATUS_BY_CODE[code])
    }


def _error_response(code: ApiErrorCode, body: ApiError) -> JSONResponse:
    return JSONResponse(status_code=_STATUS_BY_CODE[code], content=body.model_dump(mode="json"))


def _simple_error(code: ApiErrorCode, detail: str | None = None) -> JSONResponse:
    body = ApiError(code=code, title=_TITLE_BY_CODE[code], detail=detail or _DETAIL_BY_CODE[code])
    return _error_response(code, body)


async def _handle_domain_error(request: Request, exc: Exception) -> JSONResponse:
    code = next(
        (code for kind, code in _CODE_BY_ERROR.items() if isinstance(exc, kind)),
        None,
    )
    if code is None:
        return await _handle_unexpected_error(request, exc)
    return _simple_error(code)


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return await _handle_unexpected_error(request, exc)
    errors = exc.errors()
    if any(error.get("type") == JSON_INVALID_ERROR_TYPE for error in errors):
        return _simple_error(ApiErrorCode.BAD_REQUEST)
    code = ApiErrorCode.VALIDATION_FAILED
    body = ApiValidationError(
        code=code,
        title=_TITLE_BY_CODE[code],
        detail=_DETAIL_BY_CODE[code],
        errors=[_field_error(error) for error in errors],
    )
    return _error_response(code, body)


def _field_error(error: dict[str, Any]) -> FieldError:
    location = [str(part) for part in error.get("loc", ()) if part not in ("body", "query")]
    return FieldError(field=".".join(location), message=str(error.get("msg", "Invalid value.")))


async def _handle_http_error(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        return await _handle_unexpected_error(request, exc)
    if exc.status_code == HTTPStatus.NOT_FOUND:
        return _simple_error(ApiErrorCode.NOT_FOUND, "No such route.")
    return _simple_error(ApiErrorCode.BAD_REQUEST, "The request does not match this route.")


async def _handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    request_id = str(uuid4())
    log.exception("api.unexpected_error", request_id=request_id, error_type=type(exc).__name__)
    code = ApiErrorCode.INTERNAL_ERROR
    body = ApiInternalError(
        code=code,
        title=_TITLE_BY_CODE[code],
        detail=_DETAIL_BY_CODE[code],
        request_id=request_id,
    )
    return _error_response(code, body)


def install_error_handlers(app: FastAPI) -> None:
    """Makes every error response an `ApiError` body with a stable `code`."""
    app.add_exception_handler(FirstDominoError, _handle_domain_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
