"""Application logging.

* ``logs/app.log``   — everything (rotating)
* ``logs/errors.log`` — technical errors with tracebacks (rotating)

A redaction filter masks anything that looks like a password, key or token.
"""
from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

_SECRET_PATTERN = re.compile(r"(?i)(password|passwd|api[_-]?key|secret|token)([\"'\s:=]+)([^\s\"',&<]+)")


class RedactSecretsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = _SECRET_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2)}***", message)
        if redacted != message:
            record.msg, record.args = redacted, ()
        return True


def configure_logging(log_dir: Path, level: str = "INFO") -> None:
    root = logging.getLogger("brmco")
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()
    root.setLevel(level.upper())
    root.propagate = False

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    redact = RedactSecretsFilter()

    log_dir.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        RotatingFileHandler(log_dir / "app.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8"),
        logging.StreamHandler(),
    ]
    errors = RotatingFileHandler(log_dir / "errors.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    errors.setLevel(logging.ERROR)
    handlers.append(errors)

    for h in handlers:
        h.setFormatter(fmt)
        h.addFilter(redact)
        root.addHandler(h)
