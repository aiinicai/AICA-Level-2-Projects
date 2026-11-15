"""Pictures attached to message templates and sends (festival greetings, notices). Stored in the data folder under uploads/messages."""
import io
import secrets
from pathlib import Path

from PIL import Image

from ..config import data_dir

MAX_BYTES = 3 * 1024 * 1024
ALLOWED = {"PNG": ("png", "image/png"), "JPEG": ("jpg", "image/jpeg")}


class PictureError(Exception):
    pass


def folder() -> Path:
    p = data_dir() / "uploads" / "messages"
    p.mkdir(parents=True, exist_ok=True)
    return p


def save(raw: bytes) -> str:
    """Checks that the upload really is a PNG/JPG and stores it under a random name. Returns the file name."""
    if len(raw) > MAX_BYTES:
        raise PictureError("The picture must be 3 MB or smaller.")
    try:
        img = Image.open(io.BytesIO(raw))
        fmt = img.format
        img.verify()
    except Exception:
        raise PictureError("That file is not a valid PNG or JPG picture.")
    if fmt not in ALLOWED:
        raise PictureError("The picture must be a PNG or JPG.")
    name = f"{secrets.token_hex(12)}.{ALLOWED[fmt][0]}"
    (folder() / name).write_bytes(raw)
    return name


def path(name: str | None) -> Path | None:
    if not name or "/" in name or "\\" in name or ".." in name:
        return None
    p = folder() / name
    return p if p.is_file() else None


def attachment(name: str | None):
    """(file name, bytes, mime) for an email, or None."""
    p = path(name)
    if p is None:
        return None
    mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    return ("picture" + p.suffix, p.read_bytes(), mime)
