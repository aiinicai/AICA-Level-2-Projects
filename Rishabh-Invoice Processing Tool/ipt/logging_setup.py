"""Rotating file + console logging. Never log passwords or secrets."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_dir: Path, level: int = logging.INFO) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(level)
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return
    fh = RotatingFileHandler(log_dir / "ipt.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)
