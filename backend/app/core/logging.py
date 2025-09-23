"""
Logging configuration for the application.
"""

import logging
import sys

import structlog
from structlog.typing import FilteringBoundLogger

from app.core.config import settings


def setup_logging() -> None:
    """Configure structured logging."""

    # Configure structlog
    structlog.configure(
        processors=[
            # Add the name of the logger to event dict
            structlog.stdlib.add_logger_name,
            # Add log level to event dict
            structlog.stdlib.add_log_level,
            # Perform %-style formatting
            structlog.stdlib.PositionalArgumentsFormatter(),
            # Add a timestamp in ISO 8601 format
            structlog.processors.TimeStamper(fmt="iso"),
            # If the "stack_info" key in the event dict is true, remove it and
            # render the current stack trace in the "stack" key
            structlog.processors.StackInfoRenderer(),
            # If some value is in bytes, decode it to a unicode str
            structlog.processors.UnicodeDecoder(),
            # Render the final event dict as JSON
            (
                structlog.processors.JSONRenderer()
                if settings.ENVIRONMENT == "production"
                else structlog.dev.ConsoleRenderer(colors=True)
            ),
        ],
        # `wrapper_class` is the bound logger that you get back from
        # get_logger(). This one imitates the API of `logging.Logger`.
        wrapper_class=structlog.stdlib.BoundLogger,
        # `logger_factory` is used to create wrapped loggers that are used for
        # OUTPUT. This one returns a `logging.Logger`. The final value (a JSON
        # string) from the final processor (`JSONRenderer`) will be passed to
        # the method of the same name as that you've called on the bound logger.
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Effectively freeze configuration after creating the first bound
        # logger.
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG,
    )

    # Set third-party library log levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.ENVIRONMENT == "development" else logging.WARNING
    )


def get_logger(name: str) -> FilteringBoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)
