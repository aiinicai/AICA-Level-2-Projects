"""Technical log only (logs/app.log). Invoice contents are deliberately NOT logged."""
import logging
from logging.handlers import RotatingFileHandler
from .paths import logs_dir

_done = False


def get_logger() -> logging.Logger:
    global _done
    log = logging.getLogger("pec")
    if not _done:
        log.setLevel(logging.INFO)
        h = RotatingFileHandler(logs_dir() / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(module)s: %(message)s"))
        log.addHandler(h)
        _done = True
    return log
