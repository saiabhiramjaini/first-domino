"""Who is calling: a person through the web app, or the SDK with a project API key."""

from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from fd_api import examples
from fd_shared.errors import UnauthenticatedError

API_KEY_PREFIX = "fd_live_"

_bearer = HTTPBearer(auto_error=False, description="A Clerk session token or a project API key.")


class CallerKind(StrEnum):
    """How the caller authenticated."""

    PERSON = "person"
    API_KEY = "api_key"


class Caller(BaseModel):
    """The authenticated caller. Every handler scopes its work to `project_id`."""

    model_config = ConfigDict(frozen=True)

    kind: CallerKind
    project_id: UUID
    actor_id: UUID


async def _bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    if credentials is None or not credentials.credentials:
        raise UnauthenticatedError
    return credentials.credentials


def _example_caller(token: str) -> Caller:
    # EXAMPLE AUTH (contract v1): accepts any token. Replaced by Clerk and API key checks.
    if token.startswith(API_KEY_PREFIX):
        return Caller(
            kind=CallerKind.API_KEY,
            project_id=examples.PROJECT_ID,
            actor_id=examples.API_KEY_ID,
        )
    return Caller(kind=CallerKind.PERSON, project_id=examples.PROJECT_ID, actor_id=examples.USER_ID)


async def any_caller(token: Annotated[str, Depends(_bearer_token)]) -> Caller:
    """Accepts a person or an API key (`P/K` in the contract)."""
    return _example_caller(token)


async def person_caller(token: Annotated[str, Depends(_bearer_token)]) -> Caller:
    """Accepts a person only (`P` in the contract)."""
    return _example_caller(token)


async def api_key_caller(token: Annotated[str, Depends(_bearer_token)]) -> Caller:
    """Accepts a project API key only (`K` in the contract)."""
    return _example_caller(token)


AnyCaller = Annotated[Caller, Depends(any_caller)]
PersonCaller = Annotated[Caller, Depends(person_caller)]
ApiKeyCaller = Annotated[Caller, Depends(api_key_caller)]
