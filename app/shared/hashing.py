"""Reusable hashing helpers."""

from __future__ import annotations

import hashlib


def sha256_hex(content: bytes) -> str:
    """Return the hex-encoded SHA-256 digest of ``content``.

    Used for integrity, duplicate detection and future versioning.
    """
    return hashlib.sha256(content).hexdigest()
