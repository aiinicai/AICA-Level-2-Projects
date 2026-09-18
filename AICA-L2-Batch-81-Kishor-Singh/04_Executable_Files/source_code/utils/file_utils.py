"""Filesystem helpers: output naming, collision handling, temp workspace, misc.

Centralising output-path computation here guarantees the "never damage the
original file" rule is enforced in exactly one place.
"""
from __future__ import annotations

import shutil
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from models.enums import CollisionPolicy, NamingMode


def compute_output_path(
    source_path: str | Path,
    output_folder: str | Path | None,
    naming_mode: NamingMode = NamingMode.ADD_SUFFIX,
    suffix: str = "_Signed",
    prefix: str = "Signed_",
    collision_policy: CollisionPolicy = CollisionPolicy.RENAME,
) -> Path | None:
    """Compute the final output path for a processed file.

    Returns ``None`` when ``collision_policy`` is SKIP and the target already
    exists (caller should treat the job as skipped, not failed).

    The source file is *never* touched by this function; OVERWRITE_ORIGINAL
    simply means the computed output path equals the source path -- the
    caller engine still writes to a temp file first and swaps it in, so a
    crash mid-write can never corrupt the original (see
    :func:`atomic_replace`).
    """
    source_path = Path(source_path)
    folder = Path(output_folder) if output_folder else source_path.parent
    folder.mkdir(parents=True, exist_ok=True)

    stem, ext = source_path.stem, source_path.suffix
    if naming_mode == NamingMode.OVERWRITE_ORIGINAL:
        candidate = source_path
    elif naming_mode == NamingMode.ADD_PREFIX:
        candidate = folder / f"{prefix}{stem}{ext}"
    elif naming_mode == NamingMode.KEEP_ORIGINAL:
        candidate = folder / f"{stem}{ext}"
    else:  # ADD_SUFFIX (default / safest)
        candidate = folder / f"{stem}{suffix}{ext}"

    if naming_mode == NamingMode.OVERWRITE_ORIGINAL:
        # Overwriting the original is intentional here; no collision handling needed.
        return candidate

    if not candidate.exists():
        return candidate

    if collision_policy == CollisionPolicy.SKIP:
        return None
    if collision_policy == CollisionPolicy.REPLACE:
        return candidate

    # RENAME AUTOMATICALLY: ABC_Signed.pdf -> ABC_Signed (1).pdf, (2), ...
    counter = 1
    while True:
        renamed = folder / f"{candidate.stem} ({counter}){candidate.suffix}"
        if not renamed.exists():
            return renamed
        counter += 1


def atomic_replace(temp_path: str | Path, final_path: str | Path) -> None:
    """Move a finished temp file into place, replacing any existing file atomically.

    Using ``os.replace`` (via ``Path.replace``) means the destination is
    never left half-written even if the process is killed mid-copy.
    """
    Path(temp_path).replace(Path(final_path))


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def find_pdfs_in_folder(folder: str | Path, recursive: bool = False) -> list[Path]:
    folder = Path(folder)
    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted(p for p in folder.glob(pattern) if p.is_file())


def find_word_files_in_folder(folder: str | Path, recursive: bool = False) -> list[Path]:
    folder = Path(folder)
    globber = folder.rglob if recursive else folder.glob
    files = list(globber("*.docx")) + list(globber("*.doc"))
    return sorted(p for p in files if p.is_file())


def is_file_locked(path: str | Path) -> bool:
    """Best-effort check whether a file is open/locked by another process (Windows)."""
    p = Path(path)
    if not p.exists():
        return False
    try:
        with open(p, "a+b"):
            return False
    except OSError:
        return True


class TempWorkspace:
    """A per-batch temporary directory that is always cleaned up.

    Intermediate artefacts (e.g. a Word->PDF conversion before signing) are
    written here rather than next to user files, and the whole directory is
    removed once the batch finishes, cancels, or errors.
    """

    def __init__(self, base_dir: str | Path | None = None):
        base = Path(base_dir) if base_dir else Path(tempfile.gettempdir())
        base.mkdir(parents=True, exist_ok=True)
        self.path = base / f"pdf_office_utility_{uuid.uuid4().hex[:12]}"
        self.path.mkdir(parents=True, exist_ok=True)

    def new_file(self, suffix: str = ".pdf") -> Path:
        return self.path / f"{uuid.uuid4().hex}{suffix}"

    def cleanup(self) -> None:
        shutil.rmtree(self.path, ignore_errors=True)

    def __enter__(self) -> "TempWorkspace":
        return self

    def __exit__(self, *exc) -> None:
        self.cleanup()


@contextmanager
def temp_workspace(base_dir: str | Path | None = None) -> Iterator[TempWorkspace]:
    ws = TempWorkspace(base_dir)
    try:
        yield ws
    finally:
        ws.cleanup()
