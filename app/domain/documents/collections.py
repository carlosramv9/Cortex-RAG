"""KnowledgeCollection entity (prepared — no CRUD yet).

A collection groups related knowledge documents within a tenant (e.g. a project,
a workspace, a data source). Reserved for a later phase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class KnowledgeCollection:
    """A named grouping of knowledge documents for a tenant."""

    id: UUID
    tenant_id: str
    name: str
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
