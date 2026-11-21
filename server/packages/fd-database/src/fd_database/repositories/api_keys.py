"""API keys repository: create, look up by hash, revoke."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from fd_database.pages import TimeKey
from fd_database.tables import ApiKey


class ApiKeysRepository:
    """Project API keys. Only SHA-256 hashes are stored."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, project_id: UUID, name: str, prefix: str, key_hash: str, created_by_id: UUID
    ) -> ApiKey:
        """Stores a new key by its hash."""
        api_key = ApiKey(
            project_id=project_id,
            name=name,
            prefix=prefix,
            key_hash=key_hash,
            created_by_id=created_by_id,
        )
        self._session.add(api_key)
        await self._session.flush()
        return api_key

    async def find_by_hash(self, *, key_hash: str) -> ApiKey | None:
        """The key with this hash, revoked or not. Runs before the project is known."""
        return await self._session.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))

    async def touch(self, *, project_id: UUID, api_key_id: UUID, used_at: datetime) -> None:
        """Records that the key was just used."""
        await self._session.execute(
            update(ApiKey)
            .where(ApiKey.project_id == project_id, ApiKey.id == api_key_id)
            .values(last_used_at=used_at)
        )

    async def get(self, *, project_id: UUID, api_key_id: UUID) -> ApiKey | None:
        """One key of the project."""
        return await self._session.scalar(
            select(ApiKey).where(ApiKey.project_id == project_id, ApiKey.id == api_key_id)
        )

    async def list_page(
        self, *, project_id: UUID, limit: int, after: TimeKey | None
    ) -> list[ApiKey]:
        """Keys of the project, newest first."""
        statement = select(ApiKey).where(ApiKey.project_id == project_id)
        if after is not None:
            statement = statement.where(tuple_(ApiKey.created_at, ApiKey.id) < (after.at, after.id))
        statement = statement.order_by(ApiKey.created_at.desc(), ApiKey.id.desc()).limit(limit)
        return list(await self._session.scalars(statement))

    async def revoke(self, *, api_key: ApiKey, revoked_at: datetime, revoked_by_id: UUID) -> ApiKey:
        """Revokes a key. A revoked key keeps its first revocation."""
        if api_key.revoked_at is None:
            api_key.revoked_at = revoked_at
            api_key.revoked_by_id = revoked_by_id
            await self._session.flush()
        return api_key
