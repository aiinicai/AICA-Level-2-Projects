"""File signature, filename, path and ZIP archive safety controls."""
from __future__ import annotations

import os
import re
import stat
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.core.errors import DocumentError, UnsafeArchiveError

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".csv", ".txt", ".html", ".htm",
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".zip",
}
MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv", ".txt": "text/plain", ".html": "text/html", ".htm": "text/html",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".tif": "image/tiff", ".tiff": "image/tiff", ".zip": "application/zip",
}


def sanitize_filename(name: str, max_length: int = 180) -> str:
    name = unicodedata.normalize("NFKC", Path(name).name)
    name = re.sub(r"[\x00-\x1f<>:\"/\\|?*]", "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name or name in {".", ".."}:
        name = "document"
    stem, suffix = os.path.splitext(name)
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    upper_stem = stem.upper()
    if upper_stem in reserved or any(upper_stem.startswith(item + "_") for item in reserved):
        stem = "_" + stem
    allowed_suffix = re.sub(r"[^A-Za-z0-9.]", "", suffix)[:15]
    available = max(1, max_length - len(allowed_suffix))
    return stem[:available] + allowed_suffix


def contained_path(root: Path, relative: str | Path) -> Path:
    root = root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise DocumentError("File path attempted to leave the permitted storage area.") from exc
    return candidate


def detect_media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise DocumentError(f"Unsupported file type: {suffix or 'no extension'}.")
    try:
        head = path.read_bytes()[:32]
    except OSError as exc:
        raise DocumentError("Selected document could not be read.") from exc
    if not head:
        raise DocumentError("Empty files cannot be imported.")
    if suffix == ".pdf" and not head.startswith(b"%PDF-"):
        raise DocumentError("File extension is PDF but its signature is not a PDF.")
    if suffix in {".png"} and not head.startswith(b"\x89PNG\r\n\x1a\n"):
        raise DocumentError("Image signature does not match PNG.")
    if suffix in {".jpg", ".jpeg"} and not head.startswith(b"\xff\xd8\xff"):
        raise DocumentError("Image signature does not match JPEG.")
    if suffix in {".tif", ".tiff"} and not (head.startswith(b"II*\x00") or head.startswith(b"MM\x00*")):
        raise DocumentError("Image signature does not match TIFF.")
    if suffix in {".zip", ".docx", ".xlsx"}:
        if not head.startswith(b"PK\x03\x04"):
            raise DocumentError("Office/ZIP signature is invalid.")
        try:
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
                if suffix == ".docx" and "word/document.xml" not in names:
                    raise DocumentError("The selected file is not a valid DOCX document.")
                if suffix == ".xlsx" and "xl/workbook.xml" not in names:
                    raise DocumentError("The selected file is not a valid XLSX workbook.")
        except zipfile.BadZipFile as exc:
            raise DocumentError("Office/ZIP document is corrupt.") from exc
    if suffix in {".txt", ".csv", ".html", ".htm"} and b"\x00" in head:
        raise DocumentError("Text document appears to contain unsupported binary data.")
    return MEDIA_TYPES[suffix]


@dataclass(frozen=True)
class ZipLimits:
    max_files: int = 2000
    max_total_bytes: int = 500 * 1024 * 1024
    max_single_bytes: int = 100 * 1024 * 1024
    max_ratio: int = 100


def safe_extract_zip(archive_path: Path, destination: Path, limits: ZipLimits = ZipLimits()) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    total = 0
    try:
        archive = zipfile.ZipFile(archive_path)
    except zipfile.BadZipFile as exc:
        raise UnsafeArchiveError("ZIP archive is corrupt or invalid.") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > limits.max_files:
            raise UnsafeArchiveError("ZIP archive contains too many files.")
        for info in infos:
            normalized = info.filename.replace("\\", "/")
            pure = PurePosixPath(normalized)
            if pure.is_absolute() or ".." in pure.parts or re.match(r"^[A-Za-z]:", normalized):
                raise UnsafeArchiveError("ZIP archive contains an unsafe path.")
            unix_mode = info.external_attr >> 16
            if stat.S_ISLNK(unix_mode):
                raise UnsafeArchiveError("ZIP archive contains a symbolic link.")
            if info.is_dir():
                continue
            if info.file_size > limits.max_single_bytes:
                raise UnsafeArchiveError("ZIP archive contains an oversized file.")
            total += info.file_size
            if total > limits.max_total_bytes:
                raise UnsafeArchiveError("ZIP archive expands beyond the permitted total size.")
            if info.compress_size == 0 and info.file_size > 0:
                raise UnsafeArchiveError("ZIP archive has an invalid compression ratio.")
            if info.compress_size and info.file_size / info.compress_size > limits.max_ratio:
                raise UnsafeArchiveError("ZIP archive has a suspicious compression ratio.")
            target = contained_path(destination, Path(*pure.parts))
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, open(target, "xb") as output:
                copied = 0
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > info.file_size or copied > limits.max_single_bytes:
                        raise UnsafeArchiveError("ZIP member exceeded its declared safe size.")
                    output.write(chunk)
            extracted.append(target)
    return extracted
