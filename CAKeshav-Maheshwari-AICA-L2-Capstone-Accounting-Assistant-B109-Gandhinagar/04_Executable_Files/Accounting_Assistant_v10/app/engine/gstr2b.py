"""GSTR-2B (JSON from the portal, or the portal Excel) matched against invoices in the app.
Flag only: posting is never blocked by 2B status."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ..extract.parser import parse_date


@dataclass
class B2BRecord:
    gstin: str
    trade_name: str
    inv_no: str
    inv_date: str            # YYYYMMDD
    value: Decimal
    taxable: Decimal
    igst: Decimal
    cgst: Decimal
    sgst: Decimal
    cess: Decimal
    rcm: bool = False
    kind: str = "B2B"        # B2B | CDNR
    itc_available: str = ""


def norm_no(s: str) -> str:
    """Invoice number key: uppercase alphanumerics, leading zeros dropped from each digit run."""
    s = re.sub(r"[^A-Z0-9]", "", (s or "").upper())
    return re.sub(r"0+(\d)", r"\1", s)


def _d(v) -> Decimal:
    try:
        return Decimal(str(v).replace(",", "")) if v not in (None, "") else Decimal(0)
    except Exception:
        return Decimal(0)


def load(path: Path) -> list[B2BRecord]:
    path = Path(path)
    if path.suffix.lower() == ".json":
        return _load_json(json.loads(path.read_text(encoding="utf-8")))
    return _load_excel(path)


def _load_json(data: dict) -> list[B2BRecord]:
    doc = data.get("data", data).get("docdata", data.get("docdata", {}))
    out = []
    for sup in doc.get("b2b", []):
        for inv in sup.get("inv", []):
            items = inv.get("items", []) or [inv]
            out.append(B2BRecord(sup.get("ctin", ""), sup.get("trdnm", ""), inv.get("inum", ""),
                                 parse_date(inv.get("dt", "")), _d(inv.get("val")),
                                 sum((_d(i.get("txval")) for i in items), Decimal(0)),
                                 sum((_d(i.get("igst")) for i in items), Decimal(0)),
                                 sum((_d(i.get("cgst")) for i in items), Decimal(0)),
                                 sum((_d(i.get("sgst")) for i in items), Decimal(0)),
                                 sum((_d(i.get("cess")) for i in items), Decimal(0)),
                                 inv.get("rev", "N") == "Y", "B2B", inv.get("itcavl", "")))
    for sup in doc.get("cdnr", []):
        for nt in sup.get("nt", []):
            items = nt.get("items", []) or [nt]
            sign = -1 if nt.get("typ", "C") == "C" else 1
            out.append(B2BRecord(sup.get("ctin", ""), sup.get("trdnm", ""), nt.get("ntnum", ""),
                                 parse_date(nt.get("dt", "")), sign * _d(nt.get("val")),
                                 sign * sum((_d(i.get("txval")) for i in items), Decimal(0)),
                                 sign * sum((_d(i.get("igst")) for i in items), Decimal(0)),
                                 sign * sum((_d(i.get("cgst")) for i in items), Decimal(0)),
                                 sign * sum((_d(i.get("sgst")) for i in items), Decimal(0)),
                                 sign * sum((_d(i.get("cess")) for i in items), Decimal(0)),
                                 nt.get("rev", "N") == "Y", "CDNR", nt.get("itcavl", "")))
    return out


def _load_excel(path: Path) -> list[B2BRecord]:
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True, read_only=True)
    ws = next((w for w in wb.worksheets if w.title.strip().upper() == "B2B"), wb.worksheets[0])
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    hdr_i = next(i for i, r in enumerate(rows) if any(isinstance(c, str) and "GSTIN of supplier" in c for c in r))
    # portal sheets use a two-row header: merge them
    h1 = [str(c or "").strip() for c in rows[hdr_i]]
    h2 = [str(c or "").strip() for c in rows[hdr_i + 1]] if hdr_i + 1 < len(rows) else [""] * len(h1)
    headers = [(b or a).lower() for a, b in zip(h1, h2)]

    def col(*names):
        for n in names:
            for i, h in enumerate(headers):
                if n in h:
                    return i
        return None
    c = {k: col(*v) for k, v in {
        "gstin": ("gstin of supplier",), "name": ("trade/legal name", "trade", "legal name"),
        "no": ("invoice number", "note number"), "date": ("invoice date", "note date"),
        "value": ("invoice value", "note value"), "taxable": ("taxable value",), "igst": ("integrated tax",),
        "cgst": ("central tax",), "sgst": ("state/ut tax", "state tax"), "cess": ("cess",),
        "rcm": ("reverse charge",), "itc": ("itc availability",)}.items()}
    start = hdr_i + (2 if any(h2) else 1)
    out = []
    for r in rows[start:]:
        g = r[c["gstin"]] if c["gstin"] is not None else None
        if not g or not re.match(r"\d{2}[A-Z]{5}", str(g)):
            continue
        get = lambda k: r[c[k]] if c.get(k) is not None and c[k] < len(r) else None
        d = get("date")
        d = d.strftime("%Y%m%d") if hasattr(d, "strftime") else parse_date(str(d or ""))
        out.append(B2BRecord(str(g).strip(), str(get("name") or ""), str(get("no") or ""), d, _d(get("value")),
                             _d(get("taxable")), _d(get("igst")), _d(get("cgst")), _d(get("sgst")), _d(get("cess")),
                             str(get("rcm") or "").upper().startswith("Y"), "B2B", str(get("itc") or "")))
    return out


@dataclass
class Match:
    status: str                  # matched | amount_mismatch | not_in_2b | in_2b_not_booked
    gstin: str
    inv_no: str
    book_total: Decimal | None
    b2b_total: Decimal | None
    note: str = ""
    invoice_id: str = ""


def reconcile(invoices: list[dict], records: list[B2BRecord], tol: Decimal = Decimal("1")) -> list[Match]:
    """invoices: [{'id','supplier_gstin','invoice_no','grand_total','tax_total'}] from the app."""
    by_key = {(r.gstin, norm_no(r.inv_no)): r for r in records}
    used = set()
    out = []
    for inv in invoices:
        key = (inv["supplier_gstin"], norm_no(inv["invoice_no"]))
        r = by_key.get(key)
        if not r:
            out.append(Match("not_in_2b", key[0], inv["invoice_no"], Decimal(inv["grand_total"]), None,
                             "Supplier hasn't filed it in GSTR-1/IFF yet, or number differs", inv["id"]))
            continue
        used.add(key)
        book_tax = Decimal(str(inv.get("tax_total", 0)))
        b_tax = r.igst + r.cgst + r.sgst + r.cess
        diff_val = Decimal(str(inv["grand_total"])) - r.value
        if abs(diff_val) <= tol and abs(book_tax - b_tax) <= tol:
            out.append(Match("matched", key[0], inv["invoice_no"], Decimal(inv["grand_total"]), r.value, "",
                             inv["id"]))
        else:
            out.append(Match("amount_mismatch", key[0], inv["invoice_no"], Decimal(inv["grand_total"]), r.value,
                             f"Value diff {diff_val}, tax diff {book_tax - b_tax}", inv["id"]))
    for key, r in by_key.items():
        if key not in used:
            out.append(Match("in_2b_not_booked", r.gstin, r.inv_no, None, r.value,
                             f"{r.trade_name} {r.inv_date}" + (" (RCM)" if r.rcm else "")))
    return out
