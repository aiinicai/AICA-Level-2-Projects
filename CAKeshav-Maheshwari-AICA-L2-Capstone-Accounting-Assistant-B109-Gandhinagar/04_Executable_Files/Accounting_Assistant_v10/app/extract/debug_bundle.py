"""'Export for Claude': a text file describing how one invoice was read, safe to share.

Kept: layout (spacing, line order), labels, amounts, dates, tax rates, HSN codes, what each step produced.
Masked: party names, GSTINs (state code kept), PAN, bank/IFSC/UPI/Aadhaar, phone numbers, e-mails, PIN codes,
addresses' house numbers - every long digit run that is not money-shaped.
The user reviews the file before sending it.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from .redact import mask_text

_MONEY = re.compile(r"^-?(?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2}$|^-?\d{1,3}(?:,\d{2,3})+$")
_DATE = re.compile(r"^\d{1,2}[/\-.](?:\d{1,2}|[A-Za-z]{3,9})[/\-.]\d{2,4}$")
_GSTIN = re.compile(r"\b(\d{2})[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")


def _mask_gstin(m: re.Match) -> str:
    return f"{m.group(1)}XXXXX0000X1ZX"


def mask_identity(text: str, names: list[str]) -> str:
    text, _ = mask_text(text)
    text = _GSTIN.sub(_mask_gstin, text)
    text = _EMAIL.sub("[EMAIL]", text)
    for i, n in enumerate(sorted({n.strip() for n in names if n and len(n.strip()) > 2}, key=len, reverse=True)):
        text = re.sub(re.escape(n), f"[PARTY{i + 1}]", text, flags=re.I)

    def tok(m: re.Match) -> str:
        t = m.group(0)
        if _MONEY.match(t) or _DATE.match(t) or re.fullmatch(r"\d{1,2}(\.\d+)?%?", t):
            return t
        digits = sum(c.isdigit() for c in t)
        if digits >= 5 and not re.fullmatch(r"\d{4}|\d{6}|\d{8}", t):
            return re.sub(r"\d", "9", t)            # phones, accounts, service numbers
        if re.fullmatch(r"\d{6}", t):
            return "999999"                         # PIN code (also some HSN - acceptable)
        return t
    return re.sub(r"[\w,./-]*\d[\w,./-]*", tok, text)


def export(row, company, out_dir: Path) -> Path:
    e = row.extraction or {}
    names = [company.name, e.get("supplier_name", "")] + [w for w in (company.name or "").split() if len(w) > 3]
    text = mask_identity(e.get("_text", ""), names)
    fields = {k: v for k, v in e.items() if not k.startswith("_")}
    for k in ("supplier_name", "buyer_name"):
        if fields.get(k):
            fields[k] = "[PARTY]"
    for k in ("supplier_gstin", "buyer_gstin"):
        if fields.get(k):
            fields[k] = _GSTIN.sub(_mask_gstin, fields[k])
    fields.pop("supplier_pan", None)
    fields.pop("irn", None)
    trail = [mask_identity(t, names) for t in e.get("_trail", [])]
    issues = (row.validation or {}).get("issues", [])
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"invoice_debug_{datetime.now():%Y%m%d_%H%M%S}.txt"
    parts = [
        "ACCOUNTING ASSISTANT - INVOICE DEBUG BUNDLE (identities masked; review before sharing)",
        f"File type: {Path(row.file_path).suffix.lower()}   Read by: {row.extraction_source}   "
        f"Status: {(row.validation or {}).get('status')}",
        "", "== HOW IT WAS READ ==", *trail,
        "", "== ISSUES ==", *[f"[{i['level']}] {mask_identity(i['message'], names)}" for i in issues],
        "", "== EXTRACTED FIELDS ==", json.dumps(fields, indent=1, ensure_ascii=False),
        "", "== WHAT THE CORRECT VALUES SHOULD BE (fill in) ==",
        "taxable_total: ", "cgst/sgst/igst: ", "grand_total: ", "invoice_no / date: ", "other: ",
        "", "== DOCUMENT TEXT (layout kept, identities masked) ==", text,
    ]
    out.write_text("\n".join(parts), encoding="utf-8")
    return out
