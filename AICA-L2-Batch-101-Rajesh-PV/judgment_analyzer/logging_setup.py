"""Logging configuration with API-key redaction.

Logs never include document text; they record processing steps and errors only.
"""

from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import user_config_dir

# Google API keys start with "AIza"; also redact anything passed as key=...
_KEY_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}|\bAQ\.[0-9A-Za-z_\-.]{20,}"),
    re.compile(r"(?i)(api[_-]?key[\"'=:\s]+)[^\s\"',}]+"),
]


def redact(text: str) -> str:
    text = _KEY_PATTERNS[0].sub("[REDACTED-KEY]", text)
    return _KEY_PATTERNS[1].sub(r"\1[REDACTED]", text)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - malformed log call
            return True
        record.msg = redact(message)
        record.args = ()
        return True


def setup_logging(level: int = logging.INFO) -> Path:
    """Configure console + rotating file logging. Returns the log file path."""
    log_dir = user_config_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "judgment_insight_analyzer.log"

    fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    redactor = RedactingFilter()

    file_handler = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    file_handler.addFilter(redactor)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.addFilter(redactor)

    root = logging.getLogger()
    root.setLevel(level)
    # Under pythonw (no console window) sys.stderr is None - log to file only.
    root.handlers[:] = [file_handler, console] if sys.stderr else [file_handler]
    # Third-party HTTP libraries are noisy at INFO and may echo request URLs.
    for noisy in ("httpx", "httpcore", "urllib3", "google_genai", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return log_file
