"""Web session token verification for people using the web app."""

from uuid import UUID

import jwt
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from fd_api.settings import ApiSettings
from fd_database.repositories import ProjectsRepository
from fd_shared.errors import UnauthenticatedError
from fd_shared.logging import get_logger

log = get_logger(__name__)

WEB_TOKEN_ALGORITHM = "HS256"
WEB_TOKEN_ISSUER = "first-domino-web"
WEB_TOKEN_AUDIENCE = "first-domino-api"
REQUIRED_CLAIMS = ["sub", "iss", "aud", "iat", "exp"]


class WebTokenClaims(BaseModel):
    """The claims the API reads from a verified web session token."""

    model_config = ConfigDict(frozen=True)

    sub: str
    email: str
    name: str


class Person(BaseModel):
    """A signed-in person and the project they own."""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    project_id: UUID


def verify_web_token(token: str, settings: ApiSettings) -> WebTokenClaims:
    """Checks the token's signature, issuer, audience and expiry, then reads its claims.

    Raises:
        UnauthenticatedError: The token is invalid, expired, or no secret is configured.
    """
    secret = settings.web_jwt_secret.get_secret_value()
    if not secret:
        log.error("auth.web_jwt_secret_missing")
        raise UnauthenticatedError
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[WEB_TOKEN_ALGORITHM],
            issuer=WEB_TOKEN_ISSUER,
            audience=WEB_TOKEN_AUDIENCE,
            options={"require": REQUIRED_CLAIMS},
        )
        return WebTokenClaims.model_validate(payload)
    except (jwt.InvalidTokenError, ValidationError) as error:
        log.info("auth.web_token_rejected", error_type=type(error).__name__)
        raise UnauthenticatedError from error


async def sign_in(session: AsyncSession, claims: WebTokenClaims) -> Person:
    """Finds or creates the person by `sub`, and their project on first sign-in."""
    projects = ProjectsRepository(session)
    user = await projects.upsert_user(google_sub=claims.sub, email=claims.email, name=claims.name)
    project = await projects.get_owned(owner_id=user.id)
    if project is None:
        project = await projects.create(owner_id=user.id, name=f"{claims.name}'s project")
        log.info("auth.project_created", project_id=str(project.id))
    return Person(user_id=user.id, project_id=project.id)
