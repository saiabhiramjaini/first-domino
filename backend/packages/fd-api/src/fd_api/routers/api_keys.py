"""API keys routes: create, list and revoke."""

from fastapi import APIRouter

from fd_api import examples
from fd_api.auth.callers import PersonCaller
from fd_api.errors import error_responses
from fd_api.models.api_keys import (
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    ListApiKeysRequest,
    ListApiKeysResponse,
    RevokeApiKeyRequest,
    RevokeApiKeyResponse,
)
from fd_shared.enums import ApiErrorCode

router = APIRouter(prefix="/v1", tags=["api-keys"])


@router.post(
    "/api-keys.create",
    operation_id="createApiKey",
    summary="Create an API key",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def create_api_key(body: CreateApiKeyRequest, caller: PersonCaller) -> CreateApiKeyResponse:
    """Creates a project API key. The full key is in `secret` and is never shown again."""
    api_key = examples.API_KEY.model_copy(update={"name": body.name})
    return CreateApiKeyResponse(api_key=api_key, secret=examples.API_KEY_SECRET)


@router.post(
    "/api-keys.list",
    operation_id="listApiKeys",
    summary="List API keys",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def list_api_keys(body: ListApiKeysRequest, caller: PersonCaller) -> ListApiKeysResponse:
    """Lists the project's API keys, newest first, revoked ones included."""
    return ListApiKeysResponse(items=[examples.API_KEY], next_cursor=None)


@router.post(
    "/api-keys.revoke",
    operation_id="revokeApiKey",
    summary="Revoke an API key",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST,
        ApiErrorCode.UNAUTHENTICATED,
        ApiErrorCode.NOT_FOUND,
        ApiErrorCode.VALIDATION_FAILED,
    ),
)
async def revoke_api_key(body: RevokeApiKeyRequest, caller: PersonCaller) -> RevokeApiKeyResponse:
    """Revokes an API key at once. Revoking a revoked key returns it unchanged."""
    api_key = examples.API_KEY.model_copy(
        update={"revoked_at": examples.T0, "revoked_by_id": examples.USER_ID}
    )
    return RevokeApiKeyResponse(api_key=api_key)
