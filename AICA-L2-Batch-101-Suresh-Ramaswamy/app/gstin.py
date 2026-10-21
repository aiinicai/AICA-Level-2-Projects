"""GSTIN validation (format + state code + check digit). Not proof of active registration."""
import re

from .config import STATE_CODES

_GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
_UIN_RE = re.compile(r"^\d{4}[A-Z]{3}\d{5}[A-Z0-9]$")
_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def checksum_char(first14: str) -> str:
    total = 0
    for i, c in enumerate(first14):
        v = _CHARS.index(c) * (1 if i % 2 == 0 else 2)
        total += v // 36 + v % 36
    return _CHARS[(36 - total % 36) % 36]


def validate_gstin(g: str):
    """Return (level, message): level in 'ok', 'warn' (check-digit only), 'error'."""
    g = (g or "").strip().upper()
    if not g:
        return "error", "GSTIN is empty"
    if _UIN_RE.match(g):
        return "ok", "UIN format accepted"
    if len(g) != 15:
        return "error", "GSTIN must be 15 characters"
    if not _GSTIN_RE.match(g):
        return "error", "GSTIN structure is invalid"
    if g[:2] not in STATE_CODES:
        return "error", f"Unknown state code {g[:2]}"
    if checksum_char(g[:14]) != g[14]:
        return "warn", "GSTIN check digit does not match (possible typing error)"
    return "ok", "Format valid (registration status not verified)"


def is_valid_structure(g: str) -> bool:
    return validate_gstin(g)[0] in ("ok", "warn")


def state_of(g: str) -> str:
    g = (g or "").strip()
    return g[:2] if len(g) >= 2 and g[:2] in STATE_CODES else ""
