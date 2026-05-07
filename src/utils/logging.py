"""Logging utilities — stdlib for now, structlog in Round 3 (see backend-specs/08-utils.md)."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import logging

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def setup_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """Create and configure a logger with a given name.

    Args:
        name (str): Name of the logger (typically __name__ or class name).
        level (int): Logging level (e.g., logging.DEBUG, logging.INFO).

    Returns:
        logging.Logger: Configured logger instance.

    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger