"""SQLAlchemy declarative base.

ORM models (added later) will inherit from ``Base``. Alembic autogeneration
targets ``Base.metadata``.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
