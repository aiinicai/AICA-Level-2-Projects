"""Read filed returns downloaded from the GST portal (PDF): GSTR-1, GSTR-3B and GSTR-9.

The portal PDFs carry a large rotated watermark ("FILED", "FINAL", "SYSTEM COMPUTED"). Its letters are dropped by
size / rotation before the text is put back into table rows, otherwise they break the rows.
Pages that are pictures (for example a page masked and re-saved before sharing) are read with OCR when Tesseract is
installed; OCR figures are marked for checking.

Every reader returns a plain dict that is stored per client and financial year:
    {"form": "GSTR1" | "GSTR3B" | "GSTR9", "fy": "2025-26", "month": 3, "year": 2026, "gstin": "...",
     "arn_date": "...", "file": "...", "ocr": bool, "messages": [...], "data": {...}}
Amounts are kept as strings (exact decimals) so the dict can be saved as JSON.
"""
import json
import logging
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median

log = logging.getLogger(__name__)

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
GSTIN_RE = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b")
AMT_RE = re.compile(r"^\(?(-?)[₹]?([\d,]*\d\.\d{2})\)?$")
Z = Decimal("0")
V5 = ("value", "igst", "cgst", "sgst", "cess")


# ------------------------------------------------------------------ text from the PDF
def spans_to_text(spans) -> str:
    """spans: (x0, y0, x1, y1, text, size, rotated) -> text lines, top to bottom, left to right.
    Watermark letters (rotated, or far larger than the body text) are dropped."""
    body = [s for s in spans if str(s[4]).strip() and not s[6]]
    if not body:
        return ""
    med = median(s[5] for s in body)
    body = [s for s in body if s[5] <= max(med * 2.5, 14)]
    from .extractors.pdf_reader import words_to_text
    return words_to_text([s[:5] for s in body])


def _pymupdf_spans(page):
    out = []
    d = page.get_text("dict")
    for b in d.get("blocks", []):
        if b.get("type", 0) != 0:
            continue
        for ln in b.get("lines", []):
            dx, dy = ln.get("dir", (1, 0))
            rotated = abs(dy) > 0.05 or dx < 0
            for s in ln.get("spans", []):
                x0, y0, x1, y1 = s["bbox"]
                for part in _split_span(s["text"], x0, x1):
                    out.append((part[0], y0, part[1], y1, part[2], s.get("size", 8), rotated))
    return out


def _split_span(text, x0, x1):
    """Split a span on runs of 2+ spaces so table cells stay separate words (approximate x positions)."""
    parts = [p for p in re.split(r"(\s{2,})", text)]
    n = max(len(text), 1)
    w = (x1 - x0) / n
    pos, out = 0, []
    for p in parts:
        if p.strip() and not re.fullmatch(r"\s+", p):
            out.append((x0 + pos * w, x0 + (pos + len(p)) * w, p.strip()))
        pos += len(p)
    return out


def pdf_pages_text(path, settings=None):
    """-> (list of page texts, ocr_used, messages). Uses PyMuPDF; OCR (Tesseract) for picture pages."""
    settings = settings or {}
    msgs, texts, ocr = [], [], False
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
    except ImportError:
        return [], False, ["PyMuPDF not installed - run: pip install pymupdf"]
    from .extractors.pdf_reader import _ocr_page
    try:
        doc = fitz.open(str(path))
    except Exception as e:  # noqa
        return [], False, [f"Cannot open PDF: {e}"]
    for i, page in enumerate(doc):
        try:
            t = spans_to_text(_pymupdf_spans(page))
        except Exception:  # noqa
            t = page.get_text()
        if len(t.strip()) < 30:
            if settings.get("ocr_enabled", "1") == "1":
                o = _ocr_page(page, settings.get("tesseract_path", ""))
                if o.strip():
                    t, ocr = o, True
                elif i == 0:
                    msgs.append(f"Page {i + 1} is a picture and OCR is not available - its figures are missing")
        texts.append(t)
    doc.close()
    if ocr:
        msgs.append("Some pages were pictures and were read with OCR - check those figures against the PDF")
    return texts, ocr, msgs


# ------------------------------------------------------------------ helpers
def amt(tok: str):
    """'1,25,000.50' -> Decimal; OCR noise at the ends is removed. None if not an amount."""
    t = str(tok).strip().strip("|[]{}=~;:'\"").replace("₹", "")
    m = AMT_RE.match(t)
    if not m:
        return None
    try:
        return Decimal(m.group(1) + m.group(2).replace(",", ""))
    except InvalidOperation:
        return None


def amounts(line: str):
    return [a for a in (amt(t) for t in line.split()) if a is not None]


def tokens(line: str):
    """Amounts and '-' placeholders in order (for tables with blank cells shown as '-')."""
    out = []
    for t in line.split():
        if t in ("-", "–"):
            out.append(None)
        else:
            a = amt(t)
            if a is not None:
                out.append(a)
    return out


def _norm(line: str) -> str:
    line = line.replace("–", "-").replace("—", "-").replace("|", " ")
    return re.sub(r"\s+", " ", line).strip()


def vec(nums):
    """Amounts of a GSTR-1 row -> value, igst, cgst, sgst, cess (blank columns are skipped by the portal)."""
    n = list(nums)
    if len(n) >= 5:
        v = n[-5:]
    elif len(n) == 4:
        v = n + [Z]
    elif len(n) == 3:
        v = [n[0], n[1], Z, Z, n[2]]
    elif len(n) == 2:
        v = [n[0], n[1], Z, Z, Z]
    elif len(n) == 1:
        v = [n[0], Z, Z, Z, Z]
    else:
        v = [Z] * 5
    return {k: str(x) for k, x in zip(V5, v)}


def D5(d):
    d = d or {}
    return {k: Decimal(str(d.get(k, "0") or "0")) for k in V5}


def add5(*vs, sign=None):
    out = {k: Z for k in V5}
    for i, v in enumerate(vs):
        s = 1 if not sign else sign[i]
        for k in V5:
            out[k] += s * v[k]
    return out


def tax_of(v):
    return v["igst"] + v["cgst"] + v["sgst"] + v["cess"]


def period_from_text(text: str, filename: str = ""):
    """-> (fy, month, year) from 'Financial year 2025-26 / Tax period March' or the portal file name _MMYYYY."""
    t = _norm(text)
    fy = None
    m = re.search(r"(?:Financial\s+year|Year)\s*[:|]?\s*(20\d\d)\s*-\s*(\d\d)", t, re.I)
    if m:
        fy = f"{m.group(1)}-{m.group(2)}"
    month = None
    m = re.search(r"(?:Tax\s+period|Period)\s*[:|]?\s*(" + "|".join(MONTHS) + r")", t, re.I)
    if m:
        month = MONTHS.index(m.group(1).lower()) + 1
    fm = re.search(r"_(\d{2})(20\d\d)(?:\D|$)", Path(filename).stem + "_")
    if fm and not month and 1 <= int(fm.group(1)) <= 12:
        month = int(fm.group(1))
    if fm and not fy and month:
        y = int(fm.group(2))
        s = y if month >= 4 else y - 1
        fy = f"{s}-{str(s + 1)[-2:]}"
    year = None
    if fy and month:
        s = int(fy[:4])
        year = s if month >= 4 else s + 1
    return fy, month, year


def detect_form(text: str, filename: str = "") -> str:
    t = _norm(text[:3000]).upper()
    n = Path(filename).name.upper()
    if "GSTR-9C" in t or "GSTR9C" in n:
        return ""
    if re.search(r"FORM\s+GSTR-?9\b", t) or re.search(r"GSTR-?9(?!C)(_|\b)", n):
        return "GSTR9"
    if re.search(r"FORM\s+GSTR-?3B", t) or "GSTR3B" in n.replace("-", ""):
        return "GSTR3B"
    if re.search(r"FORM\s+GSTR-?1\b", t) or re.search(r"GSTR-?1(_|\b)", n):
        return "GSTR1"
    return ""


def _gstin(text, filename):
    m = GSTIN_RE.search(text.upper())
    if m:
        return m.group(1)
    m = GSTIN_RE.search(Path(filename).name.upper().replace("_", " "))
    return m.group(1) if m else ""


def _arn_date(text):
    m = re.search(r"(?:ARN\s+date|Date\s+of\s+ARN)\s*[:|]?\s*(\d{2}/\d{2}/\d{4})", _norm(text), re.I)
    if m:
        return m.group(1)
    m = re.search(r"\(d\).{0,40}?(\d{2}/\d{2}/\d{4})", _norm(text), re.I)
    return m.group(1) if m else ""


# ------------------------------------------------------------------ GSTR-1
G1_HEADS = [
    (r"^4A\b", "4A"), (r"^4B\b", "4B"), (r"^5 -", "5"), (r"^6A\b", "6A"), (r"^6B\b", "6B"), (r"^6C\b", "6C"),
    (r"^7 ?-", "7"), (r"^8 -", "8"),
    (r"^9A .*table 4 - B2B Regular", "9A_B2B"), (r"^9A .*table 4 - B2B Reverse", "9A_RCM"),
    (r"^9A .*table 5", "9A_B2CL"), (r"^9A .*table 6A", "9A_EXP"), (r"^9A .*table 6B", "9A_SEZ"),
    (r"^9A .*table 6C", "9A_DE"),
    (r"^9B .*\(Registered\)", "9B_CDNR"), (r"^9B .*\(Unregistered\)", "9B_CDNUR"),
    (r"^9C .*\(Registered\)", "9C_CDNRA"), (r"^9C .*\(Unregistered\)", "9C_CDNURA"),
    (r"^10 -", "10"), (r"^11A\(1\)", "11A"), (r"^11B\(1\)", "11B"), (r"^11A - Amendment", "11AA"),
    (r"^11B - Amendment", "11BA"), (r"^12 -", "12"), (r"^13 -", "13"), (r"^14A\b", "14A"), (r"^14 -", "14"),
    (r"^15A", "15A"), (r"^15 -", "15"),
]


def _note_sub(line):
    if "B2B Regular" in line:
        return "REG"
    if "Reverse charge" in line:
        return "RCM"
    if "SEZWP/SEZWOP" in line or "table 6B" in line:
        return "SEZ"
    if re.search(r"6C\s*-?\s*-?\s*DE|- DE\b", line):
        return "DE"
    return None


def parse_gstr1(text: str) -> dict:
    data = {}
    sec, sub = None, None
    for raw in text.splitlines():
        line = _norm(raw)
        if not line:
            continue
        head = next((k for rx, k in G1_HEADS if re.search(rx, line, re.I)), None)
        if head:
            sec, sub = head, None
            continue
        if line.startswith("Total Liability"):
            data.setdefault("LIAB", {})["total"] = vec(amounts(line))
            continue
        if sec is None:
            continue
        if sec in ("9B_CDNR", "9C_CDNRA") and (line.startswith("Credit / Debit") or line.startswith("Amended Credit")):
            sub = _note_sub(line) or sub
            continue
        nums = amounts(line)
        if sec == "13":
            m = re.search(r"Net issued documents\D*(\d+)", line)
            if m:
                data.setdefault("13", {})["net_issued"] = m.group(1)
            continue
        if not nums:
            continue
        low = line.lower()
        if low.startswith("amended amount"):
            key = "amended"
        elif low.startswith("net differential"):
            key = "diff"
        elif low.startswith("net total"):
            key = sub or "total"
        elif low.startswith("b2b total"):
            key = "B2B"
        elif low.startswith("b2c total"):
            key = "B2C"
        elif low.startswith("total"):
            key = "total"
        else:
            m = re.match(r"^-\s*(EXPWP|EXPWOP|SEZWP|SEZWOP|B2CL|Nil|Exempted|Non-GST)\b", line, re.I)
            if not m:
                continue
            key = m.group(1).upper()
        bucket = data.setdefault(sec, {})
        if key == "diff" and "diff" in bucket and sec in ("9A_EXP", "9A_SEZ"):
            continue
        if key in bucket and key not in ("total",):
            continue
        if key == "total" and "total" in bucket and sec in ("11AA", "11BA"):
            continue
        if sec == "8" or key in ("NIL", "EXEMPTED", "NON-GST"):
            bucket[key] = {**vec([]), "value": str(nums[0])}
        else:
            bucket[key] = vec(nums)
    return data


def g1_figures(d: dict) -> dict:
    """Named 5-figure vectors from a parsed GSTR-1 (missing tables are zero)."""
    def g(sec, key="total"):
        return D5((d.get(sec) or {}).get(key))
    f = {
        "b2b": g("4A"), "rcm": g("4B"), "b2cl": g("5"), "expwp": g("6A", "EXPWP"), "expwop": g("6A", "EXPWOP"),
        "sezwp": g("6B", "SEZWP"), "sezwop": g("6B", "SEZWOP"), "de": g("6C"), "b2cs": g("7"),
        "nil": g("8", "NIL"), "exempt": g("8", "EXEMPTED"), "nongst": g("8", "NON-GST"),
        "a_b2b": g("9A_B2B", "diff"), "a_rcm": g("9A_RCM", "diff"), "a_b2cl": g("9A_B2CL", "diff"),
        "a_expwp": g("9A_EXP", "EXPWP"), "a_expwop": g("9A_EXP", "EXPWOP"),
        "a_sezwp": g("9A_SEZ", "SEZWP"), "a_sezwop": g("9A_SEZ", "SEZWOP"), "a_de": g("9A_DE", "diff"),
        "n_reg": g("9B_CDNR", "REG"), "n_rcm": g("9B_CDNR", "RCM"), "n_sez": g("9B_CDNR", "SEZ"),
        "n_de": g("9B_CDNR", "DE"), "nu_b2cl": g("9B_CDNUR", "B2CL"), "nu_expwp": g("9B_CDNUR", "EXPWP"),
        "nu_expwop": g("9B_CDNUR", "EXPWOP"),
        "na_reg": g("9C_CDNRA", "REG"), "na_rcm": g("9C_CDNRA", "RCM"), "na_sez": g("9C_CDNRA", "SEZ"),
        "na_de": g("9C_CDNRA", "DE"), "nau_b2cl": g("9C_CDNURA", "B2CL"), "nau_expwp": g("9C_CDNURA", "EXPWP"),
        "nau_expwop": g("9C_CDNURA", "EXPWOP"),
        "a_b2cs": g("10", "diff"), "adv": g("11A"), "adj": g("11B"), "a_adv": g("11AA"), "a_adj": g("11BA"),
        "hsn": g("12"), "liab": g("LIAB"),
    }
    if not any(f["nil"].values()) and not any(f["exempt"].values()) and not any(f["nongst"].values()):
        f["exempt"] = g("8")                       # only the table total was readable
    f["docs"] = int((d.get("13") or {}).get("net_issued") or 0)
    # notes: the 9B total when the sub-rows could not be read
    if not any(any(f[k].values()) for k in ("n_reg", "n_rcm", "n_sez", "n_de")):
        f["n_reg"] = g("9B_CDNR")
    return f


def g1_expected_3b(f: dict) -> dict:
    """GSTR-3B Table 3.1 as the portal auto-fills it from this GSTR-1."""
    rcm_keys = ("rcm", "a_rcm", "n_rcm", "na_rcm")
    a_keys = ("b2b", "rcm", "b2cl", "de", "b2cs", "a_b2b", "a_rcm", "a_b2cl", "a_de", "a_b2cs", "n_reg", "n_rcm",
              "n_de", "nu_b2cl", "na_reg", "na_rcm", "na_de", "nau_b2cl", "adv", "a_adv")
    minus = ("adj", "a_adj")
    a = add5(*[f[k] for k in a_keys + minus], sign=[1] * len(a_keys) + [-1] * len(minus))
    rcm = add5(*[f[k] for k in rcm_keys])
    a_tax = {k: (a[k] - rcm[k]) if k != "value" else a[k] for k in V5}
    b_keys = ("expwp", "expwop", "sezwp", "sezwop", "a_expwp", "a_expwop", "a_sezwp", "a_sezwop", "n_sez", "nu_expwp",
              "nu_expwop", "na_sez", "nau_expwp", "nau_expwop")
    b = add5(*[f[k] for k in b_keys])
    c = add5(f["nil"], f["exempt"])
    e = f["nongst"]
    return {"a": a_tax, "a_rcm_value": rcm["value"], "b": b, "c": c, "e": e}


# ------------------------------------------------------------------ GSTR-3B
def parse_gstr3b(text: str) -> dict:
    data = {"3.1": {}, "3.1.1": {}, "4": {}, "6.1": {}}
    sec, part61, part4 = None, None, None
    pending = None
    for raw in text.splitlines():
        line = _norm(raw)
        if not line:
            continue
        if re.match(r"^3\.1 Details", line):
            sec = "3.1"
            continue
        if re.match(r"^3\.1\.1", line):
            sec = "3.1.1"
            continue
        if re.match(r"^3\.2\b", line):
            sec = "3.2"
            continue
        if re.match(r"^4\.? ?Eligible ITC", line, re.I):
            sec = "4"
            continue
        if re.match(r"^5 Values|^5\.1\b", line):
            sec = "5"
            continue
        if re.match(r"^6\.1\b", line):
            sec = "6.1"
            continue
        if line.startswith("Breakup of tax"):
            sec = None
            continue
        if sec == "3.1":
            m = re.match(r"^\(\s*([a-e])\s*\)", line)
            if m:
                t = tokens(line)
                v = [x if x is not None else Z for x in t[:5]] + [Z] * (5 - len(t[:5]))
                data["3.1"][m.group(1)] = {"value": str(v[0]), "igst": str(v[1]), "cgst": str(v[2]),
                                           "sgst": str(v[3]), "cess": str(v[4])}
        elif sec == "3.1.1":
            m = re.match(r"^\((i{1,2})\)", line)
            if m:
                t = [x if x is not None else Z for x in tokens(line)][:5]
                t += [Z] * (5 - len(t))
                data["3.1.1"][m.group(1)] = {k: str(x) for k, x in zip(V5, t)}
        elif sec == "4":
            m = re.match(r"^\(?([A-D])[.)]", line)
            if m:
                part4 = m.group(1)
            m2 = re.match(r"^\((\d)\)", line)
            nums = amounts(line)
            key = None
            if m2 and part4:
                key = f"{part4}{m2.group(1)}"
            elif m and len(nums) >= 4:
                key = part4
            if key and len(nums) >= 4:
                data["4"][key] = {"igst": str(nums[-4]), "cgst": str(nums[-3]), "sgst": str(nums[-2]),
                                  "cess": str(nums[-1])}
        elif sec == "6.1":
            if line.startswith("(A)"):
                part61 = "A"
                continue
            if line.startswith("(B)"):
                part61 = "B"
                continue
            m = re.match(r"^(Integrated|Central|State/UT|Cess)\b", line)
            if m and part61:
                t = tokens(line)
                if len(t) >= 8:
                    t = (t + [None] * 10)[:10]
                    head = {"Integrated": "igst", "Central": "cgst", "State/UT": "sgst", "Cess": "cess"}[m.group(1)]
                    s = lambda x: str(x if x is not None else Z)   # noqa: E731
                    itc = sum((x for x in t[3:7] if x is not None), Z)
                    data["6.1"].setdefault(part61, {})[head] = {
                        "payable": s(t[0]), "net_payable": s(t[2]), "itc": str(itc), "cash": s(t[7]),
                        "interest": s(t[8]), "late_fee": s(t[9])}
    return data


def g3b_figures(d: dict) -> dict:
    t31 = {k: D5((d.get("3.1") or {}).get(k)) for k in "abcde"}
    pay = {}
    for part in ("A", "B"):
        for h in ("igst", "cgst", "sgst", "cess"):
            r = ((d.get("6.1") or {}).get(part) or {}).get(h) or {}
            for k in ("payable", "itc", "cash", "interest", "late_fee"):
                pay[f"{part}_{h}_{k}"] = Decimal(str(r.get(k, "0") or "0"))
    itc = {}
    for k, v in (d.get("4") or {}).items():
        itc[k] = {h: Decimal(str(v.get(h, "0"))) for h in ("igst", "cgst", "sgst", "cess")}
    return {"3.1": t31, "pay": pay, "itc": itc, "found_61": bool(d.get("6.1"))}


# ------------------------------------------------------------------ GSTR-9
def parse_gstr9(text: str) -> dict:
    data = {}
    table = None
    for raw in text.splitlines():
        line = _norm(raw)
        if not line:
            continue
        m = re.match(r"^(4|5|6|7|8|9|10|11|12|13|14|15|16|17|18|19)\s+(Details|Description|Particulars|Supplies|"
                     r"Differential|Late|Refunds|Demands|Information|Summary|HSN|Other)", line, re.I)
        if m:
            table = m.group(1)
            continue
        if re.match(r"^Pt\.?\s*(II|III|IV|V|VI)\b", line):
            continue
        m = re.match(r"^([A-Z]\d?)\s+(\S.*)$", line)
        if not m or not table:
            continue
        code, rest = m.group(1), m.group(2)
        nums = amounts(rest)
        if not nums:
            continue
        key = f"{table}{code}"
        if key in data:
            continue
        if table == "4":
            n = (nums + [Z] * 5)[:5]
            data[key] = {"value": str(n[0]), "cgst": str(n[1]), "sgst": str(n[2]), "igst": str(n[3]), "cess": str(n[4])}
        elif table == "5":
            data[key] = {"value": str(nums[0])}
        elif table in ("6", "7", "8"):
            n = nums[-4:] if len(nums) >= 4 else nums + [Z] * (4 - len(nums))
            data[key] = {"cgst": str(n[0]), "sgst": str(n[1]), "igst": str(n[2]), "cess": str(n[3])}
        elif table == "9":
            data[key] = {"payable": str(nums[0]), "cash": str(nums[1] if len(nums) > 1 else Z),
                         "paid": str(nums[-2] if len(nums) >= 3 else (nums[1] if len(nums) > 1 else Z)),
                         "diff": str(nums[-1] if len(nums) >= 3 else Z)}
        elif table in ("10", "11"):
            n = (nums + [Z] * 5)[:5]
            data[key] = {"value": str(n[0]), "cgst": str(n[1]), "sgst": str(n[2]), "igst": str(n[3]), "cess": str(n[4])}
        else:
            data[key] = {"value": str(nums[0])}
    return data


# ------------------------------------------------------------------ one file
def read_return_text(pages, filename: str) -> dict:
    text = "\n".join(pages)
    form = detect_form(text, filename)
    fy, month, year = period_from_text(text, filename)
    doc = {"form": form, "fy": fy, "month": month, "year": year, "gstin": _gstin(text, filename),
           "arn_date": _arn_date(text), "file": Path(filename).name, "messages": [], "data": {}}
    if not form:
        doc["messages"].append("Not a GSTR-1, GSTR-3B or GSTR-9 return PDF")
        return doc
    if form == "GSTR9":
        doc["month"], doc["year"] = 3, (int(fy[:4]) + 1 if fy else None)
    doc["data"] = {"GSTR1": parse_gstr1, "GSTR3B": parse_gstr3b, "GSTR9": parse_gstr9}[form](text)
    if not fy or (form != "GSTR9" and not month):
        doc["messages"].append("The return period could not be read - choose it before importing")
    if not doc["data"]:
        doc["messages"].append("No figures could be read from this file")
    return doc


def read_return(path, settings=None) -> dict:
    pages, ocr, msgs = pdf_pages_text(path, settings)
    doc = read_return_text(pages, Path(path).name)
    doc["ocr"] = ocr
    doc["messages"] = msgs + doc["messages"]
    return doc


def looks_like_return(path) -> bool:
    """Quick check by file name, used when scanning a folder."""
    n = Path(path).name.upper().replace("-", "")
    return Path(path).suffix.lower() == ".pdf" and bool(re.search(r"GSTR(1|3B|9)(_|\b)", n))


# ------------------------------------------------------------------ storage (per client and FY)
def filed_key(client_id, fy):
    return f"filed_returns_{client_id}_{fy}"


def load_filed(db, client_id, fy) -> dict:
    try:
        return json.loads(db.get_settings().get(filed_key(client_id, fy), "{}") or "{}")
    except Exception:  # noqa
        return {}


def save_filed(db, client_id, fy, filed: dict):
    db.set_setting(filed_key(client_id, fy), json.dumps(filed))


def store_return(db, client: dict, doc: dict) -> str:
    """Keep the return under its FY / form / month. Returns the FY used. A GSTR-3B also fills the typed
    GSTR-3B figures of the month (the 'Books vs GSTR-3B' table) unless they were typed by hand."""
    fy = doc["fy"]
    filed = load_filed(db, client["id"], fy)
    key = "FY" if doc["form"] == "GSTR9" else f"{doc['year']}-{doc['month']:02d}"
    filed.setdefault(doc["form"], {})[key] = doc
    save_filed(db, client["id"], fy, filed)
    if doc["form"] == "GSTR3B":
        from . import annual
        f = g3b_figures(doc["data"])["3.1"]
        entries = annual.load_entries(db, client["id"], fy)
        cur = entries.get(key, {})
        if not cur or cur.get("_src") == "GSTR-3B PDF":
            val = f["a"]["value"] + f["b"]["value"] + f["c"]["value"] + f["e"]["value"]
            new = {"tb_taxable": str(val), "_src": "GSTR-3B PDF"}
            for h in ("igst", "cgst", "sgst", "cess"):
                new["tb_" + h] = str(f["a"][h] + f["b"][h])
            if cur.get("bk_taxable"):
                new["bk_taxable"] = cur["bk_taxable"]
            entries[key] = new
            annual.save_entries(db, client["id"], fy, entries)
    return fy


def remove_return(db, client_id, fy, form, key):
    filed = load_filed(db, client_id, fy)
    (filed.get(form) or {}).pop(key, None)
    save_filed(db, client_id, fy, filed)
