import os
import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])) / relative


def data_dir() -> Path:
    override = os.environ.get("FINSTOCK_DATA_DIR")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # Check for portable data directory adjacent to executable
    app_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    exe_dir = app_root.parent if getattr(sys, "frozen", False) else app_root
    portable_dir = exe_dir / "data"
    try:
        portable_dir.mkdir(parents=True, exist_ok=True)
        test_file = portable_dir / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        return portable_dir
    except Exception:
        pass

    # Fallback to LOCALAPPDATA
    for candidate in [
        Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Finstock" / "EventScope",
        Path.home() / ".finstock" / "eventscope",
        Path.cwd() / "data",
    ]:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test_file = candidate / ".write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            return candidate
        except Exception:
            continue

    # Absolute fallback to current directory
    cwd_dir = Path.cwd() / "data"
    cwd_dir.mkdir(parents=True, exist_ok=True)
    return cwd_dir

