"""Excel / CSV reader with automatic structure detection and manual column mapping."""
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from . import ReadResult
from ..gstin import state_of
from ..models import Line
from ..utils import D, parse_date, state_from_text, snap_rate, parse_rates, ZERO

FIELD_LABELS = {
    "invoice_no": "Invoice number", "invoice_date": "Invoice date",
    "recipient_gstin": "Recipient GSTIN", "recipient_name": "Recipient name",
    "pos": "Place of supply", "hsn": "HSN/SAC", "description": "Description",
    "qty": "Quantity", "uqc": "Unit (UQC)", "rate": "GST rate %", "taxable": "Taxable value",
    "igst": "IGST", "cgst": "CGST", "sgst": "SGST/UTGST", "cess": "Cess",
    "invoice_total": "Invoice total", "reverse_charge": "Reverse charge",
    "invoice_type": "Invoice type", "note_type": "Note type (Credit/Debit)",
    "orig_invoice_no": "Original invoice no.", "orig_invoice_date": "Original invoice date",
    "ecom_gstin": "E-commerce GSTIN",
    "nil_kind": "Nil / Exempt / Non-GST kind", "export_type": "Export type (WPAY/WOPAY)",
    "port_code": "Port code", "ship_bill_no": "Shipping bill no.", "ship_bill_date": "Shipping bill date",
}

SYNONYMS = {
    "invoice_no": ["invoice no", "invoice number", "inv no", "invoice", "bill no", "bill number",
                   "voucher no", "voucher number", "vch no", "doc no", "document no", "document number",
                   "invoice no.", "inv number", "inv. no", "tax invoice no"],
    "invoice_date": ["invoice date", "inv date", "bill date", "voucher date", "doc date", "document date",
                     "date", "inv. date"],
    "recipient_gstin": ["gstin", "gstin/uin", "customer gstin", "buyer gstin", "party gstin", "gst no",
                        "gstin of recipient", "gstin/uin of recipient", "recipient gstin", "gst number",
                        "gstin no", "customer gst no", "party gst no"],
    "recipient_name": ["customer name", "party name", "buyer name", "particulars", "name of customer",
                       "receiver name", "recipient name", "customer", "party", "name", "buyer"],
    "pos": ["place of supply", "pos", "state", "supply state", "state of supply"],
    "hsn": ["hsn", "hsn/sac", "hsn code", "sac", "hsn no", "sac code", "hsn/sac code", "hsn sac"],
    "description": ["description", "item description", "item name", "item", "product", "product name",
                    "particulars of goods", "goods description"],
    "qty": ["qty", "quantity", "total quantity", "qty."],
    "uqc": ["uom", "unit", "uqc", "unit of measure", "unit of measurement"],
    "rate": ["gst rate", "tax rate", "rate", "gst %", "rate %", "tax %", "gst rate %", "rate of tax",
             "gst rate(%)", "igst rate"],
    "taxable": ["taxable value", "taxable amount", "taxable", "assessable value", "basic amount",
                "taxable amt", "net amount", "amount before tax", "basic value"],
    "igst": ["igst", "igst amount", "integrated tax", "igst amt", "integrated tax amount"],
    "cgst": ["cgst", "cgst amount", "central tax", "cgst amt", "central tax amount"],
    "sgst": ["sgst", "sgst amount", "state tax", "sgst amt", "utgst", "sgst/utgst", "state/ut tax",
             "state/ut tax amount", "sgst/utgst amount"],
    "cess": ["cess", "cess amount", "cess amt"],
    "invoice_total": ["invoice value", "invoice total", "total", "gross total", "bill amount",
                      "total amount", "grand total", "invoice amount", "net total", "total invoice value"],
    "reverse_charge": ["reverse charge", "rcm", "reverse charge applicable"],
    "invoice_type": ["invoice type", "supply type", "type of supply"],
    "note_type": ["note type", "document type", "doc type", "voucher type", "note/refund voucher type"],
    "orig_invoice_no": ["original invoice no", "original invoice number", "against invoice",
                        "original invoice"],
    "orig_invoice_date": ["original invoice date"],
    "ecom_gstin": ["e-commerce gstin", "ecommerce gstin", "ecom gstin"],
    "nil_kind": ["nil exempt non gst", "supply kind", "nil/exempt/non-gst", "exempt type", "nil kind"],
    "export_type": ["export type", "wpay/wopay", "export with/without payment"],
    "port_code": ["port code", "port"],
    "ship_bill_no": ["shipping bill no", "shipping bill number", "sb no", "shipping bill"],
    "ship_bill_date": ["shipping bill date", "sb date"],
}

REQUIRED_FOR_DETECT = ("invoice_no", "taxable")


def _norm(h) -> str:
    s = str(h).lower().strip()
    s = re.sub(r"[^a-z0-9%/ .#]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def auto_map(headers) -> Dict[str, str]:
    """Return {field: original header}. Exact synonym match first, then first-found."""
    normed = [(_norm(h), h) for h in headers]
    mapping: Dict[str, str] = {}
    used = set()
    # pass 1: exact; longest synonyms listed first resolve ambiguity by order in SYNONYMS
    for fld, syns in SYNONYMS.items():
        for syn in syns:
            for n, orig in normed:
                if n == syn and orig not in used and fld not in mapping:
                    mapping[fld] = orig
                    used.add(orig)
    # pass 2: header startswith a long synonym (e.g. "Taxable Value (Rs)")
    for fld, syns in SYNONYMS.items():
        if fld in mapping:
            continue
        for syn in syns:
            if len(syn) < 6:
                continue
            for n, orig in normed:
                if orig not in used and n.startswith(syn):
                    mapping[fld] = orig
                    used.add(orig)
                    break
            if fld in mapping:
                break
    return mapping


def find_header_row(df: pd.DataFrame, scan: int = 20) -> int:
    best, best_score = 0, -1
    for i in range(min(scan, len(df))):
        vals = [v for v in df.iloc[i].tolist() if isinstance(v, str) and v.strip()]
        score = len(auto_map(vals))
        if score > best_score:
            best, best_score = i, score
    if best_score <= 0:                       # no known heading anywhere: take the row with the most filled cells
        counts = [sum(1 for v in df.iloc[i].tolist() if _clean(v) not in (None, "")) for i in range(min(scan, len(df)))]
        if counts:
            best = counts.index(max(counts))
    return best


def col_letter(i: int) -> str:
    s, i = "", i + 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def make_headers(values) -> List[str]:
    """Column names of a header row: the heading text, or 'Column C' for a blank cell; duplicates get a suffix."""
    out, seen = [], {}
    for i, h in enumerate(values):
        h = _clean(h)
        name = str(h).strip() if h not in (None, "") else f"Column {col_letter(i)}"
        seen[name] = seen.get(name, 0) + 1
        out.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
    return out


def preview_rows(df: pd.DataFrame, n: int = 15) -> List[List[str]]:
    return [["" if _clean(v) is None else str(v)[:40] for v in df.iloc[i].tolist()] for i in range(min(n, len(df)))]


def classify_structure(mapping: Dict[str, str]) -> str:
    if not all(k in mapping for k in REQUIRED_FOR_DETECT):
        return "unsupported"
    if "hsn" in mapping:
        return "item-level"
    return "sales-register"


def _clean(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def _note_type(v) -> str:
    s = str(v or "").strip().lower()
    if not s:
        return ""
    if "credit" in s or s in ("c", "cn", "cr"):
        return "C"
    if "debit" in s or s in ("d", "dn", "dr"):
        return "D"
    return ""


def _rc(v) -> str:
    s = str(v or "").strip().lower()
    return "Y" if s in ("y", "yes", "true", "1", "rcm") else "N"


def decode_invoice_type(text):
    """Free text -> (GSTR-1 invoice type, export type). Handles 'Export without payment', 'SEZ', 'B2B', 'Domestic' ..."""
    t = str(text or "").strip().lower()
    if not t:
        return "", ""
    without = any(w in t for w in ("without", "wopay", "w/o", "lut", "bond", "wop"))
    if "sez" in t:
        return ("SEZ supplies without payment" if without else "SEZ supplies with payment"), ""
    if "deemed" in t:
        return "Deemed Exp", ""
    if "export" in t or t in ("exp", "wpay", "wopay"):
        return "Export", ("WOPAY" if without else "WPAY")
    if "intra" in t and "igst" in t:
        return "Intra-State supplies attracting IGST", ""
    if any(w in t for w in ("regular", "b2b", "b2c", "domestic", "local", "normal", "tax invoice", "taxable")):
        return "Regular", ""
    return "", ""


FIXED_FIELDS = ("invoice_type", "note_type", "reverse_charge", "nil_kind", "pos", "rate")


# ---------------------------------------------------------------------------
# One printed tax invoice per sheet (typical of a billing format kept in Excel)
# ---------------------------------------------------------------------------
_INV_NO_RE = re.compile(r"INVOICE\s*NO\.?\s*:?\s*([A-Za-z0-9/\-_.]+)", re.I)
_INV_DT_RE = re.compile(r"DATE\s*:?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})", re.I)
_GSTIN_RE = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z])\b")
_TAXLINE_RE = re.compile(r"^\s*(CGST|SGST|UTGST|IGST)\s*@?\s*([\d.]+)\s*%", re.I)


def _cells(df):
    out = []
    for r in range(df.shape[0]):
        for c in range(df.shape[1]):
            v = df.iat[r, c]
            if v is None or (isinstance(v, float) and v != v):
                continue
            if isinstance(v, str) and not v.strip():
                continue
            out.append((r, c, v))
    return out


def is_invoice_sheet(df) -> bool:
    txt = " ".join(str(v) for _, _, v in _cells(df.head(60)) if isinstance(v, str))
    return bool(re.search(r"TAX\s+INVOICE", txt, re.I) and _INV_NO_RE.search(txt) and _INV_DT_RE.search(txt)
                and re.search(r"HSN", txt, re.I) and re.search(r"Assessable|Taxable", txt, re.I))


def read_invoice_sheet(sheet, df, path, client, rates, next_id, res):
    """Reads one printed invoice (header block, item table, tax lines). Returns the number of lines added."""
    cells = _cells(df)
    texts = [(r, c, str(v)) for r, c, v in cells]
    blob = "\n".join(t for _, _, t in texts)
    m_no, m_dt = _INV_NO_RE.search(blob), _INV_DT_RE.search(blob)
    if re.search(r"CREDIT\s+NOTE|DEBIT\s+NOTE", blob[:800], re.I):
        res.messages.append(f"Sheet '{sheet}' looks like a credit/debit note - not read from this layout; use the Master Template")
        return 0
    inv_no = m_no.group(1).strip().rstrip(".") if m_no else ""
    inv_date = parse_date(m_dt.group(1).replace("/", ".").replace("-", ".")) if m_dt else None
    # supplier GSTIN = first GSTIN above the consignee block
    cons_r = next((r for r, c, t in texts if "CONSIGNEE" in t.upper()), None)
    sup = next((m.group(1) for r, c, t in texts if (cons_r is None or r < cons_r) for m in [_GSTIN_RE.search(t)] if m), "")
    if sup and sup != client["gstin"]:
        res.messages.append(f"Sheet '{sheet}': supplier GSTIN {sup} differs from the client's GSTIN {client['gstin']}")
    rec_gstin, rec_name, rec_state = "", "", ""
    if cons_r is not None:
        ctext = next(t for r, c, t in texts if r == cons_r and "CONSIGNEE" in t.upper())
        g = _GSTIN_RE.search(ctext)
        rec_gstin = g.group(1) if g else ""
        lines_ = [x.strip() for x in ctext.splitlines() if x.strip()]
        for i, x in enumerate(lines_):
            if x.lower().strip(" :,") == "to" and i + 1 < len(lines_):
                rec_name = re.sub(r"^M/s\.?\s*", "", lines_[i + 1], flags=re.I).strip()
                break
        sm = re.search(r"State\s*:\s*([A-Za-z ]+)", ctext)
        rec_state = sm.group(1).strip() if sm else ""
    # item table
    hdr = None
    for r, c, t in texts:
        if re.match(r"\s*HSN", t, re.I):
            hdr = r
            break
    if hdr is None or not inv_no:
        res.messages.append(f"Sheet '{sheet}': invoice number or item table not found")
        return 0
    cols = {}
    for r, c, t in texts:
        if r != hdr:
            continue
        tl = t.strip().lower()
        if tl.startswith("s.no") or tl == "sl no":
            cols["sno"] = c
        elif tl.startswith("description"):
            cols["desc"] = c
        elif tl.startswith("hsn"):
            cols["hsn"] = c
        elif tl.startswith("quantity") or tl == "qty":
            cols["qty"] = c
        elif tl.startswith("unit"):
            cols["uqc"] = c
        elif "rate" in tl:
            cols["rate"] = c
        elif "assessable" in tl or "taxable" in tl:
            cols["val"] = c
    if not {"hsn", "val"} <= set(cols):
        res.messages.append(f"Sheet '{sheet}': HSN / value columns not found in the item table")
        return 0
    end = next((r for r, c, t in texts if r > hdr and re.search(r"total\s+assessable|tax\s+amount\s*\(in words", t, re.I)), df.shape[0])
    items = []
    for r in range(hdr + 1, end):
        row = {k: (df.iat[r, c] if c < df.shape[1] else None) for k, c in cols.items()}
        val = D(row.get("val"))
        hsn = row.get("hsn")
        if not val or hsn is None or (isinstance(hsn, float) and hsn != hsn):
            continue
        items.append(row)
    # tax lines
    tax = {"CGST": ZERO, "SGST": ZERO, "UTGST": ZERO, "IGST": ZERO}
    rate = ZERO
    total_val = tot_inv = ZERO
    for r, c, t in texts:
        mt = _TAXLINE_RE.match(t)
        nums = [v for rr, cc, v in cells if rr == r and cc > c and isinstance(v, (int, float))]
        if mt and nums:
            tax[mt.group(1).upper()] += D(nums[-1])
            rr_ = D(mt.group(2))
            rate = rr_ * 2 if mt.group(1).upper() in ("CGST", "SGST", "UTGST") else rr_
        elif re.search(r"total\s+assessable", t, re.I) and nums:
            total_val = D(nums[-1])
        elif re.search(r"total\s+invoice\s+value", t, re.I) and nums:
            tot_inv = D(nums[-1])
    if not items:
        res.messages.append(f"Sheet '{sheet}': no item rows found")
        return 0
    if rate == ZERO and (tax["CGST"] or tax["IGST"]):
        rate = None
    sum_val = sum((D(i["val"]) for i in items), ZERO)
    inter = tax["IGST"] > 0
    pos = state_of(rec_gstin) if rec_gstin else (state_from_text(rec_state) if rec_state else "")
    added = 0
    for i, row in enumerate(items):
        l = Line(id=next_id + added, source_file=path.name, source_ref=f"{sheet}!item {i + 1}",
                 supplier_gstin=client["gstin"], supplier_name=client.get("legal_name") or client["name"])
        l.invoice_no, l.invoice_date = inv_no, inv_date
        l.recipient_gstin, l.recipient_name, l.pos = rec_gstin, rec_name, pos
        l.hsn = re.sub(r"\.0$", "", str(row["hsn"]).strip())
        l.description = str(row.get("desc") or "").strip()
        l.uqc = str(row.get("uqc") or "").strip().upper()
        l.qty = D(row.get("qty"))
        l.taxable = D(row["val"]).quantize(D("0.01"))
        if rate:
            l.rate = rate
            amt = (l.taxable * rate / D(100)).quantize(D("0.01"))
            if inter:
                l.igst = amt
            else:
                l.cgst = (amt / D(2)).quantize(D("0.01"))
                l.sgst = l.cgst
        else:
            l.rate = snap_rate(l.taxable, tax["CGST"] + tax["SGST"] + tax["IGST"], rates)
        l.invoice_total = tot_inv.quantize(D("0.01")) if tot_inv else ZERO
        l.confidence = 1.0
        notes = []
        if i == 0 and total_val and abs(total_val - sum_val) > D("1"):
            notes.append(f"Items add up to {sum_val} but the sheet shows total value {total_val} - check")
        if i == 0 and tot_inv and rate:
            calc = sum_val + sum_val * rate / D(100)
            if abs(calc - tot_inv) > D("1"):
                notes.append(f"Sheet total {tot_inv} differs from items + tax {calc.quantize(D('0.01'))} - check")
        l.note = "; ".join(notes)
        res.lines.append(l)
        added += 1
    return added


def read_workbook(path: Path, client: dict, settings: dict,
                  override: Optional[Dict[str, str]] = None) -> ReadResult:
    res = ReadResult()
    path = Path(path)
    try:
        if path.suffix.lower() in (".csv", ".txt"):
            sheets = {"CSV": pd.read_csv(path, header=None, dtype=object, keep_default_na=False)}
        else:
            sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=object)
    except Exception as e:  # noqa
        res.messages.append(f"Cannot open file: {e}")
        return res

    rates = parse_rates(settings.get("valid_rates", ""))
    override = dict(override) if override else None
    fixed = dict(override.pop("__fixed", {}) or {}) if override else {}
    forced_hdr = override.pop("__header_row", None) if override else None
    fixed = {k: str(v).strip() for k, v in fixed.items() if str(v).strip()}
    kinds = []
    next_id = 1
    for sheet, df in sheets.items():
        if df.empty:
            continue
        df = df.dropna(how="all").reset_index(drop=True)
        if df.empty:
            continue
        if not override and is_invoice_sheet(df):
            try:
                n = read_invoice_sheet(sheet, df, path, client, rates, next_id, res)
            except Exception as ex:  # noqa
                res.messages.append(f"Sheet '{sheet}': could not be read ({ex})")
                n = 0
            if n:
                next_id += n
                kinds.append("invoice-per-sheet")
            continue
        hdr = forced_hdr if isinstance(forced_hdr, int) and 0 <= forced_hdr < len(df) else find_header_row(df)
        top = " ".join(str(v).lower() for v in df.head(5).values.ravel() if isinstance(v, str))
        if "nature of document" in top and "total number" in top:
            res.messages.append(f"Sheet '{sheet}' is a document-series summary - not invoice data, so it is skipped. "
                                "its series are read into the Documents tab (Table 13) automatically")
            continue
        headers = make_headers(df.iloc[hdr].tolist())
        mapping = auto_map(headers)
        kind = classify_structure(mapping)
        if override:
            valid = {k: v for k, v in override.items() if v in headers}
            if all(k in valid for k in REQUIRED_FOR_DETECT):
                mapping, kind = valid, ("item-level" if "hsn" in valid else "sales-register")
        res.sheets.append({"sheet": sheet, "columns": headers, "header_row": hdr, "mapping": dict(mapping),
                           "preview": preview_rows(df)})
        if kind == "unsupported" and sum(1 for h in df.iloc[hdr].tolist() if isinstance(h, str) and h.strip()) < 2:
            res.messages.append(f"Sheet '{sheet}' has no column headings - ignored")
            continue
        if kind == "unsupported":
            res.needs_mapping.append({"sheet": sheet, "columns": headers, "header_row": hdr, "preview": preview_rows(df)})
            res.messages.append(f"Sheet '{sheet}': structure not recognised - column mapping needed")
            continue
        kinds.append(kind)
        idx = {f: headers.index(h) for f, h in mapping.items()}
        used = set(idx.values())
        amt_idx = next((i for i, h in enumerate(headers)
                        if i not in used and h.strip().lower() in ("amount", "amt", "value", "invoice amt")), None)
        row_vals_amount = lambda v: v[amt_idx] if amt_idx is not None and amt_idx < len(v) else None
        body = df.iloc[hdr + 1:]
        for ridx, row in body.iterrows():
            vals = row.tolist()

            def g(f, vals=vals):
                return _clean(vals[idx[f]]) if f in idx else None

            inv = g("invoice_no")
            if inv is None or str(inv).strip() == "":
                continue
            low = str(inv).strip().lower()
            if low.startswith(("total", "grand total", "sub total")):
                continue
            l = Line(id=next_id, source_file=path.name,
                     source_ref=f"{sheet}!row {ridx + 1 + 0}", supplier_gstin=client["gstin"],
                     supplier_name=client.get("legal_name") or client["name"])
            next_id += 1
            l.invoice_no = str(inv).strip()
            if isinstance(inv, float) and inv.is_integer():
                l.invoice_no = str(int(inv))
            l.invoice_date = parse_date(g("invoice_date"))
            l.recipient_gstin = str(g("recipient_gstin") or "").strip().upper()
            l.recipient_name = str(g("recipient_name") or "").strip()
            l.hsn = re.sub(r"\.0$", "", str(g("hsn") or "").strip())
            l.description = str(g("description") or "").strip()
            l.uqc = str(g("uqc") or "").strip().upper()
            l.qty = D(g("qty"))
            l.taxable = D(g("taxable"))
            l.igst, l.cgst, l.sgst, l.cess = D(g("igst")), D(g("cgst")), D(g("sgst")), D(g("cess"))
            l.invoice_total = D(g("invoice_total"))
            l.note_type = _note_type(g("note_type"))
            l.reverse_charge = _rc(g("reverse_charge"))
            l.orig_invoice_no = str(g("orig_invoice_no") or "").strip()
            l.orig_invoice_date = parse_date(g("orig_invoice_date"))
            l.ecom_gstin = str(g("ecom_gstin") or "").strip().upper()
            nk = str(g("nil_kind") or "").strip().lower()
            l.nil_kind = ("Non-GST" if "non" in nk else "Exempted" if "exempt" in nk else
                          "Nil Rated" if "nil" in nk else "")
            et = str(g("export_type") or "").strip().upper()
            l.export_type = "WOPAY" if et.startswith("WOP") or "WITHOUT" in et else "WPAY" if et else ""
            l.port_code = str(g("port_code") or "").strip().upper()
            l.ship_bill_no = re.sub(r"\.0$", "", str(g("ship_bill_no") or "").strip())
            l.ship_bill_date = parse_date(g("ship_bill_date"))
            it = str(g("invoice_type") or "").strip()
            if it:
                l.invoice_type, et2 = decode_invoice_type(it)
                l.invoice_type = l.invoice_type or "Regular"
                if et2 and not l.export_type:
                    l.export_type = et2
            # rate
            if "rate" in idx and g("rate") is not None:
                r = D(g("rate"))
                if 0 < r < 1 and r not in (D("0.1"), D("0.25")):   # 0.18 style fractions
                    r = r * 100
                l.rate = r
            elif l.taxable:
                l.rate = snap_rate(l.taxable, l.igst + l.cgst + l.sgst, rates)
                l.note = "Rate inferred from tax amounts"
            # place of supply
            pos_raw = g("pos")
            l.pos = state_from_text(pos_raw) if pos_raw else ""
            if not l.pos and fixed.get("pos"):
                l.pos = state_from_text(fixed["pos"])
            if not l.pos and l.recipient_gstin:
                l.pos = state_of(l.recipient_gstin)
            # ---- "same value for every row" chosen on the mapping screen (used where the file has no such column)
            if fixed.get("invoice_type") and not it:
                l.invoice_type, et2 = decode_invoice_type(fixed["invoice_type"])
                if et2 and not l.export_type:
                    l.export_type = et2
            if fixed.get("note_type") and "note_type" not in idx:
                l.note_type = _note_type(fixed["note_type"])
            if fixed.get("reverse_charge") and "reverse_charge" not in idx:
                l.reverse_charge = _rc(fixed["reverse_charge"])
            if fixed.get("nil_kind") and not l.nil_kind:
                nk = fixed["nil_kind"].lower()
                l.nil_kind = "Non-GST" if "non" in nk else "Exempted" if "exempt" in nk else "Nil Rated"
            if fixed.get("rate") and not l.rate and D(fixed["rate"], None) is not None:
                l.rate = D(fixed["rate"])
                l.note = (l.note + "; " if l.note else "") + f"GST rate {l.rate}% set for the whole file"
            # ---- exempt / nil file: only an 'Amount' column and no tax -> the amount is the (non-taxable) value
            if not l.taxable and not (l.igst or l.cgst or l.sgst):
                am = D(row_vals_amount(vals)) if amt_idx is not None else ZERO
                l.taxable = l.invoice_total or am
                if l.taxable:
                    l.note = (l.note + "; " if l.note else "") + "Taxable value taken from the Amount column (no tax in source)"
            if not l.nil_kind and l.taxable and not l.rate and not (l.igst or l.cgst or l.sgst):
                fn = path.name.lower().replace(" ", "").replace("_", "").replace("-", "")
                hint = ("Non-GST" if "nongst" in fn else "Exempted" if "exempt" in fn else "Nil Rated" if "nil" in fn else "")
                if hint:
                    l.nil_kind = hint
                    l.note = (l.note + "; " if l.note else "") + f"Marked {hint} from the file name - change if wrong"
            conf = 1.0 if kind == "item-level" else 0.9
            if kind == "sales-register":
                l.note = (l.note + "; " if l.note else "") + "No item-level HSN data in source"
            l.confidence = conf
            res.lines.append(l)
    res.kind = ", ".join(sorted(set(kinds))) or "unsupported"
    if not res.lines and not res.needs_mapping:
        res.messages.append("No invoice rows found")
    return res
