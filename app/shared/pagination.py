"""Generic pagination helpers reusable by any layer."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, Field


class Page[T](BaseModel):
    """A page of results."""

    items: Sequence[T]
    total: int = Field(ge=0)
    limit: int = Field(gt=0)
    offset: int = Field(ge=0)
