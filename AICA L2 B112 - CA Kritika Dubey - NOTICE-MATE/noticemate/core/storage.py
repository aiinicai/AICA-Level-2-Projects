"""Local document storage. Originals stay on disk under the workspace; never
transmitted. Optional at-rest encryption with Fernet (key from env)."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from .config import get_settings
from .errors import ValidationError
from .security import safe_join


def _fernet():
    key = get_settings().encryption_key
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet

        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        raise ValidationError(f"NOTICEMATE_ENCRYPTION_KEY is invalid: {type(exc).__name__}")


def case_dir(case_id: int) -> Path:
    d = get_settings().docs_dir / f"case_{int(case_id)}"
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:  # pragma: no cover
        pass
    return d


def save_document(case_id: int, ext: str, data: bytes) -> tuple[str, bool]:
    stored = f"{uuid.uuid4().hex}{ext}"
    f = _fernet()
    payload = f.encrypt(data) if f else data
    path = safe_join(case_dir(case_id), stored + (".enc" if f else ""))
    with open(path, "wb") as fh:
        fh.write(payload)
    try:
        os.chmod(path, 0o600)
    except OSError:  # pragma: no cover
        pass
    return path.name, bool(f)


def load_document(case_id: int, stored_name: str, encrypted: bool) -> bytes:
    path = safe_join(case_dir(case_id), stored_name)
    data = path.read_bytes()
    if encrypted:
        f = _fernet()
        if f is None:
            raise ValidationError("Document is encrypted but NOTICEMATE_ENCRYPTION_KEY is not set.")
        data = f.decrypt(data)
    return data


def delete_document(case_id: int, stored_name: str) -> None:
    path = safe_join(case_dir(case_id), stored_name)
    if path.exists():
        path.unlink()
