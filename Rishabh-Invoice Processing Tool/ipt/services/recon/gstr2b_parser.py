"""Read a GSTR-2B file downloaded from the GST portal: the Excel workbook or the JSON file.

Excel: one sheet per table (B2B, B2BA, B2B-CDNR, B2B-CDNRA, ISD, ISDA, IMPG, IMPGSEZ). Header rows are
found by their text, not by fixed positions, and two-row headers ('Invoice details' over 'Invoice
number') are combined, so small layout changes on the portal do not break the import. Sheets that are
not document tables (Read me, ITC summary ...) are skipped and listed.

JSON: data -> (data ->) docdata -> b2b / b2ba / cdnr / cdnra / isd / isda / impg / impgsez. Both the
older layout (tax amounts in items[]) and the newer one (amounts on the document) are read.

Nothing is guessed: a row without a document number is skipped and reported; amounts that cannot be
read are left empty.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ipt.core.textnorm import normalize_invoice_no, parse_date

SECTIONS = ("B2B", "B2BA", "CDNR", "CDNRA", "ISD", "ISDA", "IMPG", "IMPGSEZ")
MONTHS = {m: i for i, m in enumerate(("january february march april may june july august september october "
                                      "november december").split(), 1)}


@dataclass
class Parsed2B:
    period: str | None = None          # YYYY-MM
    gstin: str = ""
    gstin_raw: str = ""            # what the file prints next to 'GSTIN', even if it is not a valid GSTIN
    records: list[dict] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    source_format: str = ""

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.records:
            out[r["section"]] = out.get(r["section"], 0) + 1
        return out


class Gstr2bFormatError(ValueError):
    pass


# ----------------------------------------------------------------------------- helpers
def _money(v) -> Decimal | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float, Decimal)):
        return Decimal(str(v)).quantize(Decimal("0.01"))
    s = re.sub(r"[₹,\s]", "", str(v))
    if s in ("", "-"):
        return None
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _date(v) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return parse_date(str(v).strip())


def _yes(v) -> bool:
    return str(v or "").strip().upper() in ("Y", "YES", "TRUE")


def _itc(v) -> str:
    s = str(v or "").strip().upper()
    return {"Y": "Yes", "YES": "Yes", "N": "No", "NO": "No", "T": "Temporary", "TEMPORARY": "Temporary"}.get(s, s.title())


def _record(section: str, **kw) -> dict:
    rec = {"section": section, "supplier_gstin": "", "supplier_name": "", "doc_type": "INV", "doc_no": "",
           "doc_date": None, "original_doc_no": "", "original_doc_date": None, "pos": "", "reverse_charge": False,
           "invoice_value": None, "taxable_value": None, "igst": None, "cgst": None, "sgst": None, "cess": None,
           "itc_available": "", "itc_reason": "", "supplier_period": "", "supplier_filing_date": None, "row_ref": ""}
    rec.update(kw)
    rec["supplier_gstin"] = (rec["supplier_gstin"] or "").strip().upper()
    rec["doc_no"] = str(rec["doc_no"] or "").strip()
    rec["original_doc_no"] = str(rec["original_doc_no"] or "").strip()
    rec["doc_no_normalized"] = normalize_invoice_no(rec["doc_no"]) or ""
    return rec


def _period_from_mmyyyy(s: str | None) -> str | None:
    s = re.sub(r"\D", "", str(s or ""))
    if len(s) == 6 and 1 <= int(s[:2]) <= 12:
        return f"{s[2:]}-{s[:2]}"
    return None


# ----------------------------------------------------------------------------- JSON
def _find_docdata(obj):
    if isinstance(obj, dict):
        if "docdata" in obj:
            return obj
        for v in obj.values():
            found = _find_docdata(v)
            if found is not None:
                return found
    return None


def _sum_items(doc: dict) -> dict:
    """Tax amounts of a document: on the document itself, or summed over items[] / itms[]."""
    keys = ("txval", "igst", "cgst", "sgst", "cess")
    items = doc.get("items") or doc.get("itms")
    if items:
        tot = {k: None for k in keys}
        for it in items:
            src = it.get("itm_det", it)
            for k in keys:
                v = _money(src.get(k))
                if v is not None:
                    tot[k] = (tot[k] or Decimal("0.00")) + v
        return tot
    return {k: _money(doc.get(k)) for k in keys}


def parse_json(raw: bytes | str) -> Parsed2B:
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError) as e:
        raise Gstr2bFormatError(f"Not a valid JSON file: {e}") from e
    payload = _find_docdata(obj)
    if payload is None:
        raise Gstr2bFormatError("This JSON has no 'docdata' - it does not look like a GSTR-2B file")
    out = Parsed2B(period=_period_from_mmyyyy(payload.get("rtnprd")), gstin=str(payload.get("gstin") or ""),
                   source_format="json")
    dd = payload["docdata"] or {}
    for key, val in dd.items():
        sec = key.upper()
        if sec not in SECTIONS:
            out.skipped.append(f"Table '{key}' is not read by IPT ({len(val or [])} entries)")
            continue
        for si, sup in enumerate(val or []):
            if sec in ("IMPG",):
                docs, base = [sup], {}
            else:
                base = {"supplier_gstin": sup.get("ctin", ""), "supplier_name": sup.get("trdnm", ""),
                        "supplier_period": str(sup.get("supprd") or ""),
                        "supplier_filing_date": _date(sup.get("supfildt"))}
                docs = (sup.get("inv") or sup.get("nt") or sup.get("doclist") or sup.get("boe") or [])
            for di, d in enumerate(docs):
                amt = _sum_items(d)
                common = dict(base, invoice_value=_money(d.get("val")), taxable_value=amt["txval"],
                              igst=amt["igst"], cgst=amt["cgst"], sgst=amt["sgst"], cess=amt["cess"],
                              pos=str(d.get("pos") or ""), reverse_charge=_yes(d.get("rev")),
                              itc_available=_itc(d.get("itcavl") or d.get("itcelg")), itc_reason=str(d.get("rsn") or ""),
                              row_ref=f"{key}[{si}][{di}]")
                if sec in ("B2B", "B2BA"):
                    rec = _record(sec, doc_type="INV", doc_no=d.get("inum"), doc_date=_date(d.get("dt")),
                                  original_doc_no=d.get("oinum", ""), original_doc_date=_date(d.get("oidt")), **common)
                elif sec in ("CDNR", "CDNRA"):
                    typ = str(d.get("typ") or d.get("ntty") or "").upper()[:1]
                    rec = _record(sec, doc_type="DBN" if typ == "D" else "CRN", doc_no=d.get("ntnum") or d.get("nt_num"),
                                  doc_date=_date(d.get("dt") or d.get("nt_dt")),
                                  original_doc_no=d.get("ontnum", ""), original_doc_date=_date(d.get("ontdt")),
                                  **common)
                elif sec in ("ISD", "ISDA"):
                    rec = _record(sec, doc_type="ISD", doc_no=d.get("docnum"), doc_date=_date(d.get("docdt")),
                                  original_doc_no=d.get("odocnum", "") or d.get("oinvnum", ""),
                                  original_doc_date=_date(d.get("odocdt") or d.get("oinvdt")), **common)
                else:   # IMPG / IMPGSEZ: bill of entry
                    rec = _record(sec, doc_type="BOE", doc_no=d.get("boenum"), doc_date=_date(d.get("boedt")),
                                  **common)
                if not rec["doc_no"]:
                    out.skipped.append(f"{sec}: entry {si + 1}/{di + 1} has no document number")
                    continue
                out.records.append(rec)
    return out


# ----------------------------------------------------------------------------- Excel
SHEET_SECTIONS = {"B2B": "B2B", "B2BA": "B2BA", "B2BCDNR": "CDNR", "CDNR": "CDNR", "B2BCDNRA": "CDNRA",
                  "B2BDNR": "CDNR", "B2BDNRA": "CDNRA",           # IMS-era debit-note sheets
                  "CDNRA": "CDNRA", "ISD": "ISD", "ISDA": "ISDA", "IMPG": "IMPG", "IMPGSEZ": "IMPGSEZ"}

# (field, must contain any, must not contain any) - checked in order, first match wins per column
COLUMN_RULES = [
    ("supplier_gstin", ("gstin of supplier", "gstin of isd", "gstin"), ("recipient",)),
    ("supplier_name", ("trade/legal name", "trade name", "legal name", "name of"), ()),
    ("original_doc_no", ("original invoice number", "original note number", "original document number",
                         "original bill of entry number"), ()),
    ("original_doc_date", ("original invoice date", "original note date", "original document date"), ()),
    ("doc_type_text", ("note type", "document type"), ("original",)),
    ("doc_no", ("invoice number", "note number", "document number", "bill of entry number"), ("original",)),
    ("doc_date", ("invoice date", "note date", "document date", "bill of entry date"), ("original",)),
    ("invoice_value", ("invoice value", "note value", "document value"), ()),
    ("pos", ("place of supply",), ()),
    ("reverse_charge", ("reverse charge",), ()),
    ("taxable_value", ("taxable value",), ()),
    ("igst", ("integrated tax",), ()),
    ("cgst", ("central tax",), ()),
    ("sgst", ("state/ut tax", "state tax", "state / ut tax"), ()),
    ("cess", ("cess",), ()),
    ("supplier_filing_date", ("filing date",), ()),
    ("supplier_period", ("period",), ("filing",)),
    ("itc_available", ("itc availability", "eligibility of itc", "itc available"), ()),
    ("itc_reason", ("reason",), ()),
]


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").replace("\n", " ")).strip().lower()


def _header_labels(rows: list[tuple], h: int) -> tuple[list[str], int]:
    """Labels for the header starting at row h (one or two rows). Returns (labels, first data row)."""
    top = list(rows[h])
    sub = list(rows[h + 1]) if h + 1 < len(rows) else []
    sub_is_header = sum(1 for v in sub if isinstance(v, str) and re.search(
        r"number|date|value|tax|type|name|gstin|cess", v, re.I)) >= 2
    width = max(len(top), len(sub))
    labels, parent = [], ""
    for c in range(width):
        t = top[c] if c < len(top) else None
        if t not in (None, ""):
            parent = str(t)
        s = sub[c] if sub_is_header and c < len(sub) else None
        if s not in (None, ""):
            labels.append(_norm(f"{parent} {s}") if t in (None, "") else _norm(f"{t} {s}"))
        else:
            labels.append(_norm(t if t not in (None, "") else (parent if sub_is_header else "")))
    return labels, h + (2 if sub_is_header else 1)


def _map_columns(labels: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for c, lab in enumerate(labels):
        if not lab:
            continue
        for fld, any_of, none_of in COLUMN_RULES:
            if fld in out:
                continue
            if any(a in lab for a in any_of) and not any(n in lab for n in none_of):
                out[fld] = c
                break
    return out


def _period_from_sheet(rows: list[tuple]) -> str | None:
    fy, month = None, None
    for row in rows[:15]:
        cells = [str(v) for v in row if v not in (None, "")]
        line = " ".join(cells).lower()
        m = re.search(r"financial year\s*[:\-]?\s*(20\d{2})\s*-\s*(\d{2,4})", line)
        if m:
            fy = int(m.group(1))
        m = re.search(r"tax period\s*[:\-]?\s*([a-z]+)", line)
        if m and m.group(1) in MONTHS:
            month = MONTHS[m.group(1)]
    if fy and month:
        year = fy if month >= 4 else fy + 1
        return f"{year}-{month:02d}"
    return None


def parse_excel(path: Path) -> Parsed2B:
    try:
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:  # noqa: BLE001 - any unreadable workbook
        raise Gstr2bFormatError(f"Could not open the Excel file: {e}") from e
    out = Parsed2B(source_format="excel")
    try:
        for ws in wb.worksheets:
            rows = [tuple(r) for r in ws.iter_rows(values_only=True)]
            out.period = out.period or _period_from_sheet(rows)
            if not out.gstin_raw:
                for row in rows[:15]:
                    cells = [str(v).strip() for v in row if v not in (None, "")]
                    if len(cells) >= 2 and cells[0].strip().upper() in ("GSTIN", "GSTIN OF THE TAXPAYER", "GSTIN:"):
                        out.gstin_raw = cells[1].upper()
                        break
            if not out.gstin:
                for row in rows[:15]:
                    for v in row:
                        m = re.search(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b", str(v or ""))
                        if m and "gstin" in " ".join(str(x or "") for x in row).lower():
                            out.gstin = m.group(1)
            key = re.sub(r"[^A-Z0-9]", "", ws.title.upper())
            sec = SHEET_SECTIONS.get(key)
            if sec is None:
                out.skipped.append(f"Sheet '{ws.title}' is not a document table - not read")
                continue
            h = next((i for i, r in enumerate(rows[:20]) if any(
                re.search(r"gstin of (supplier|isd)|invoice number|note number|bill of entry number|document number",
                          _norm(v)) for v in r)), None)
            if h is None:
                out.skipped.append(f"Sheet '{ws.title}': header row not found - not read")
                continue
            labels, start = _header_labels(rows, h)
            cols = _map_columns(labels)
            if "doc_no" not in cols:
                out.skipped.append(f"Sheet '{ws.title}': no document number column - not read")
                continue

            def get(row, fld):
                c = cols.get(fld)
                return row[c] if c is not None and c < len(row) else None

            for i, row in enumerate(rows[start:], start=start + 1):
                if not any(v not in (None, "") for v in row):
                    continue
                doc_no = get(row, "doc_no")
                if doc_no in (None, ""):
                    first = _norm(row[0] if row else "")
                    if not first.startswith("total"):
                        out.skipped.append(f"Sheet '{ws.title}' row {i}: no document number")
                    continue
                if sec in ("CDNR", "CDNRA"):
                    t = _norm(get(row, "doc_type_text"))
                    doc_type = "DBN" if t.startswith("d") else "CRN"
                elif sec in ("ISD", "ISDA"):
                    doc_type = "ISD"
                elif sec in ("IMPG", "IMPGSEZ"):
                    doc_type = "BOE"
                else:
                    doc_type = "INV"
                pos = re.match(r"\s*(\d{2})", str(get(row, "pos") or ""))
                out.records.append(_record(
                    sec, supplier_gstin=str(get(row, "supplier_gstin") or ""),
                    supplier_name=str(get(row, "supplier_name") or ""), doc_type=doc_type,
                    doc_no=str(doc_no).strip(), doc_date=_date(get(row, "doc_date")),
                    original_doc_no=str(get(row, "original_doc_no") or ""),
                    original_doc_date=_date(get(row, "original_doc_date")),
                    pos=pos.group(1) if pos else _state_code_from_name(get(row, "pos")),
                    reverse_charge=_yes(get(row, "reverse_charge")),
                    invoice_value=_money(get(row, "invoice_value")), taxable_value=_money(get(row, "taxable_value")),
                    igst=_money(get(row, "igst")), cgst=_money(get(row, "cgst")), sgst=_money(get(row, "sgst")),
                    cess=_money(get(row, "cess")), itc_available=_itc(get(row, "itc_available")),
                    itc_reason=str(get(row, "itc_reason") or ""), supplier_period=str(get(row, "supplier_period") or ""),
                    supplier_filing_date=_date(get(row, "supplier_filing_date")), row_ref=f"{ws.title}!{i}"))
    finally:
        wb.close()
    if not out.records and not any("row" in s for s in out.skipped):
        raise Gstr2bFormatError("No GSTR-2B tables (B2B, B2B-CDNR ...) were found in this workbook")
    return out


def _state_code_from_name(name) -> str:
    from ipt.core.states import STATES
    n = _norm(name)
    for code, st in STATES.items():
        if _norm(getattr(st, "name", st)) == n:
            return code
    return ""


def parse_file(path: Path) -> Parsed2B:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return parse_json(path.read_bytes())
    if suffix in (".xlsx", ".xlsm"):
        return parse_excel(path)
    if suffix == ".zip":
        import zipfile
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".json")]
            if not names:
                raise Gstr2bFormatError("The ZIP file has no JSON inside")
            return parse_json(z.read(names[0]))
    raise Gstr2bFormatError("Choose the GSTR-2B Excel (.xlsx) or JSON (.json / .zip) downloaded from the portal")
