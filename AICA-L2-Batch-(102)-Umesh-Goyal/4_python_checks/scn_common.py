r"""Shared helpers for the SCN checks (standard library only, plus pypdf for text PDFs).

Everything here works on plain text, so the same code serves a text PDF (read with pypdf)
and a scanned PDF (read with OCR first).
"""
import re
from collections import Counter

# ---------- reading ----------

def pdf_text(path):
    """Text layer of a PDF. Returns '' for a scanned PDF (no text layer)."""
    from pypdf import PdfReader
    reader = PdfReader(path)
    return "\n".join((p.extract_text() or "") for p in reader.pages), len(reader.pages)


# ---------- Indian number format ----------

def inr(n):
    """1126156 -> 11,26,156"""
    s = str(int(n))
    neg = s.startswith("-")
    s = s.lstrip("-")
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if neg else "") + s


# ---------- header fields ----------

GSTIN = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b")

_TO_DIGIT = {"O": "0", "D": "0", "I": "1", "L": "1", "S": "5", "B": "8", "Z": "2"}
_TO_LETTER = {"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z"}


def gstin_ocr_guess(text):
    """When no valid GSTIN is found, OCR has usually swapped 0/O, 1/I, 5/S or 8/B (or added a
    character). Take what follows the word GSTIN, repair each position by the GSTIN pattern when
    it has exactly 15 characters, and otherwise return the raw text. Either way the person must
    read the GSTIN on the notice: this is a pointer, not a result."""
    out = []
    for raw in re.findall(r"GSTIN\s*[:\-]?\s*([A-Z0-9]{10,20})", text):
        if len(raw) == 15:
            chars = list(raw)
            for i, ch in enumerate(chars):
                if i in (0, 1, 7, 8, 9, 10):
                    chars[i] = _TO_DIGIT.get(ch, ch)
                elif i in (2, 3, 4, 5, 6, 11):
                    chars[i] = _TO_LETTER.get(ch, ch)
            fixed = "".join(chars)
            out.append(fixed if GSTIN.fullmatch(fixed) else raw)
        else:
            out.append(raw)
    return sorted(set(out))


def header_fields(text, pages=None):
    """Candidate lists, not a single guess: the first regex hit is often the wrong one,
    so every candidate is kept and the main one is chosen by simple counting."""
    # SCN number: the token after "Show Cause Notice No."
    scn_numbers = re.findall(r"Show\s*Cause\s*Notice\s*No\.?\s*[:\-]?\s*(\S+)", text, re.I)

    # Dates: "dated dd-mm-yyyy", "Date: dd-mm-yyyy" and the digital-signature stamp yyyy.mm.dd
    dates = re.findall(r"\bdated?\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})", text, re.I)
    stamp = re.findall(r"Date\s*[:\-]?\s*(\d{4})[./-](\d{2})[./-](\d{2})", text, re.I)
    stamp_dates = ["%s-%s-%s" % (d, m, y) for y, m, d in stamp]

    # Section: count every mention of 73 / 73A / 74 / 74A and pick the most frequent
    sec_hits = [s.upper() for s in re.findall(r"\bsection\s*(7[34]A?)\b", text, re.I)]
    sec_counts = Counter(sec_hits)

    forms = sorted({re.sub(r"\s+", "", f.upper().replace("\u2014", "-").replace("\u2013", "-"))
                    for f in re.findall(r"(DRC\s*[-\u2013\u2014]?\s*0?\d[A-Z]?)", text, re.I)})

    fys = sorted(set(re.findall(r"(?:FY|F\.Y\.|financial\s+years?)\s*(20\d{2}-\d{2})", text, re.I)))
    amounts = re.findall(r"(?:Rs\.?|INR|\u20b9)\s*([\d,]*\d)", text, re.I)

    reply_due = re.findall(r"on or before\s*(\d{2}[./-]\d{2}[./-]\d{4})", text, re.I)
    hearing = re.findall(r"personal\s+hearing\s+on\s*(\d{2}[./-]\d{2}[./-]\d{4})", text, re.I)
    din = re.findall(r"\bDIN\s*[:\-]?\s*([A-Z0-9]{12,25})", text)

    return {
        "scn_number": scn_numbers[0].rstrip(",.;") if scn_numbers else None,
        "scn_date_candidates": sorted(set(dates + stamp_dates)),
        "form": forms,
        "section_main": sec_counts.most_common(1)[0][0] if sec_counts else None,
        "sections_mentioned": dict(sec_counts),
        "gstin": sorted(set(GSTIN.findall(text))),
        "gstin_ocr_guess_verify": gstin_ocr_guess(text) if not GSTIN.findall(text) else [],
        "financial_years": fys,
        "amounts_found": amounts,
        "reply_due_date_in_notice": reply_due,
        "personal_hearing_date": hearing,
        "din_found": bool(din),
        "pages": pages,
    }


# ---------- tax table ----------

# A number token: at least 5 characters, digits with commas, not part of a year like 2022-23
NUM = r"(?<![\d,.\-])\d[\d,]*\d(?![\d\-])"
ROW = re.compile(r"(20\d{2}-\d{2})((?:\s+" + NUM + r"){3,4})")
TOTAL = re.compile(r"\bTotal((?:\s+" + NUM + r"){3,4})", re.I)


def _nums(chunk):
    out = []
    for tok in re.findall(NUM, chunk):
        if len(tok) >= 5:
            out.append(int(tok.replace(",", "")))
    return out


def tax_tables(text):
    """Find year rows followed by a Total row. Works whether each row is on one line
    (OCR) or each cell is on its own line (pypdf)."""
    items = []
    for m in ROW.finditer(text):
        items.append((m.start(), "row", m.group(1), _nums(m.group(2))))
    for m in TOTAL.finditer(text):
        items.append((m.start(), "total", "Total", _nums(m.group(1))))
    items.sort()
    tables, rows = [], []
    for _, kind, label, nums in items:
        if kind == "row":
            rows.append((label, nums))
        elif rows:
            tables.append((rows, nums))
            rows = []
    return tables


# =====================================================================
# Added for check_scn.py: numbers, dates and the checks that work on the AI Studio JSON
# =====================================================================
import calendar
import json
import sys
from datetime import date, timedelta

GSTR9_DUE = {
    "2020-21": date(2022, 2, 28),
    "2021-22": date(2022, 12, 31),
    "2022-23": date(2023, 12, 31),
    "2023-24": date(2024, 12, 31),
    "2024-25": date(2025, 12, 31),
}
DATE_RE = re.compile(r"(\d{1,2})[-./](\d{1,2})[-./](\d{4})")


def load_json_file(path):
    """AI Studio sometimes wraps the JSON in ``` fences; take what is between the outer braces."""
    raw = open(path, encoding="utf-8-sig").read()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("No JSON object found in " + path)
    return json.loads(raw[start:end + 1])


def find_date(text):
    m = DATE_RE.search(str(text or ""))
    if not m:
        return None
    d, mth, y = map(int, m.groups())
    try:
        return date(y, mth, d)
    except ValueError:
        return None


def years_from_text(text):
    """'2021-22, 2022-23' or '2021-22 to 2023-24' -> ['2021-22', '2022-23', '2023-24']"""
    if isinstance(text, (list, tuple)):
        text = " ".join(str(t) for t in text)
    years = sorted(set(re.findall(r"20\d{2}-\d{2}", str(text or ""))))
    if len(years) == 2 and re.search(r"\bto\b|–|—", str(text)):
        a, b = int(years[0][:4]), int(years[1][:4])
        years = ["%d-%02d" % (y, (y + 1) % 100) for y in range(a, b + 1)]
    return years


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)


def add_months(d, n):
    total = d.year * 12 + (d.month - 1) + n
    y, m = divmod(total, 12)
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def show(d):
    return d.strftime("%d-%m-%Y")


def limitation_lines(scn, years, reply_printed=None, due_lookup=None):
    """Lines of text: reply date and, for each year, the section 73 / 74 / 74A windows.
    due_lookup(fy) may return a date for a year that is not in the table (or None)."""
    today = date.today()
    reply = reply_printed or (scn + timedelta(days=30))
    out = ["SCN date        : %s" % show(scn),
           "Financial years : %s" % ", ".join(years),
           "Reply due       : %s %s | days left from today: %d" % (
               show(reply),
               "(date printed in the notice)" if reply_printed else "(SCN date + 30 days; the date in the notice overrides)",
               (reply - today).days),
           ""]
    for fy in years:
        due = GSTR9_DUE.get(fy) or (due_lookup(fy) if due_lookup else None)
        if not due:
            out.append("FY %s : GSTR-9 due date not in the table - skipped (add it to GSTR9_DUE in scn_common.py after checking the notification)." % fy)
            out.append("")
            continue
        out.append("FY %s | GSTR-9 due: %s" % (fy, show(due)))
        if int(fy[:4]) >= 2024:
            last = add_months(due, 42)
            out.append("   s.74A: SCN by %s (42 months) | %s | order within 12 months of the notice" % (
                show(last), "within time" if scn <= last else "BARRED"))
        else:
            o73, o74 = add_years(due, 3), add_years(due, 5)
            s73, s74 = add_months(o73, -3), add_months(o74, -6)
            out.append("   s.73: order by %s | SCN by %s | %s" % (show(o73), show(s73), "within time" if scn <= s73 else "BARRED"))
            out.append("   s.74: order by %s | SCN by %s | %s" % (show(o74), show(s74), "within time" if scn <= s74 else "BARRED"))
        out.append("   Extension under s.168A: not checked here - verify on the official site.")
        out.append("")
    return out


# ---------- numbers from the JSON ----------

def parse_num(x):
    """'6,90,500' / 'Rs. 6,90,500/-' / 690500 -> 690500.  None if there is no number."""
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    m = re.search(r"\d[\d,]*(?:\.\d+)?", str(x))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def _close(a, b, tol=1.0):
    return abs(a - b) <= tol


def table_checks(data, rate_fwd=None, rate_rcm=None):
    """Arithmetic checks on year_wise_table. Nothing is assumed about the rates unless the user gives them:
    the implied rate is shown and the years are compared with each other.
    Returns (lines, problems)."""
    rows = data.get("year_wise_table")
    lines, problems = [], 0
    if not isinstance(rows, list) or not rows:
        return ["No year_wise_table in the JSON - amount check skipped."], 0

    def g(row, key):
        return parse_num(row.get(key)) if isinstance(row, dict) else None

    year_rows = [r for r in rows if isinstance(r, dict) and re.search(r"20\d{2}-\d{2}", str(r.get("year", "")))]
    total_rows = [r for r in rows if isinstance(r, dict) and re.search(r"total", str(r.get("year", "")), re.I)]
    implied_fwd, implied_rcm = [], []

    for r in year_rows:
        fy = r.get("year")
        lines.append("FY %s" % fy)
        q, rt, v = g(r, "quantity"), g(r, "rate"), g(r, "value")
        if q is not None and rt is not None and v is not None:
            ok = _close(q * rt, v)
            lines.append("   quantity x rate = %s | value printed %s | %s" % (inr(q * rt), inr(v), "OK" if ok else "MISMATCH"))
            problems += 0 if ok else 1
        else:
            lines.append("   quantity x rate = value : not checked (quantity or rate not printed)")
        t5 = g(r, "tax_forward_charge")
        if v and t5 is not None:
            pct = t5 / v * 100
            implied_fwd.append((fy, pct))
            note = ""
            if rate_fwd is not None:
                ok = _close(v * rate_fwd / 100, t5)
                note = " | expected at %g%% = %s | %s" % (rate_fwd, inr(v * rate_fwd / 100), "OK" if ok else "MISMATCH")
                problems += 0 if ok else 1
            lines.append("   tax on value %s = %s -> implied rate %.2f%%%s" % (inr(v), inr(t5), pct, note))
        roy, rcm = g(r, "royalty_paid"), g(r, "tax_rcm")
        if roy and rcm is not None:
            pct = rcm / roy * 100
            implied_rcm.append((fy, pct))
            note = ""
            if rate_rcm is not None:
                ok = _close(roy * rate_rcm / 100, rcm)
                note = " | expected at %g%% = %s | %s" % (rate_rcm, inr(roy * rate_rcm / 100), "OK" if ok else "MISMATCH")
                problems += 0 if ok else 1
            lines.append("   RCM on royalty %s = %s -> implied rate %.2f%%%s" % (inr(roy), inr(rcm), pct, note))
        lines.append("")

    for name, imp in (("forward-charge", implied_fwd), ("RCM", implied_rcm)):
        if len(imp) > 1:
            same = max(p for _, p in imp) - min(p for _, p in imp) <= 0.01
            lines.append("Implied %s rate is %s across the years: %s" % (
                name, "the same" if same else "NOT the same (one figure may be misread)",
                ", ".join("%s %.2f%%" % (fy, p) for fy, p in imp)))
            problems += 0 if same else 1

    # every numeric column except year / quantity / rate is added and compared with the printed Total row,
    # so a table with other column names is still checked
    cols = []
    for r in rows:
        if isinstance(r, dict):
            for k, v in r.items():
                if k not in ("year", "quantity", "rate") and parse_num(v) is not None and k not in cols:
                    cols.append(k)
    sums = {c: sum(g(r, c) or 0 for r in year_rows) for c in cols}
    for c in ("value", "royalty_paid", "tax_forward_charge", "tax_rcm"):
        sums.setdefault(c, 0)
    if total_rows:
        tr = total_rows[0]
        lines.append("")
        lines.append("Total row printed in the notice vs sum of the years:")
        for c in cols:
            tv = g(tr, c)
            if tv is None:
                continue
            ok = _close(sums[c], tv)
            lines.append("   %-20s sum %s | printed %s | %s" % (c, inr(sums[c]), inr(tv), "OK" if ok else "MISMATCH"))
            problems += 0 if ok else 1
    else:
        lines.append("")
        lines.append("No total row printed - totals below are computed by this script, not read from the notice.")

    i1, i2 = parse_num(data.get("issue_1_tax_amount")), parse_num(data.get("issue_2_tax_amount"))
    if i1 is not None:
        ok = _close(sums["tax_forward_charge"], i1)
        lines.append("Issue 1 amount %s vs column sum %s | %s" % (inr(i1), inr(sums["tax_forward_charge"]), "OK" if ok else "MISMATCH"))
        problems += 0 if ok else 1
    if i2 is not None:
        ok = _close(sums["tax_rcm"], i2)
        lines.append("Issue 2 amount %s vs column sum %s | %s" % (inr(i2), inr(sums["tax_rcm"]), "OK" if ok else "MISMATCH"))
        problems += 0 if ok else 1
    lines.append("Tax demanded, both issues (computed): %s" % inr(sums["tax_forward_charge"] + sums["tax_rcm"]))
    return lines, problems


def source_check(data, text):
    """Does every figure the AI reported appear in the notice text? A figure that is not in the text was
    misread or invented. Works on a PDF with a text layer, or on OCR text."""
    present = set()
    for tok in re.findall(r"\d[\d,]*\d", text):
        try:
            present.add(int(tok.replace(",", "")))
        except ValueError:
            pass
    figures = []
    for key in ("issue_1_tax_amount", "issue_2_tax_amount", "penalty_amount"):
        figures.append((key, data.get(key)))
    for r in data.get("year_wise_table") or []:
        if isinstance(r, dict):
            for k in ("quantity", "rate", "value", "tax_forward_charge", "royalty_paid", "tax_rcm"):
                if r.get(k) is not None:
                    figures.append(("%s / %s" % (r.get("year"), k), r.get(k)))
    lines, problems, checked = [], 0, 0
    for label, val in figures:
        n = parse_num(val)
        if n is None or n < 1000:
            continue
        checked += 1
        if int(n) in present:
            continue
        lines.append("   NOT FOUND in the notice text: %s = %s" % (label, val))
        problems += 1
    head = "%d figure(s) checked against the notice text: %s" % (
        checked, "all found" if problems == 0 else "%d NOT found" % problems)
    return [head] + lines, problems


def rate_from_text(text):
    """If a description mentions exactly one percentage (e.g. '... taxable at 5% ...'), return it, else None."""
    found = set(re.findall(r"(\d+(?:\.\d+)?)\s*(?:%|per\s*cent)", str(text or "")))
    return float(found.pop()) if len(found) == 1 else None
