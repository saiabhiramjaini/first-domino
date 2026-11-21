"""Structured logging setup and get_logger."""

import logging

import structlog


def configure_logging(level: str = "INFO", *, json_output: bool = False) -> None:
    """Sets up structlog once per process.

    Args:
        level: The lowest level to emit, such as `INFO` or `DEBUG`.
        json_output: Emit one JSON object per line instead of the console format.
    """
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    """Returns a logger that takes an event name and structured fields.

    Args:
        name: The module name, usually `__name__`.
    """
    return structlog.get_logger(name)
