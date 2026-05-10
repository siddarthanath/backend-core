"""Logging — structlog with JSON (production) or coloured console (debug) output."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import logging

# Third Party
import structlog
from structlog.types import Processor

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def configure_logging(*, debug: bool = False) -> None:
    """Configure the structlog processor chain. Call once at application startup.

    In debug mode: coloured, human-readable console output.
    In production: JSON lines, one per log event.
    request_id and user_id bound in middleware are automatically merged into
    every log call within that request via merge_contextvars.

    Args:
        debug (bool): True for coloured console output, False for JSON lines.

    """
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),
        structlog.processors.StackInfoRenderer(),
    ]

    processors: list[Processor] = (
        [*shared, structlog.dev.ConsoleRenderer()]
        if debug
        else [*shared, structlog.processors.ExceptionRenderer(), structlog.processors.JSONRenderer()]
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a structlog bound logger for the given module.

    Args:
        name (str): Typically __name__ from the calling module.

    Returns:
        structlog.BoundLogger: A bound logger with the module name pre-bound.

    """
    return structlog.get_logger(name)
