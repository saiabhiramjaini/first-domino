"""API keys routes: create, list and revoke."""

from fastapi import APIRouter

from fd_api.auth.api_keys import create_api_key
from fd_api.auth.callers import PersonCaller
from fd_api.database import DbSession
from fd_api.errors import error_responses
from fd_api.models.api_keys import (
    ApiKey,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    ListApiKeysRequest,
    ListApiKeysResponse,
    RevokeApiKeyRequest,
    RevokeApiKeyResponse,
)
from fd_api.pagination import decode_cursor, paginate
from fd_database.pages import TimeKey
from fd_database.repositories import ApiKeysRepository
from fd_database.tables.base import utc_now
from fd_shared.enums import ApiErrorCode
from fd_shared.errors import NotFoundError
from fd_shared.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["api-keys"])


@router.post(
    "/api-keys.create",
    operation_id="createApiKey",
    summary="Create an API key",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def create_api_key_route(
    body: CreateApiKeyRequest, caller: PersonCaller, session: DbSession
) -> CreateApiKeyResponse:
    """Creates a project API key. The full key is in `secret` and is never shown again."""
    created = await create_api_key(
        session, project_id=caller.project_id, name=body.name, created_by_id=caller.actor_id
    )
    log.info(
        "api_keys.created", project_id=str(caller.project_id), api_key_id=str(created.api_key.id)
    )
    return CreateApiKeyResponse(api_key=ApiKey.from_row(created.api_key), secret=created.secret)


@router.post(
    "/api-keys.list",
    operation_id="listApiKeys",
    summary="List API keys",
    responses=error_responses(
        ApiErrorCode.BAD_REQUEST, ApiErrorCode.UNAUTHENTICATED, ApiErrorCode.VALIDATION_FAILED
    ),
)
async def list_api_keys(
    body: ListApiKeysRequest, caller: PersonCaller, session: DbSession
) -> ListApiKeysResponse:
    """Lists the project's API keys, newest first, revoked ones included."""
    rows = await ApiKeysRepository(session).list_page(
        project_id=caller.project_id,
        limit=body.limit + 1,
        after=decode_cursor(body.cursor, TimeKey),
    )
    page, next_cursor = paginate(
        rows, body.limit, lambda row: TimeKey(at=row.created_at, id=row.id)
    )
    return ListApiKeysResponse(
        items=[ApiKey.from_row(row) for row in page], next_cursor=next_cursor
    )


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
async def revoke_api_key(
    body: RevokeApiKeyRequest, caller: PersonCaller, session: DbSession
) -> RevokeApiKeyResponse:
    """Revokes an API key at once. Revoking a revoked key returns it unchanged."""
    api_keys = ApiKeysRepository(session)
    api_key = await api_keys.get(project_id=caller.project_id, api_key_id=body.api_key_id)
    if api_key is None:
        raise NotFoundError
    api_key = await api_keys.revoke(
        api_key=api_key, revoked_at=utc_now(), revoked_by_id=caller.actor_id
    )
    return RevokeApiKeyResponse(api_key=ApiKey.from_row(api_key))
