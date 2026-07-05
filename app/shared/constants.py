"""Shared constants and enums used across layers."""

from __future__ import annotations

from enum import StrEnum

API_V1_PREFIX = "/api/v1"


class DocumentStatus(StrEnum):
    """Lifecycle status of a document."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
