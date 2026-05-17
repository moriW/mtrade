import logging
import sys
import structlog
from typing import Optional


def setup_logging(level: str = "INFO", file_path: Optional[str] = None):
    log_level = getattr(logging, level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
            if file_path
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    handlers = [logging.StreamHandler(sys.stdout)]
    if file_path:
        handlers.append(logging.FileHandler(file_path))

    logging.basicConfig(
        format="%(message)s", stream=sys.stdout, level=log_level, handlers=handlers
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    for handler in handlers:
        root_logger.addHandler(handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
