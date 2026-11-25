"""Application logging with a PII-scrubbing filter so that operational logs never
contain PAN, Aadhaar, account numbers, e-mails or phone numbers."""
from __future__ import annotations

import logging
import logging.handlers

from .config import get_settings

_configured = False


class PIIScrubFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        from .pii import scrub_for_log  # local import to avoid cycles

        try:
            msg = record.getMessage()
            record.msg = scrub_for_log(msg)
            record.args = ()
        except Exception:  # never break logging
            pass
        return True


def setup_logging() -> logging.Logger:
    global _configured
    logger = logging.getLogger("noticemate")
    if _configured:
        return logger
    s = get_settings()
    logger.setLevel(s.log_level.upper())
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    fh = logging.handlers.RotatingFileHandler(s.logs_dir / "noticemate.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.addFilter(PIIScrubFilter())
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    sh.addFilter(PIIScrubFilter())
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.propagate = False
    _configured = True
    return logger


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(f"noticemate.{name}")
