"""Placeholder seed script.

Reserved for seeding local development data once persistence is implemented.
Run with: ``uv run python -m scripts.seed``.
"""

from __future__ import annotations

from app.shared.logging import configure_logging, get_logger


def main() -> None:
    """Entry point."""
    configure_logging()
    logger = get_logger("seed")
    logger.info("seed_noop", detail="Nothing to seed yet.")


if __name__ == "__main__":
    main()
