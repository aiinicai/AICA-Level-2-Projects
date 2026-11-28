"""Application paths and static configuration.

All data stays on this computer. The data folder defaults to
%LOCALAPPDATA%\\IPT_DATA and can be overridden with the IPT_DATA_DIR
environment variable (useful for testing or a different drive).
"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "IPT - Invoice Processing Tool"
DB_FILENAME = "ipt.db"


def data_dir() -> Path:
    env = os.environ.get("IPT_DATA_DIR")
    if env:
        path = Path(env)
    else:
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        path = Path(base) / "IPT_DATA"
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path(base: Path | None = None) -> Path:
    return (base or data_dir()) / DB_FILENAME


def logs_dir(base: Path | None = None) -> Path:
    path = (base or data_dir()) / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
