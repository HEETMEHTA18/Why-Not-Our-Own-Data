from __future__ import annotations

import structlog
from structlog.dev import ConsoleRenderer
from structlog.processors import JSONRenderer

from .config import settings


def configure_logging() -> None:
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.log_json:
        shared_processors.append(JSONRenderer())
    else:
        shared_processors.append(ConsoleRenderer())

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()
