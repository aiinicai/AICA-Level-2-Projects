"""Offline PAN/GSTIN validation; no network access."""
import re
from dataclasses import dataclass
PAN_TYPES = dict(P="Individual", C="Company", H="Hindu Undivided Family", F="Firm", A="Association of Persons", T="Trust", B="Body of Individuals", L="Local Authority", J="Artificial Juridical Person", G="Government")
STATES = {f"{n:02}" for n in range(1,39)} | {"97", "99"}
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
@dataclass(frozen=True)
class Validated:
    value: str
    kind: str
    meaning: str

def normalize(value: object) -> str:
    return value.strip().upper() if isinstance(value, str) else ""

def checksum(prefix: str) -> str:
    """Luhn mod 36, starting factor 2 at the rightmost payload digit."""
    if len(prefix) != 14 or any(c not in ALPHABET for c in prefix):
        raise ValueError("Checksum payload must contain 14 alphanumeric characters")
    total, factor = 0, 2
    for char in reversed(prefix):
        product = ALPHABET.index(char) * factor
        total += product // 36 + product % 36
        factor = 1 if factor == 2 else 2
    return ALPHABET[(36-total%36)%36]

def validate_pan(value: object) -> Validated:
    v = normalize(value)
    if len(v) != 10: raise ValueError(f"PAN length is {len(v)}, must be 10")
    if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", v): raise ValueError("PAN must be five letters, four digits, one letter")
    if v[3] not in PAN_TYPES: raise ValueError(f"Invalid PAN holder type {v[3]}")
    return Validated(v, "PAN", PAN_TYPES[v[3]])

def validate_gstin(value: object) -> Validated:
    v = normalize(value)
    if len(v) != 15: raise ValueError(f"GSTIN length is {len(v)}, must be 15")
    if v[:2] not in STATES: raise ValueError(f"Invalid state code {v[:2]}")
    pan = validate_pan(v[2:12])
    if not re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", v): raise ValueError("Invalid GSTIN format: position 13 must be 1-9/A-Z; position 14 must be Z")
    expected = checksum(v[:14])
    if v[-1] != expected: raise ValueError(f"Checksum mismatch: expected {expected}, found {v[-1]}")
    return Validated(v, "GSTIN", pan.meaning)

def validate(value: object) -> Validated:
    v = normalize(value)
    if len(v) == 10: return validate_pan(v)
    if len(v) == 15: return validate_gstin(v)
    raise ValueError(f"Length is {len(v)}, must be 10 (PAN) or 15 (GSTIN)")

def batch(values: str | list) -> list[str]:
    items = re.split(r"[,;\s]+", values) if isinstance(values, str) else values
    return list(dict.fromkeys(normalize(v) for v in items if normalize(v)))
