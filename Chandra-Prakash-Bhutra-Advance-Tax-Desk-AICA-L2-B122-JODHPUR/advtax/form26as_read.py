"""Read the TDS / TCS credit out of a Form 26AS file (PDF or text from TRACES).

Form 26AS on TRACES now carries only TDS and TCS. Advance tax and
self-assessment tax challans are shown in the AIS, not here, so this reader
fills only the TDS / TCS figure.

It works on the one thing every 26AS layout has in common: a summary line per
deductor or collector that carries the TAN followed by three amounts (amount
paid or credited, tax deducted, tax deposited). The lines are shown to the user
for review before the total is used.

Not read: entries identified by a PAN instead of a TAN, such as TDS on purchase
of property or on rent deducted by an individual. Add those by hand.
"""
from __future__ import annotations

import io
import re

TAN = re.compile(r"(?<![A-Z0-9])([A-Z]{4}[0-9]{5}[A-Z])(?![A-Z0-9])")
PAN = re.compile(r"(?<![A-Z0-9])([A-Z]{5}[0-9]{4}[A-Z])(?![A-Z0-9])")
AMOUNT = re.compile(r"-?\d[\d,]*\.\d{2}(?!\d)")
YEAR = re.compile(r"(?:Assessment|Tax)\s+Year\D{0,12}(\d{4}\s*-\s*\d{2,4})", re.I)


def extract_text(data: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError("PDF reading is not installed. Start the app again with 'Start Advance Tax Desk.bat'.") from exc
        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise ValueError("This PDF is password-protected. Open it, save an unprotected copy and try again.")
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001 - any damaged or unusual PDF
            raise ValueError(f"Could not read this PDF ({exc.__class__.__name__}).") from exc
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def _num(text: str) -> float:
    return float(text.replace(",", ""))


def parse(text: str) -> dict:
    """Deductor-wise rows and totals from the text of a 26AS."""
    rows, kind, loose = [], "TDS", 0
    for line in text.splitlines():
        low = line.lower()
        if "part" in low and ("collected at source" in low or "tcs" in low):
            kind = "TCS"
        elif "part" in low and ("deducted at source" in low or "tds" in low):
            kind = "TDS"
        m = TAN.search(line)
        if not m:
            continue
        amounts = AMOUNT.findall(line[m.end():])
        if len(amounts) < 3:
            loose += 1
            continue
        name = re.sub(r"^[\s^|]*\d*[\s^|.]*", "", line[:m.start()]).replace("^", " ").strip(" |-")
        paid, deducted, deposited = (_num(a) for a in amounts[-3:])
        rows.append({"name": re.sub(r"\s+", " ", name) or "(name not read)", "tan": m.group(1), "kind": kind,
                     "amount_paid": paid, "tax_deducted": deducted, "tax_deposited": deposited})
    pan = PAN.search(text)
    year = YEAR.search(text)
    return {"rows": rows, "pan": pan.group(1) if pan else "",
            "year": re.sub(r"\s+", "", year.group(1)) if year else "",
            "total_deducted": round(sum(r["tax_deducted"] for r in rows)),
            "total_deposited": round(sum(r["tax_deposited"] for r in rows)),
            "lines_not_read": loose}


def read(data: bytes, filename: str) -> dict:
    return parse(extract_text(data, filename))
