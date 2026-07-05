"""Async SQLAlchemy engine and session management.

``Database`` owns the async engine and session factory and exposes a session
context manager. It is created once at startup and disposed at shutdown.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import Settings


class Database:
    """Owns the async engine and session factory."""

    def __init__(self, dsn: str, *, echo: bool = False) -> None:
        self._engine: AsyncEngine = create_async_engine(
            dsn,
            echo=echo,
            pool_pre_ping=True,
        )
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield a session, committing on success and rolling back on error."""
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def dispose(self) -> None:
        """Dispose of the engine's connection pool."""
        await self._engine.dispose()


def get_database(settings: Settings) -> Database:
    """Factory building a ``Database`` from settings."""
    return Database(settings.db.async_dsn, echo=settings.db.echo)
