"""GSTIN structure + check-digit validation.

Format: 2-digit state code, 10-char PAN, 1 entity number (1-9/A-Z),
1 char (normally 'Z'), 1 check character computed with the official
mod-36 weighted algorithm.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ipt.core.states import STATES

_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z][A-Z0-9][0-9A-Z]$")


def check_char(first14: str) -> str:
    total = 0
    for i, ch in enumerate(first14):
        value = _CHARS.index(ch)
        product = value * (2 if i % 2 else 1)
        total += product // 36 + product % 36
    return _CHARS[(36 - total % 36) % 36]


@dataclass(frozen=True)
class GstinResult:
    valid: bool
    message: str
    state_code: str | None = None
    pan: str | None = None


def normalize(gstin: str | None) -> str:
    return (gstin or "").strip().upper().replace(" ", "")


def validate_gstin(gstin: str | None) -> GstinResult:
    g = normalize(gstin)
    if not g:
        return GstinResult(False, "GSTIN is empty")
    if len(g) != 15:
        return GstinResult(False, f"GSTIN must be 15 characters (found {len(g)})")
    if not _PATTERN.match(g):
        return GstinResult(False, "GSTIN format is invalid")
    if g[:2] not in STATES:
        return GstinResult(False, f"Unknown state code {g[:2]}")
    expected = check_char(g[:14])
    if g[14] != expected:
        return GstinResult(False, f"Check digit mismatch (expected {expected})", g[:2], g[2:12])
    return GstinResult(True, "Valid GSTIN", g[:2], g[2:12])


# ------------------------------------------------------------------ OCR repair
_TO_DIGIT = {"O": ["0"], "D": ["0"], "Q": ["0"], "I": ["1"], "L": ["1"], "Z": ["2"], "S": ["5", "8"], "B": ["8"],
             "G": ["6"], "T": ["7"], "@": ["0", "8"], "!": ["1"], "|": ["1"]}
_TO_LETTER = {"0": ["O", "Q", "D"], "1": ["I", "L"], "2": ["Z"], "5": ["S"], "8": ["B"], "6": ["G"], "4": ["A"],
              "7": ["T"], "!": ["I"], "|": ["I"]}
_DIGIT_POS = (0, 1, 7, 8, 9, 10)
_LETTER_POS = (2, 3, 4, 5, 6, 11)


def _candidates_15(chunk: str, base_cost: int = 0) -> list[tuple[int, str]]:
    """Valid GSTINs reachable from a 15-character chunk, with the number of characters changed."""
    options: list[list[str]] = []
    for i, ch in enumerate(chunk):
        if i in _DIGIT_POS:
            opts = [ch] if ch.isdigit() else _TO_DIGIT.get(ch, [])
        elif i in _LETTER_POS:
            opts = [ch] if ch.isalpha() else _TO_LETTER.get(ch, [])
        elif i == 13:
            opts = ["Z"] if ch in "Z27" else [ch]
        else:
            opts = ([ch] if ch.isalnum() else []) + _TO_LETTER.get(ch, []) + _TO_DIGIT.get(ch, [])
        if not opts:
            return []
        options.append(list(dict.fromkeys(opts)))
    combos = [(base_cost, "")]
    for i, opts in enumerate(options):
        combos = [(c + (o != chunk[i] and not (i == 13 and chunk[i] in "27")), s + o)
                  for c, s in combos for o in opts]
        if len(combos) > 512:
            return []
    return [(c, s) for c, s in combos if validate_gstin(s).valid]


def repair_ocr_gstin(raw: str) -> str | None:
    """Fix typical OCR confusions (O/0, B/8, S/5/8, I/1 ...) using the GSTIN's fixed character
    positions, and a single stray character inserted by OCR. A repaired value is returned ONLY
    if exactly one candidate passes the official check digit, so nothing is guessed."""
    s = re.sub(r"[^A-Z0-9@!|]", "", (raw or "").upper())
    found: list[tuple[int, str]] = []
    for start in range(0, max(1, len(s) - 14)):
        chunk = s[start:start + 15]
        if len(chunk) == 15:
            found += _candidates_15(chunk)
    if not found:
        # one extra character read by OCR (e.g. 'O8SDWIPR2155G1ZA' for 08DWIPR2155G1ZA)
        for start in range(0, max(1, len(s) - 15)):
            chunk = s[start:start + 16]
            if len(chunk) != 16:
                break
            for k in range(16):
                found += _candidates_15(chunk[:k] + chunk[k + 1:], base_cost=1)
    if not found:
        return None
    # the reading that needs the fewest character changes wins – only if no other reading ties with it
    best = min(c for c, _ in found)
    winners = {g for c, g in found if c == best}
    return winners.pop() if len(winners) == 1 else None
