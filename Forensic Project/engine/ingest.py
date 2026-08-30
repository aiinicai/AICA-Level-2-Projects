"""
Ingestion module for Red Flag Engine.
Handles file validation, cryptographic SHA-256 hashing, format routing.
"""
import hashlib
import os
from typing import BinaryIO, Tuple, Union

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".pdf"}

class UnsupportedFileFormatError(ValueError):
    """Raised when an uploaded file is not strictly .xlsx, .xls, or .pdf."""
    pass

def compute_sha256(file_obj_or_path: Union[str, BinaryIO, bytes]) -> str:
    """Compute SHA-256 hex digest of file contents."""
    h = hashlib.sha256()
    if isinstance(file_obj_or_path, str):
        with open(file_obj_or_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    elif isinstance(file_obj_or_path, bytes):
        h.update(file_obj_or_path)
    else:
        # File-like object
        pos = file_obj_or_path.tell()
        file_obj_or_path.seek(0)
        for chunk in iter(lambda: file_obj_or_path.read(65536), b""):
            h.update(chunk)
        file_obj_or_path.seek(pos)
    return h.hexdigest()

def validate_and_route(filename: str) -> str:
    """
    Validate file extension and return format type ('excel' or 'pdf').
    Raises UnsupportedFileFormatError if format is invalid.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileFormatError(
            f"Invalid file '{filename}'. Input is strictly .xlsx, .xls and .pdf. "
            "No CSV, JSON, or XML uploads are permitted."
        )
    if ext in [".xlsx", ".xls"]:
        return "excel"
    return "pdf"
