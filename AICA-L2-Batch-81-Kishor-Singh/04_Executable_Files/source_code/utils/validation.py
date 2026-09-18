"""Input validation helpers with clear, non-technical error messages.

Every exception raised here is meant to be shown almost verbatim in a
QMessageBox to a non-programmer office user, so messages avoid jargon,
stack traces and library names.
"""
from __future__ import annotations

from pathlib import Path


class ValidationError(Exception):
    """Raised for any user-facing, recoverable input problem."""


class EncryptedPdfError(ValidationError):
    """Raised when a PDF is password protected and no/incorrect password was supplied."""


class UnsupportedFileError(ValidationError):
    """Raised when a file's type/extension is not supported by the requested operation."""


SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
SUPPORTED_WORD_EXTENSIONS = {".doc", ".docx"}
SUPPORTED_PDF_EXTENSION = ".pdf"


def validate_file_exists(path: str | Path, what: str = "File") -> Path:
    p = Path(path)
    if not p.exists():
        raise ValidationError(f"{what} not found:\n{p}")
    if not p.is_file():
        raise ValidationError(f"{what} is not a valid file:\n{p}")
    return p


def validate_pdf_path(path: str | Path) -> Path:
    p = validate_file_exists(path, "PDF file")
    if p.suffix.lower() != SUPPORTED_PDF_EXTENSION:
        raise UnsupportedFileError(f"Not a PDF file: {p.name}")
    return p


def validate_image_path(path: str | Path) -> Path:
    p = validate_file_exists(path, "Signature image")
    if p.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise UnsupportedFileError(
            f"Unsupported signature image type '{p.suffix}'. Use PNG, JPG or JPEG."
        )
    return p


def validate_word_path(path: str | Path) -> Path:
    p = validate_file_exists(path, "Word document")
    if p.suffix.lower() not in SUPPORTED_WORD_EXTENSIONS:
        raise UnsupportedFileError(f"Not a Word document: {p.name}")
    return p


def validate_output_folder(path: str | Path) -> Path:
    p = Path(path)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValidationError(f"Cannot create/write to output folder:\n{p}\n\n{exc}") from exc
    probe = p / ".pdf_office_utility_write_test.tmp"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise ValidationError(f"No write permission for output folder:\n{p}\n\n{exc}") from exc
    return p


def validate_percentage(value: float, name: str = "Value") -> float:
    if not (0.0 <= value <= 100.0):
        raise ValidationError(f"{name} must be between 0 and 100.")
    return value
