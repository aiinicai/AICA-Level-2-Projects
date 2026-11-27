"""
Excel extractor (.xlsx / .xlsm / .xls).

Handles three layouts:
  1. The CMA Builder Input Template (column 'CMA Head Key' present) - exact.
  2. Vertical statements: Particulars | (Note) | FY 2025-26 | FY 2024-25 ...
     Year columns are read from the headers; one statement per sheet or a
     'Statement' column.
  3. T-form (horizontal) statements: Particulars | Amount || Particulars | Amount
     Each text cell starts a segment; the last amount in the segment is taken.
Every line becomes a SourceLine (label, amount, FY, statement) for the mapper.
"""
import os
import re

from core.models import SourceLine
from extraction.statement_detector import (parse_amount, classify_text, detect_years,
                                           year_from_header)


def _read_rows(path):
    """Yield (sheet_name, rows[list of lists])."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xls":
        import xlrd
        wb = xlrd.open_workbook(path)
        for sh in wb.sheets():
            rows = []
            for r in range(sh.nrows):
                row = []
                for c in range(sh.ncols):
                    cell = sh.cell(r, c)
                    v = cell.value
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        try:
                            v = xlrd.xldate.xldate_as_datetime(v, wb.datemode)
                        except Exception:
                            pass
                    if v == "":
                        v = None
                    row.append(v)
                rows.append(row)
            yield sh.name, rows
    else:
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        for ws in wb.worksheets:
            if getattr(ws, "sheet_state", "visible") != "visible":
                continue
            rows = [list(r) for r in ws.iter_rows(values_only=True)]
            yield ws.title, rows
        wb.close()


def _is_text(v):
    return isinstance(v, str) and v.strip() != "" and parse_amount(v) is None


def _sheet_text(rows, limit=60):
    parts = []
    for r in rows[:limit]:
        for v in r:
            if isinstance(v, str):
                parts.append(v)
    return " ".join(parts)


def _template_lines(rows, src, default_year):
    """CMA Builder Input Template."""
    hdr_idx = None
    for i, r in enumerate(rows[:15]):
        cells = [str(v).strip().lower() if v is not None else "" for v in r]
        if "cma head key" in cells:
            hdr_idx = i
            break
    if hdr_idx is None:
        return None
    hdr = rows[hdr_idx]
    cells = [str(v).strip().lower() if v is not None else "" for v in hdr]
    c_key = cells.index("cma head key")
    c_lab = cells.index("particulars") if "particulars" in cells else 0
    c_st = cells.index("statement") if "statement" in cells else None
    year_cols = [(j, year_from_header(v)) for j, v in enumerate(hdr)]
    year_cols = [(j, y) for j, y in year_cols if y]
    out = []
    for r in rows[hdr_idx + 1:]:
        if c_key >= len(r) or not r[c_key]:
            continue
        key = str(r[c_key]).strip()
        st = str(r[c_st]).strip().upper() if c_st is not None and r[c_st] else ("PL" if key in _PL_SET else "BS")
        for j, y in year_cols:
            if j < len(r):
                amt = parse_amount(r[j])
                if amt is None:
                    continue
                out.append(SourceLine(year=y, statement=st, label=str(r[c_lab] or key), amount=amt,
                                      head=key, confidence=100, source=src, note="input template"))
    return out


def _vertical_lines(rows, src, statement, default_year):
    """Particulars + year columns."""
    best = None
    for i, r in enumerate(rows[:25]):
        ycols = [(j, year_from_header(v)) for j, v in enumerate(r)]
        ycols = [(j, y) for j, y in ycols if y]
        if ycols and (best is None or len(ycols) > len(best[1])):
            best = (i, ycols)
    if not best:
        return None
    hdr_i, ycols = best
    hdr = rows[hdr_i]
    st_col = None
    for j, v in enumerate(hdr):
        if isinstance(v, str) and v.strip().lower() in ("statement", "type"):
            st_col = j
    out = []
    current_st = statement
    for r in rows[hdr_i + 1:]:
        label = None
        for j, v in enumerate(r):
            if j in [c for c, _ in ycols]:
                break
            if _is_text(v):
                label = v.strip() if label is None else label + " " + v.strip()
        if not label:
            continue
        low = label.lower()
        if "balance sheet" in low or "equity and liabilities" in low:
            current_st = "BS"
        elif "profit and loss" in low or "profit & loss" in low or "income and expenditure" in low:
            current_st = "PL"
        st = current_st
        if st_col is not None and st_col < len(r) and r[st_col]:
            st = "PL" if str(r[st_col]).upper().startswith("P") else "BS"
        for j, y in ycols:
            if j < len(r):
                amt = parse_amount(r[j])
                if amt is None:
                    continue
                out.append(SourceLine(year=y, statement=st or "PL", label=label, amount=amt, source=src))
    return out


def _tform_lines(rows, src, statement, year, max_col=None):
    from extraction.tform_rules import TState, emit, orphan
    out = []
    state = TState()
    split = _split_col(rows)
    for r in rows:
        if max_col is not None:
            r = r[:max_col + 1]
        seg_label, nums, seg_col = None, [], 0
        segs, orphans = [], {}
        for j, v in enumerate(r):
            if _is_text(v):
                if v.strip().lower() in ("to", "by"):
                    continue
                if seg_label is not None:
                    segs.append((seg_label, nums, seg_col))
                seg_label, nums, seg_col = v.strip(), [], j
            else:
                a = parse_amount(v)
                if a is None:
                    continue
                side_here = 1 if (split is not None and j >= split) else 0
                if seg_label is not None and (split is None or (1 if seg_col >= split else 0) == side_here):
                    nums.append(a)
                else:
                    orphans.setdefault(side_here, []).append(a)
        if seg_label is not None:
            segs.append((seg_label, nums, seg_col))
        for lab, ns, col in segs:
            side = 1 if (split is not None and col >= split) else 0
            out += emit(state, side, lab, ns, year, statement or "PL", src)
        for side, ns in orphans.items():
            out += orphan(state, side, ns, year, statement or "PL", src)
    return out


_TITLE = re.compile(r"(year\s+end(ed|ing)|as\s+(on|at))\b.*?(20\d{2})", re.I)


def _blocks(rows):
    """Split a sheet holding several statements (one under the other) at their title rows."""
    titles = []
    for i, r in enumerate(rows):
        for v in r[:12]:
            if isinstance(v, str) and _TITLE.search(v) and ("account" in v.lower() or "balance sheet" in v.lower()
                                                            or "statement" in v.lower()):
                titles.append((i, v))
                break
    out = []
    for k, (i, title) in enumerate(titles):
        end = titles[k + 1][0] if k + 1 < len(titles) else len(rows)
        start = max(0, i - 4) if k == 0 else i
        year = int(_TITLE.search(title).group(4))
        st = "BS" if "balance sheet" in title.lower() else "PL"
        block = rows[i:end]
        # statement columns end at the last heading of the header row ([RS.] / AMOUNT)
        max_col = None
        for r in block[:6]:
            hdr = [j for j, v in enumerate(r) if isinstance(v, str) and re.search(r"\brs\b|amount", v, re.I)]
            if len(hdr) >= 2:
                max_col = max(hdr)
                break
        out.append((year, st, block, max_col, title.strip()))
    return out


def _split_col(rows):
    """Column where the right-hand side of a T-form starts (second heading on the header row)."""
    heads = ("particulars", "liabilities", "assets", "expenditure", "income", "dr.", "cr.")
    for r in rows[:15]:
        cols = [j for j, v in enumerate(r) if isinstance(v, str) and v.strip().lower().rstrip(":") in heads]
        if len(cols) >= 2:
            return cols[1]
    return None


def extract_excel(path, default_year=None, force_statement=None):
    """Return (lines, info_messages)."""
    lines, info = [], []
    base = os.path.basename(path)
    for sheet, rows in _read_rows(path):
        rows = [r for r in rows if r and any(v not in (None, "") for v in r)]
        if not rows:
            continue
        src = "%s / %s" % (base, sheet)
        tl = _template_lines(rows, src, default_year)
        if tl is not None:
            lines += tl
            info.append("%s: CMA input template read (%d values)." % (src, len(tl)))
            continue
        text = sheet + " " + _sheet_text(rows)
        st = force_statement or classify_text(text) or ""
        blocks = _blocks(rows)
        if blocks and any(_split_col(b[2]) is not None for b in blocks):
            for year, bst, block, max_col, title in blocks:
                bl = _tform_lines(block, src, force_statement or bst, year, max_col)
                btxt = _sheet_text(block, 200).lower()
                kind = "Provisional" if "provisional" in btxt else (
                    "Audited" if re.search(r"\baudited\b|auditor'?s'? report|udin", btxt) else "")
                for ln in bl:
                    ln.year_kind = kind
                lines += bl
                info.append("%s: %s, year ending %d, %d lines (T-form)." % (src, "Balance Sheet" if bst == "BS"
                                                                             else "P&L", year, len(bl)))
            continue
        vl = _vertical_lines(rows, src, st, default_year)
        if vl:
            lines += vl
            info.append("%s: vertical layout, %s, %d values." % (src, st or "mixed", len(vl)))
            continue
        years = detect_years(text)
        year = years[0] if years else default_year
        if year is None:
            info.append("%s: financial year not found - choose it on the Upload page and read again." % src)
            continue
        tf = _tform_lines(rows, src, st, year)
        lines += tf
        info.append("%s: T-form layout, %s, FY ending %s, %d lines." % (src, st or "?", year, len(tf)))
    return lines, info


from config.constants import PL_KEYS as _PLK  # noqa: E402
_PL_SET = set(_PLK) | {"_reported_net_profit"}
