"""Mask PAN, Aadhaar, bank account numbers and IFSC before anything leaves the PC.
GSTINs are kept: they are public and needed to identify the parties."""
from __future__ import annotations

import re

from .ocr import Word

PAN = re.compile(r"(?<![0-9A-Z])[A-Z]{3}[ABCFGHLJPTK][A-Z]\d{4}[A-Z](?![0-9A-Z])")
IFSC = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
AADHAAR = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
ACCOUNT = re.compile(r"\b\d{9,18}\b")
UPI = re.compile(r"\b[\w.\-]{2,}@[a-z]{3,}\b", re.I)
BANK_CTX = re.compile(r"a/?c|account|acct|bank|ifsc|beneficiary|branch|upi", re.I)
MASK = "[REDACTED]"


def _is_gstin_part(text: str, start: int) -> bool:
    return start >= 2 and text[start - 2:start].isdigit()


def mask_text(text: str) -> tuple[str, int]:
    count = 0

    def pan_sub(m):
        nonlocal count
        if _is_gstin_part(m.string, m.start()):
            return m.group(0)
        count += 1
        return MASK

    out_lines = []
    for line in text.splitlines():
        line = PAN.sub(pan_sub, line)
        n0 = line.count(MASK)
        line = IFSC.sub(MASK, line)
        line = UPI.sub(MASK, line)
        line = AADHAAR.sub(MASK, line)
        if BANK_CTX.search(line):
            line = ACCOUNT.sub(MASK, line)
        count += line.count(MASK) - n0
        out_lines.append(line)
    return "\n".join(out_lines), count


def sensitive_word_indexes(words: list[Word]) -> set[int]:
    """Indexes of OCR words to black out (by pattern, or digit runs on a bank-details row)."""
    hits: set[int] = set()
    rows: dict[int, list[int]] = {}
    for i, w in enumerate(words):
        rows.setdefault(int((w.y + w.h / 2) // max(w.h, 1)), []).append(i)
    for idxs in rows.values():
        row_text = " ".join(words[i].text for i in idxs)
        bank_row = bool(BANK_CTX.search(row_text))
        for i in idxs:
            t = words[i].text.strip(".,:;()")
            if (PAN.fullmatch(t) or IFSC.fullmatch(t) or UPI.fullmatch(t)
                    or (bank_row and re.fullmatch(r"\d{6,18}", t))
                    or re.fullmatch(r"\d{4}", t) and AADHAAR.search(row_text)):
                hits.add(i)
    return hits


def redact_image(img: bytes, words: list[Word], ocr_width: float | None = None) -> tuple[bytes, int]:
    """Black boxes over sensitive words. Word boxes may come from an upscaled copy: pass its width."""
    from PyQt6.QtCore import QBuffer, QIODevice, QRectF
    from PyQt6.QtGui import QColor, QImage, QPainter
    q = QImage.fromData(img).convertToFormat(QImage.Format.Format_RGB32)
    scale = q.width() / ocr_width if ocr_width else 1.0
    idxs = sensitive_word_indexes(words)
    p = QPainter(q)
    for i in idxs:
        w = words[i]
        p.fillRect(QRectF(w.x * scale - 3, w.y * scale - 3, w.w * scale + 6, w.h * scale + 6), QColor("black"))
    p.end()
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    q.save(buf, "PNG")
    return bytes(buf.data()), len(idxs)
