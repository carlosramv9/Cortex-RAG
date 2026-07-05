"""Fixtures for integration tests backed by an in-memory SQLite database."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_database, get_storage_provider

# Import models so their tables register on Base.metadata.
from app.infrastructure.persistence.sqlalchemy import models  # noqa: F401
from app.infrastructure.persistence.sqlalchemy.base import Base
from app.infrastructure.persistence.sqlalchemy.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.persistence.sqlalchemy.repositories.processing_job_repository import (
    SqlAlchemyProcessingJobRepository,
)
from app.infrastructure.persistence.sqlalchemy.session import Database
from app.infrastructure.storage.local_storage import LocalStorageProvider
from app.main import create_app


@pytest_asyncio.fixture()
async def session() -> AsyncIterator[AsyncSession]:
    """A session bound to a fresh in-memory SQLite database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as db_session:
        yield db_session

    await engine.dispose()


@pytest_asyncio.fixture()
async def document_repo(
    session: AsyncSession,
) -> SqlAlchemyDocumentRepository:
    """A document repository over the in-memory database."""
    return SqlAlchemyDocumentRepository(session)


@pytest_asyncio.fixture()
async def job_repo(
    session: AsyncSession,
) -> SqlAlchemyProcessingJobRepository:
    """A processing job repository over the in-memory database."""
    return SqlAlchemyProcessingJobRepository(session)


@pytest.fixture()
def api_client(tmp_path: Path) -> Iterator[TestClient]:
    """A TestClient wired to a file-backed SQLite DB and local storage."""
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    database = Database(db_url)

    async def _create_tables() -> None:
        async with database.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_tables())

    app = create_app()
    app.dependency_overrides[get_database] = lambda: database
    storage = LocalStorageProvider(str(tmp_path / "storage"))
    app.dependency_overrides[get_storage_provider] = lambda: storage

    with TestClient(app) as client:
        yield client
