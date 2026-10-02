"""GST reference data and helpers (states, GSTIN checks, valid rates)."""
from __future__ import annotations

import re
from decimal import Decimal

STATES: dict[str, str] = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra", "29": "Karnataka",
    "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
    "97": "Other Territory",
}
STATE_NAMES = list(STATES.values())
_STATE_BY_KEY = {name.lower(): name for name in STATE_NAMES}
_STATE_BY_KEY.update({code: name for code, name in STATES.items()})
_STATE_BY_KEY.update({"orissa": "Odisha", "pondicherry": "Puducherry", "new delhi": "Delhi",
                      "nct of delhi": "Delhi", "j&k": "Jammu and Kashmir"})

# Valid IGST rates (CGST/SGST are half of these).
IGST_RATES = {Decimal(x) for x in ("0", "0.1", "0.25", "1", "1.5", "3", "5", "6", "7.5", "12", "18", "28", "40")}
CGST_RATES = {r / 2 for r in IGST_RATES}

_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def normalise_state(value: str) -> str | None:
    """Accepts 'Maharashtra', '27', '27-Maharashtra', '27 - Maharashtra'. Returns canonical name."""
    v = value.strip().lower()
    if not v:
        return None
    if v in _STATE_BY_KEY:
        return _STATE_BY_KEY[v]
    m = re.match(r"^(\d{1,2})\s*[-–:]\s*(.+)$", v)
    if m:
        return _STATE_BY_KEY.get(m.group(1).zfill(2)) or _STATE_BY_KEY.get(m.group(2).strip())
    if v.isdigit():
        return _STATE_BY_KEY.get(v.zfill(2))
    return None


def gstin_checksum_char(first14: str) -> str:
    total = 0
    for i, ch in enumerate(first14):
        product = _CHARS.index(ch) * (2 if i % 2 else 1)
        total += product // 36 + product % 36
    return _CHARS[(36 - total % 36) % 36]


def gstin_error(gstin: str) -> str | None:
    """Returns a human-readable problem with the GSTIN, or None if it is valid."""
    if len(gstin) != 15:
        return f'GSTIN "{gstin}" must be 15 characters (found {len(gstin)}).'
    if not _GSTIN_RE.match(gstin):
        return f'GSTIN "{gstin}" is not in the valid format (e.g. 27AAPFU0939F1ZV).'
    if gstin[:2] not in STATES:
        return f'GSTIN "{gstin}" has an unknown state code {gstin[:2]}.'
    if gstin_checksum_char(gstin[:14]) != gstin[14]:
        return f'GSTIN "{gstin}" fails the checksum — please re-check for a typing error.'
    return None


def state_from_gstin(gstin: str) -> str | None:
    return STATES.get(gstin[:2]) if len(gstin) >= 2 else None
