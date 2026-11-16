"""Path helpers: app data location, path normalisation, containment checks, drive types."""
from __future__ import annotations

import ctypes
import os
import sys
from datetime import datetime, timezone

APP_DIR_NAME = "AICA Folder Storage Manager"


def app_data_dir() -> str:
    override = os.environ.get("AICA_FSM_DATA")
    if override:
        base = override
    else:
        base = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), APP_DIR_NAME)
    os.makedirs(base, exist_ok=True)
    return base


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def ts_to_iso(ts: float | None) -> str:
    if ts is None:
        return ""
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return ""


def normalize_root(path: str) -> str:
    """Normalise a user-selected root but keep it the same location (no resolving of links)."""
    p = path.strip().strip('"')
    p = p.replace("/", "\\")
    if p.startswith("\\\\"):
        body = p[2:].rstrip("\\")
        while "\\\\" in body:
            body = body.replace("\\\\", "\\")
        return "\\\\" + body
    p = os.path.normpath(p)
    if len(p) == 2 and p[1] == ":":
        p += "\\"
    return p


def is_within(root: str, path: str) -> bool:
    """True if *path* is root itself or below it (case-insensitive, separator-aware, no '..' escapes)."""
    r = os.path.normcase(os.path.normpath(root)).rstrip("\\")
    p = os.path.normcase(os.path.normpath(path)).rstrip("\\")
    if p == r:
        return True
    return p.startswith(r + "\\")


def join_rel(root: str, rel: str) -> str:
    full = os.path.join(root, rel)
    if not is_within(root, full):
        raise ValueError(f"Path escapes project folder: {rel}")
    return full


def rel_of(root: str, full: str) -> str:
    if not is_within(root, full):
        raise ValueError(f"Path is outside project folder: {full}")
    r = os.path.normpath(root).rstrip("\\")
    f = os.path.normpath(full)
    rel = f[len(r):].lstrip("\\")
    return rel


DRIVE_UNKNOWN, DRIVE_NO_ROOT_DIR, DRIVE_REMOVABLE, DRIVE_FIXED, DRIVE_REMOTE, DRIVE_CDROM, DRIVE_RAMDISK = range(7)


def drive_type(path: str) -> int:
    if sys.platform != "win32":
        return DRIVE_FIXED
    p = os.path.abspath(path)
    if p.startswith("\\\\"):
        return DRIVE_REMOTE
    root = os.path.splitdrive(p)[0] + "\\"
    try:
        return ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root))
    except Exception:
        return DRIVE_UNKNOWN


def location_kind(path: str) -> str:
    t = drive_type(path)
    if path.startswith("\\\\"):
        return "Network (UNC)"
    return {
        DRIVE_FIXED: "Local drive",
        DRIVE_REMOVABLE: "Removable drive",
        DRIVE_REMOTE: "Mapped network drive",
        DRIVE_CDROM: "Optical drive",
        DRIVE_RAMDISK: "RAM disk",
    }.get(t, "Unknown")


def supports_recycle_bin(path: str) -> bool:
    """Recycle Bin is only reliable on fixed local drives. Network shares and removable media
    delete permanently, so those must be treated as permanent deletion."""
    return drive_type(path) == DRIVE_FIXED and not path.startswith("\\\\")


def human_size(n: int | None) -> str:
    if n is None:
        return ""
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:,.0f} {unit}" if unit == "B" else f"{n:,.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"


def file_type_of(name: str) -> str:
    ext = os.path.splitext(name)[1].lower()
    return ext[1:] if ext else "(none)"


CATEGORIES = {
    "Documents": {"pdf", "doc", "docx", "rtf", "odt", "txt", "md"},
    "Spreadsheets": {"xls", "xlsx", "xlsm", "csv", "ods"},
    "Presentations": {"ppt", "pptx", "odp"},
    "Images": {"jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "webp", "heic"},
    "Video": {"mp4", "mov", "avi", "mkv", "wmv"},
    "Audio": {"mp3", "wav", "m4a", "flac", "aac"},
    "Archives": {"zip", "rar", "7z", "tar", "gz"},
    "Email": {"msg", "eml", "pst", "ost"},
}


def category_of(ext: str) -> str:
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return "Other"
