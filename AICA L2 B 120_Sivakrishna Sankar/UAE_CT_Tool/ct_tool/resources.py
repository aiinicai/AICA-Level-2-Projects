"""Resource resolution helpers for dev mode and frozen (PyInstaller) mode."""
from __future__ import annotations

import sys
from pathlib import Path


def get_base_dir() -> Path:
    """Return the base directory for locating bundled application data."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    # In source / development mode, root is the parent directory of ct_tool
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str | Path) -> Path:
    """Return absolute path to a resource file or directory."""
    return get_base_dir().joinpath(*parts)
