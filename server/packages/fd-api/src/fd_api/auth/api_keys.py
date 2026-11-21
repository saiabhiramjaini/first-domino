"""Project API key verification for the SDK and the worker."""

import hashlib
import hmac
import secrets
from datetime import timedelta
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.repositories import ApiKeysRepository
from fd_database.tables import ApiKey
from fd_database.tables.base import utc_now
from fd_database.tables.projects import API_KEY_PREFIX_LENGTH
from fd_shared.errors import UnauthenticatedError

API_KEY_PREFIX = "fd_live_"
API_KEY_RANDOM_BYTES = 32
LAST_USED_RESOLUTION = timedelta(minutes=1)


class NewApiKey(BaseModel):
    """A freshly minted key. The secret leaves the API once, in the create response."""

    model_config = ConfigDict(frozen=True)

    secret: str
    prefix: str
    key_hash: str


def hash_api_key(secret: str) -> str:
    """SHA-256 of the key, as stored."""
    return hashlib.sha256(secret.encode()).hexdigest()


def mint_api_key() -> NewApiKey:
    """Creates a random `fd_live_` key and its stored hash."""
    secret = API_KEY_PREFIX + secrets.token_urlsafe(API_KEY_RANDOM_BYTES)
    return NewApiKey(
        secret=secret, prefix=secret[:API_KEY_PREFIX_LENGTH], key_hash=hash_api_key(secret)
    )


class CreatedApiKey(BaseModel):
    """A stored key and its secret, which leaves the API only once."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    api_key: ApiKey
    secret: str


async def create_api_key(
    session: AsyncSession, *, project_id: UUID, name: str, created_by_id: UUID
) -> CreatedApiKey:
    """Mints a key and stores its hash."""
    new_key = mint_api_key()
    api_key = await ApiKeysRepository(session).create(
        project_id=project_id,
        name=name,
        prefix=new_key.prefix,
        key_hash=new_key.key_hash,
        created_by_id=created_by_id,
    )
    return CreatedApiKey(api_key=api_key, secret=new_key.secret)


async def verify_api_key(session: AsyncSession, secret: str) -> ApiKey:
    """Finds the key by hash and records its use, to the minute.

    Raises:
        UnauthenticatedError: No such key, or it is revoked.
    """
    key_hash = hash_api_key(secret)
    api_keys = ApiKeysRepository(session)
    api_key = await api_keys.find_by_hash(key_hash=key_hash)
    if api_key is None or not hmac.compare_digest(api_key.key_hash, key_hash):
        raise UnauthenticatedError
    if api_key.revoked_at is not None:
        raise UnauthenticatedError
    now = utc_now()
    if api_key.last_used_at is None or now - api_key.last_used_at > LAST_USED_RESOLUTION:
        await api_keys.touch(project_id=api_key.project_id, api_key_id=api_key.id, used_at=now)
    return api_key
