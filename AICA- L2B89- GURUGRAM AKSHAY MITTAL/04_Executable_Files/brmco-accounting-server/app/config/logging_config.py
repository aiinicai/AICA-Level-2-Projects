"""Logging setup with a filter that masks anything that looks like a secret."""
from __future__ import annotations

import logging
import re

_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|secret|password|token|mongodb(\+srv)?://[^\s]*?:)([=:\s\"']*)([^\s\"',&]+)"
)


class RedactSecretsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = _SECRET_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(3)}***", message)
        if redacted != message:
            record.msg, record.args = redacted, ()
        return True


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger("brmco")
    if getattr(root, "_brmco_configured", False):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(RedactSecretsFilter())
    root.addHandler(handler)
    root.setLevel(level.upper())
    root._brmco_configured = True  # type: ignore[attr-defined]
