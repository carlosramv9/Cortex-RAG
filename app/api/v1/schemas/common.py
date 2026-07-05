"""Shared HTTP schemas."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error envelope returned by the API."""

    error: str
    detail: str | None = None


class HealthResponse(BaseModel):
    """Health check payload."""

    status: str
    service: str
    version: str
