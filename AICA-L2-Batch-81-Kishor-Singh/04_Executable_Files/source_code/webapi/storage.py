"""Local filesystem document storage for the web API.

A real "Team Deployment" would point this at protected object storage
(S3-compatible, Azure Blob, etc.) behind authenticated, scoped download
URLs -- this local-disk implementation is what runs by default for
development, testing, and small single-office deployments. The storage
location is intentionally separate from the desktop app's own files.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path


def _default_storage_dir() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "CADocuFlowAI" / "webapi_storage"
    base.mkdir(parents=True, exist_ok=True)
    return base


STORAGE_DIR = Path(os.environ.get("DOCUFLOW_STORAGE_DIR", str(_default_storage_dir())))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def save_document_bytes(content: bytes) -> tuple[str, str]:
    """Save file content under a random name; returns (storage_path, sha256)."""
    sha256 = hashlib.sha256(content).hexdigest()
    key = f"{uuid.uuid4().hex}.bin"
    path = STORAGE_DIR / key
    path.write_bytes(content)
    return str(path), sha256


def read_document_bytes(storage_path: str) -> bytes:
    return Path(storage_path).read_bytes()
