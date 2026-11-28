"""Normalisation helpers used by extraction, duplicates and reconciliation."""
from __future__ import annotations

import re
from datetime import date, datetime

def _is_fy_segment(seg: str) -> bool:
    """'2025-26', '25-26', '2526', '2025-2026': a financial-year fragment (second year = first + 1)."""
    m = re.fullmatch(r"(?:20)?(\d{2})-?(?:20)?(\d{2})", seg)
    return bool(m) and 15 <= int(m.group(1)) <= 60 and int(m.group(1)) + 1 == int(m.group(2))


def normalize_invoice_no(value: str | None) -> str | None:
    """INV/001, INV-001, 'inv 0001' -> INV1. FY fragments like 2025-26 / 25-26 are dropped only when
    they are a separate segment. The original is always kept elsewhere."""
    if not value:
        return None
    parts = [p for p in re.split(r"[\s/_.\\#]+", value.strip().upper()) if p]
    if len(parts) > 1:
        kept = [p for p in parts if not _is_fy_segment(p)]
        # do not strip everything: a purely numeric invoice no. stays as it is
        parts = kept or parts
    joined = "".join(parts).replace("-", "")
    m = re.match(r"^(.*?)(\d+)$", joined)
    if m:
        joined = m.group(1) + str(int(m.group(2)))
    return joined or None


_DATE_FORMATS = ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y",
                 "%d %B %Y", "%b %d, %Y", "%d-%m-%y", "%d/%m/%y", "%d-%b-%y")


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    v = re.sub(r"\s+", " ", value.strip().rstrip(".,"))
    # '6.Oct-26' / '16 Oct 26' / '16-Oct.26' -> '6-Oct-26'
    v = re.sub(r"^(\d{1,2})[ .-]?([A-Za-z]{3,9})[ .,-]+(\d{2,4})$", r"\1-\2-\3", v)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    return None
