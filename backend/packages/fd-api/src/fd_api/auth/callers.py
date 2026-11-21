"""Who is calling: a person through the web app, or the SDK with a project API key."""

from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from fd_api.auth.api_keys import API_KEY_PREFIX, verify_api_key
from fd_api.auth.users import sign_in, verify_web_token
from fd_api.database import DbSession
from fd_api.settings import ApiSettings
from fd_shared.errors import UnauthenticatedError

_bearer = HTTPBearer(auto_error=False, description="A web session token or a project API key.")


class CallerKind(StrEnum):
    """How the caller authenticated."""

    PERSON = "person"
    API_KEY = "api_key"


class Caller(BaseModel):
    """The authenticated caller. Every handler scopes its work to `project_id`.

    `actor_id` is the person's user id or the API key's id, for `*_by_id` columns.
    """

    model_config = ConfigDict(frozen=True)

    kind: CallerKind
    project_id: UUID
    actor_id: UUID


def get_settings(request: Request) -> ApiSettings:
    """The settings the app was built with."""
    return request.app.state.settings


async def _bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    if credentials is None or not credentials.credentials:
        raise UnauthenticatedError
    return credentials.credentials


async def _person(token: str, session: DbSession, settings: ApiSettings) -> Caller:
    claims = verify_web_token(token, settings)
    person = await sign_in(session, claims)
    return Caller(kind=CallerKind.PERSON, project_id=person.project_id, actor_id=person.user_id)


async def _api_key(token: str, session: DbSession) -> Caller:
    api_key = await verify_api_key(session, token)
    return Caller(kind=CallerKind.API_KEY, project_id=api_key.project_id, actor_id=api_key.id)


async def any_caller(
    token: Annotated[str, Depends(_bearer_token)],
    session: DbSession,
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> Caller:
    """Accepts a person or an API key (`P/K` in the contract)."""
    if token.startswith(API_KEY_PREFIX):
        return await _api_key(token, session)
    return await _person(token, session, settings)


async def person_caller(
    token: Annotated[str, Depends(_bearer_token)],
    session: DbSession,
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> Caller:
    """Accepts a person only (`P` in the contract)."""
    return await _person(token, session, settings)


async def api_key_caller(
    token: Annotated[str, Depends(_bearer_token)], session: DbSession
) -> Caller:
    """Accepts a project API key only (`K` in the contract)."""
    return await _api_key(token, session)


AnyCaller = Annotated[Caller, Depends(any_caller)]
PersonCaller = Annotated[Caller, Depends(person_caller)]
ApiKeyCaller = Annotated[Caller, Depends(api_key_caller)]
