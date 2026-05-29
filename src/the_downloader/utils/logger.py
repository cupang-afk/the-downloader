"""Logging configuration for the downloader package."""

import logging
from logging import Logger

LOGGER = logging.getLogger("the_downloader")


def get_logger(name: str | None = None) -> Logger:
    """Get a child logger.

    Args:
        name: The child logger name.

    Returns:
        A Logger instance named ``<parent>.<name>``.
    """
    return LOGGER.getChild(name) if name else LOGGER
