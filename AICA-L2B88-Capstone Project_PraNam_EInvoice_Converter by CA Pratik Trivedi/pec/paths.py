"""Local folder locations. Everything stays on this computer."""
import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):          # running as PyInstaller EXE
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def sub(name: str) -> Path:
    p = app_dir() / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def settings_dir() -> Path: return sub("settings")
def profiles_dir() -> Path: return sub("profiles")
def output_dir() -> Path: return sub("Output")
def logs_dir() -> Path: return sub("logs")
