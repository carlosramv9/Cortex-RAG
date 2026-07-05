"""Tests for LocalStorageProvider."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.shared.exceptions import EntityNotFoundError
from app.infrastructure.storage.local_storage import LocalStorageProvider


async def test_save_writes_file_and_returns_path(tmp_path: Path) -> None:
    storage = LocalStorageProvider(str(tmp_path))
    key = "documents/tenant/2026/07/doc.pdf"

    location = await storage.save(key, b"%PDF-1.7 data")

    assert Path(location).is_file()
    assert Path(location).read_bytes() == b"%PDF-1.7 data"


async def test_save_load_roundtrip(tmp_path: Path) -> None:
    storage = LocalStorageProvider(str(tmp_path))
    await storage.save("a/b/c.bin", b"payload")

    assert await storage.load("a/b/c.bin") == b"payload"


async def test_load_missing_raises(tmp_path: Path) -> None:
    storage = LocalStorageProvider(str(tmp_path))

    with pytest.raises(EntityNotFoundError):
        await storage.load("missing.bin")


async def test_delete_is_idempotent(tmp_path: Path) -> None:
    storage = LocalStorageProvider(str(tmp_path))
    await storage.save("x.bin", b"data")

    await storage.delete("x.bin")
    await storage.delete("x.bin")  # no error second time

    with pytest.raises(EntityNotFoundError):
        await storage.load("x.bin")


async def test_path_traversal_is_blocked(tmp_path: Path) -> None:
    storage = LocalStorageProvider(str(tmp_path))

    with pytest.raises(ValueError, match="Invalid storage key"):
        await storage.save("../escape.bin", b"nope")
