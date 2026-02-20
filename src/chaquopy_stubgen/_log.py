"""Logging configuration helpers."""

from __future__ import annotations

import logging


def configure_logging(level: int | str = logging.INFO) -> None:
    """Configure logging with a consistent format for all processes."""
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
