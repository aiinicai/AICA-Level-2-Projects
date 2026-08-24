"""Centralized logging configuration.

Per the spec: use logging rather than print statements throughout the
application. This module is imported once from app/main.py (or from
conftest.py in tests) to configure handlers; all other modules just call
`logging.getLogger(__name__)`.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path


def configure_logging(log_dir: Path, level: str = "INFO") -> None:
    """Configure root logger with console + rotating file handlers.

    Args:
        log_dir: Directory to write log files into. Created if absent.
        level: Standard logging level name, e.g. "INFO", "DEBUG".
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    root = logging.getLogger()
    root.setLevel(level.upper())

    # Avoid duplicate handlers if configure_logging() is called more than
    # once (e.g. once by Streamlit's script-rerun model).
    if root.handlers:
        return

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(level.upper())

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)  # file always captures full detail

    root.addHandler(console_handler)
    root.addHandler(file_handler)

    # Quiet noisy third-party loggers unless we're explicitly debugging.
    for noisy in ("urllib3", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
