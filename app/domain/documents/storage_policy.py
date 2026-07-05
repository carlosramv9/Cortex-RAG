"""Storage path policy (pure domain logic, no I/O).

Centralizes how storage keys are derived so the layout is consistent and
reconstructable:

    documents/{tenant_id}/{year}/{month}/{document_id}/{version_id}.{ext}
    pages/{document_id}/page_{page:03d}.{image_format}

Each version is a distinct physical file, so the key is scoped by version id
under a per-document folder. The physical write is done by a ``StorageProvider``
adapter; this module only computes keys.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID


def build_document_version_key(
    *,
    tenant_id: str,
    document_id: UUID,
    version_id: UUID,
    extension: str,
    uploaded_at: datetime,
) -> str:
    """Return the storage key for a document version's original bytes."""
    ext = extension.lstrip(".").lower()
    return (
        f"documents/{tenant_id}/{uploaded_at.year:04d}/"
        f"{uploaded_at.month:02d}/{document_id}/{version_id}.{ext}"
    )


def build_page_image_key(
    *,
    document_id: UUID,
    page_number: int,
    image_format: str,
) -> str:
    """Return the storage key for a rendered page image (reserved)."""
    fmt = image_format.lstrip(".").lower()
    return f"pages/{document_id}/page_{page_number:03d}.{fmt}"
