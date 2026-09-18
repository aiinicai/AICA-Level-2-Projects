"""Application-wide logging setup.

A single rotating log file captures every operation (timestamp, operation,
input/output filenames, page counts, result, error). Secrets (certificate
and document passwords) are never logged -- callers must use
:func:`redact` when a log line might otherwise include one.
"""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(log_dir: str | Path, level: int = logging.INFO) -> Path:
    """Configure the root application logger. Safe to call multiple times."""
    global _configured
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "pdf_office_utility.log"

    if _configured:
        return log_file

    root = logging.getLogger("pdf_office_utility")
    root.setLevel(level)
    root.propagate = False

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(console_handler)

    _configured = True
    return log_file


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"pdf_office_utility.{name}")


def redact(value: str | None) -> str:
    """Return a placeholder instead of a secret value, for use in log messages."""
    return "<redacted>" if value else "<empty>"


def log_operation(
    logger: logging.Logger,
    *,
    operation: str,
    input_file: str = "",
    output_file: str = "",
    pages: int | None = None,
    signing_pages: str = "",
    result: str = "",
    error: str = "",
) -> None:
    """Write one structured, greppable audit-style log line for a processed file."""
    parts = [f"operation={operation}"]
    if input_file:
        parts.append(f"input='{input_file}'")
    if output_file:
        parts.append(f"output='{output_file}'")
    if pages is not None:
        parts.append(f"pages={pages}")
    if signing_pages:
        parts.append(f"signed_pages='{signing_pages}'")
    parts.append(f"result={result}")
    if error:
        parts.append(f"error='{error}'")
    line = " ".join(parts)
    if result.lower() in {"failed", "error"}:
        logger.error(line)
    else:
        logger.info(line)
