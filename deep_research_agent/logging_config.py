"""Logging setup for the Deep Research Agent.

Call setup_logging() once at application startup before any other module logs.
Sensitive data (API keys, credentials) must never appear in log output (SECURITY-03).
"""

import logging
import logging.handlers
from pathlib import Path

_CONFIGURED = False


def setup_logging(
    log_dir: Path,
    console_level: str = "WARNING",
    file_level: str = "DEBUG",
) -> None:
    """Configure root logger with a rotating file handler and a console handler.

    Idempotent — safe to call multiple times; subsequent calls are no-ops.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "deep_research_agent.log"

    fmt = "%(asctime)s %(levelname)-8s %(name)s %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Rotating file handler: 10 MB, 5 backups
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
    console_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _CONFIGURED = True
