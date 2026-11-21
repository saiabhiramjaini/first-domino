"""Async engine, session factory and table creation at startup."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from fd_database.settings import DatabaseSettings
from fd_database.tables import Base


class Database:
    """One engine and session factory per process."""

    def __init__(self, settings: DatabaseSettings | None = None) -> None:
        self._settings = settings or DatabaseSettings()
        self.engine: AsyncEngine = create_async_engine(
            self._settings.url.get_secret_value(),
            pool_size=self._settings.pool_size,
            max_overflow=self._settings.max_overflow,
            pool_timeout=self._settings.pool_timeout_seconds,
            echo=self._settings.echo,
        )
        self._sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_tables(self) -> None:
        """Creates every missing table. There is no migration tool yet."""
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        """Yields a session whose work commits on exit, or rolls back on an error."""
        async with self._sessions.begin() as session:
            yield session

    async def dispose(self) -> None:
        """Closes every pooled connection."""
        await self.engine.dispose()
