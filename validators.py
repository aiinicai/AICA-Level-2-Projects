"""Public-safe errors and upload validation."""
from pathlib import PurePath

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_PAGES = 60
MAX_TEXT_CHARS = 300_000


class AppError(Exception):
    """An actionable message safe to display without exception details."""


def validate_pdf(data: bytes, filename: str, mime_type: str | None = None) -> None:
    if PurePath(filename).suffix.lower() != ".pdf":
        raise AppError("Please upload a PDF file.")
    if mime_type and mime_type.lower() not in {
        "application/pdf", "application/x-pdf", "application/octet-stream"
    }:
        raise AppError("This file is not identified as a PDF. Please export it as a PDF and retry.")
    if not data:
        raise AppError("The uploaded file is empty. Please choose a readable PDF.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise AppError("Please upload a PDF no larger than 20 MB.")
    if not data.lstrip().startswith(b"%PDF-"):
        raise AppError("Unable to read PDF. The file may be damaged or is not a PDF.")
