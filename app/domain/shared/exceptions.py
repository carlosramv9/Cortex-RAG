"""Base domain exceptions.

Domain code raises these framework-agnostic errors. The API layer maps them to
HTTP responses (see ``app.api.errors``). Domain never knows about HTTP.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-level errors."""

    default_message: str = "A domain error occurred."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message


class EntityNotFoundError(DomainError):
    """Raised when a requested entity does not exist."""

    default_message = "The requested entity was not found."


class ValidationError(DomainError):
    """Raised when a domain invariant is violated."""

    default_message = "A domain validation rule was violated."


class ConflictError(DomainError):
    """Raised when an operation conflicts with current state."""

    default_message = "The operation conflicts with the current state."
