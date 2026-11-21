"""API key contract models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from fd_api.pagination import PageRequest, PageResponse
from fd_database import tables


class ApiKey(BaseModel):
    """A project API key, used by the SDK and the replay worker. The secret is never returned."""

    id: UUID
    name: str = Field(max_length=128, description="Name given at creation, such as `staging`.")
    prefix: str = Field(description="First 12 characters of the key, for telling keys apart.")
    created_at: datetime = Field(description="Time of creation, in UTC RFC 3339 format.")
    created_by_id: UUID = Field(description="Id of the person who created the key.")
    last_used_at: datetime | None = Field(
        description="Time of the last request with this key, in UTC RFC 3339 format."
    )
    revoked_at: datetime | None = Field(
        description="Time of revocation, in UTC RFC 3339 format. Null while the key works."
    )
    revoked_by_id: UUID | None = Field(description="Id of the person who revoked the key.")

    @classmethod
    def from_row(cls, row: tables.ApiKey) -> "ApiKey":
        """Maps a stored key to the contract. The hash never leaves the database."""
        return cls(
            id=row.id,
            name=row.name,
            prefix=row.prefix,
            created_at=row.created_at,
            created_by_id=row.created_by_id,
            last_used_at=row.last_used_at,
            revoked_at=row.revoked_at,
            revoked_by_id=row.revoked_by_id,
        )


class CreateApiKeyRequest(BaseModel):
    """Creates a project API key."""

    name: str = Field(min_length=1, max_length=128, description="Name to tell the key apart.")


class CreateApiKeyResponse(BaseModel):
    """The new key and its secret."""

    api_key: ApiKey
    secret: str = Field(description="The full key. Shown only here; store it now.")


class ListApiKeysRequest(PageRequest):
    """Lists the project's API keys, newest first, revoked ones included."""


class ListApiKeysResponse(PageResponse[ApiKey]):
    """A page of API keys."""


class RevokeApiKeyRequest(BaseModel):
    """Revokes an API key. Revoking a revoked key changes nothing."""

    api_key_id: UUID


class RevokeApiKeyResponse(BaseModel):
    """The revoked key."""

    api_key: ApiKey
