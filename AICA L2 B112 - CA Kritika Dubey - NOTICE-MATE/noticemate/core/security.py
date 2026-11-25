"""Password hashing, token handling, filename / upload validation."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from pathlib import Path

from .config import ALLOWED_EXTENSIONS
from .errors import ValidationError

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    validate_password_strength(password)
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_hex, dk_hex = stored.split("$")
        if algo != "scrypt":
            return False
        dk = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def validate_password_strength(password: str) -> None:
    if len(password) < 10:
        raise ValidationError("Password must be at least 10 characters.")
    classes = sum(bool(re.search(p, password)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]"))
    if classes < 3:
        raise ValidationError("Password must contain at least three of: lowercase, uppercase, digit, symbol.")


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]")


def sanitize_filename(name: str) -> str:
    name = Path(name.replace("\\", "/")).name  # drop any directory components
    name = _SAFE_NAME.sub("_", name).strip(" .")
    if not name:
        raise ValidationError("Invalid file name.")
    return name[:150]


_MAGIC = {
    ".pdf": [b"%PDF"],
    ".docx": [b"PK\x03\x04"],
    ".xlsx": [b"PK\x03\x04"],
    ".xlsm": [b"PK\x03\x04"],
    ".png": [b"\x89PNG"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".tif": [b"II*\x00", b"MM\x00*"],
    ".tiff": [b"II*\x00", b"MM\x00*"],
}


def validate_upload(filename: str, data: bytes, max_mb: int) -> str:
    safe = sanitize_filename(filename)
    ext = Path(safe).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"File type '{ext}' is not allowed.", details={"allowed": sorted(ALLOWED_EXTENSIONS)})
    if not data:
        raise ValidationError("Empty file.")
    if len(data) > max_mb * 1024 * 1024:
        raise ValidationError(f"File exceeds {max_mb} MB limit.")
    sigs = _MAGIC.get(ext)
    if sigs and not any(data.startswith(s) for s in sigs):
        raise ValidationError("File content does not match its extension.")
    if ext in {".csv", ".txt"}:
        try:
            data[:4096].decode("utf-8")
        except UnicodeDecodeError:
            try:
                data[:4096].decode("cp1252")
            except UnicodeDecodeError:
                raise ValidationError("Text file is not valid UTF-8/CP1252.")
    return safe


def safe_join(base: Path, name: str) -> Path:
    p = (base / name).resolve()
    if base.resolve() not in p.parents and p != base.resolve():
        raise ValidationError("Path traversal detected.")
    return p
