"""Structured logging configuration built on structlog.

Call :func:`configure_logging` once at startup. Obtain loggers anywhere with
:func:`get_logger`. Never use ``print``.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

_Processor = Any  # structlog processor type alias (kept loose on purpose)


def configure_logging(*, level: str = "INFO", json_logs: bool = False) -> None:
    """Configure structlog and the stdlib logging bridge.

    Args:
        level: Minimum log level name (e.g. ``"INFO"``).
        json_logs: Emit JSON when True; human-readable console output otherwise.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list[_Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    renderer: _Processor = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (uvicorn, sqlalchemy, ...) through the same handler.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
