"""
Generic parser for AMC monthly portfolio disclosures (.xlsx / .xls / .csv).

AMCs publish different layouts, so nothing is hard-coded per AMC. For every
sheet the parser:
  1. finds the header row that contains an 'ISIN' column,
  2. finds the weight column ('% to NAV', '% to Net Assets', '% of AUM' ...),
     the instrument-name column and the industry / rating column,
  3. reads every row whose ISIN is well formed,
  4. identifies the scheme from the sheet's title rows, sheet name and file name,
  5. identifies the portfolio date from the same text.
Some AMCs (UTI, in the SEBI exposure format) stack every scheme in ONE sheet, each block opening with a
"SCHEME: <name>" title. Such a sheet is split at those titles and each block is read as its own portfolio;
blocks that match no configured scheme are skipped (a file of 150 schemes would otherwise list 150 sheets).
Weights given as fractions (0.0523) are converted to percentages.
Every result carries warnings so the user can review before applying.
"""
import csv
import re
from datetime import date, datetime
from pathlib import Path

from common import is_equity_isin, isin_check_digit_ok, log, month_end

ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
RATING_WORDS = ("crisil", "icra", "care", "ind ", "ind a", "fitch", "brickwork", "sovereign", "sov", "aaa", "aa+", "a1+", "unrated", "tbill", "t-bill", "g-sec", "gsec")
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _grid_xlsx(path, max_rows=20000, max_cols=30):  # stacked all-scheme sheets run to ~10,000 rows
    import openpyxl
    with open(path, "rb") as fh:  # a file handle, so openpyxl does not reject a mis-named extension
        wb = openpyxl.load_workbook(fh, read_only=True, data_only=True)
        for ws in wb.worksheets:
            rows = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i >= max_rows:
                    break
                rows.append(list(row[:max_cols]))
            yield ws.title, rows
        wb.close()


def _grid_xls(path, max_rows=20000, max_cols=30):
    import xlrd
    wb = xlrd.open_workbook(path)
    for sh in wb.sheets():
        rows = []
        for r in range(min(sh.nrows, max_rows)):
            vals = []
            for c in range(min(sh.ncols, max_cols)):
                cell = sh.cell(r, c)
                if cell.ctype == xlrd.XL_CELL_DATE:
                    try:
                        vals.append(xlrd.xldate_as_datetime(cell.value, wb.datemode))
                        continue
                    except Exception:  # noqa: BLE001
                        pass
                vals.append(cell.value)
            rows.append(vals)
        yield sh.name, rows


def _grid_csv(path, max_rows=1500):
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        yield Path(path).stem, [r for i, r in enumerate(csv.reader(f)) if i < max_rows]


def grids(path):
    ext = Path(path).suffix.lower()
    if ext in (".xls", ".xlsx", ".xlsm"):
        # Pick the reader from the file's signature, not its name: some AMCs publish .xlsx workbooks named .xls.
        with open(path, "rb") as f:
            magic = f.read(8)
        if magic.startswith(b"PK"):
            return _grid_xlsx(path)
        if magic.startswith(b"\xd0\xcf\x11\xe0"):
            return _grid_xls(path)
        raise ValueError(f"{Path(path).name} is not an Excel workbook (signature {magic[:4]!r})")
    if ext == ".csv":
        return _grid_csv(path)
    raise ValueError(f"Unsupported file type {ext}")


def _txt(v):
    if v is None:
        return ""
    if isinstance(v, (datetime, date)):
        return v.strftime("%d-%b-%Y")
    return str(v).strip()


def _num(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("%", "").strip()
    if s in ("", "-", "--", "$", "#"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    try:
        x = float(s.strip("()"))
    except ValueError:
        return None
    return -x if neg else x


def find_date(text):
    """Find a portfolio date in free text → month-end date."""
    t = text.lower()
    pats = [
        (r"(\d{1,2})(?:st|nd|rd|th)?[\s\-./]+([a-z]{3})[a-z]*[\s\-.,/]+(\d{4})", "dmy_name"),
        (r"([a-z]{3})[a-z]*[\s\-.]+(\d{1,2})(?:st|nd|rd|th)?,?[\s\-]+(\d{4})", "mdy_name"),
        (r"(\d{1,2})[\-./](\d{1,2})[\-./](\d{4})", "dmy_num"),
        (r"(\d{4})-(\d{2})-(\d{2})", "ymd"),
        (r"\b([a-z]{3})[a-z]*[\s\-']+(\d{4})\b", "my_name"),
    ]
    for rx, kind in pats:
        for m in re.finditer(rx, t):
            try:
                if kind == "dmy_name" and m.group(2) in MONTHS:
                    return month_end(date(int(m.group(3)), MONTHS[m.group(2)], 1))
                if kind == "mdy_name" and m.group(1) in MONTHS:
                    return month_end(date(int(m.group(3)), MONTHS[m.group(1)], 1))
                if kind == "dmy_num":
                    return month_end(date(int(m.group(3)), int(m.group(2)), 1))
                if kind == "ymd":
                    return month_end(date(int(m.group(1)), int(m.group(2)), 1))
                if kind == "my_name" and m.group(1) in MONTHS and 2000 < int(m.group(2)) < 2100:
                    return month_end(date(int(m.group(2)), MONTHS[m.group(1)], 1))
            except ValueError:
                continue
    return None


def match_scheme(text, schemes):
    t = re.sub(r"\s+", " ", text.lower())
    best, score = None, 0
    for s in schemes:
        if any(x in t for x in s.get("exclude_sheet", [])):
            continue
        for grp in s["match_any"]:
            if all(k in t for k in grp):
                sc = sum(len(k) for k in grp)
                if sc > score:
                    best, score = s["scheme_id"], sc
    return best


def parse_sheet(title_text, rows):
    """Return (holdings, warnings) for one sheet grid, or (None, reason) if no portfolio table."""
    hdr_i, cols = None, {}
    hcell = lambda c: re.sub(r"\s+", " ", _txt(c)).lower()  # noqa: E731 - headers often wrap: "% to Net\n Assets"
    for i, r in enumerate(rows[:80]):
        cells = [hcell(c) for c in r]
        if any(c == "isin" or c.startswith("isin") or "isin code" in c or "isin no" in c for c in cells):
            hdr_i = i
            for j, c in enumerate(cells):
                if "isin" in c and "isin" not in cols:
                    cols["isin"] = j
                elif ("%" in c or "percent" in c or "weight" in c) and any(k in c for k in ("nav", "net asset", "aum", "portfolio", "weight", "total")) and "weight" not in cols:
                    cols["weight"] = j
                elif ("name" in c or "instrument" in c or "company" in c or "issuer" in c or "security" in c) and "name" not in cols:
                    cols["name"] = j
                elif ("industry" in c or "rating" in c or "sector" in c) and "industry" not in cols:
                    cols["industry"] = j
            break
    if hdr_i is None:
        return None, "no ISIN column"
    if "weight" not in cols:
        # header may be split across two rows ("% to" / "NAV")
        nxt = [hcell(c) for c in rows[hdr_i + 1]] if hdr_i + 1 < len(rows) else []
        for j, c in enumerate(nxt):
            if "nav" in c or "net asset" in c or "aum" in c:
                cols["weight"] = j
        if "weight" not in cols:
            return None, "no '% to NAV' column"
    out, warn = [], []
    for r in rows[hdr_i + 1:]:
        if len(r) <= max(cols.values()):
            r = list(r) + [None] * (max(cols.values()) + 1 - len(r))
        isin = _txt(r[cols["isin"]]).upper().replace(" ", "")
        if not ISIN_RE.match(isin):
            continue
        w = _num(r[cols["weight"]])
        if w is None:
            continue
        name = _txt(r[cols["name"]]) if "name" in cols else ""
        ind = _txt(r[cols["industry"]]) if "industry" in cols else ""
        if not isin_check_digit_ok(isin):
            warn.append(f"ISIN {isin} fails its check digit")
        out.append({"isin": isin, "name": name, "industry": ind, "weight": w})
    if not out:
        return None, "no holdings rows"
    tot = sum(x["weight"] for x in out)
    if max(abs(x["weight"]) for x in out) <= 1.0 and tot <= 1.5:
        for x in out:
            x["weight"] *= 100
        warn.append("weights given as fractions; converted to %")
    return out, warn


def classify(h):
    ind = (h.get("industry") or "").lower()
    if is_equity_isin(h["isin"]):
        return "equity"
    if not h["isin"].startswith("IN") and not any(w in ind for w in RATING_WORDS):
        return "foreign_equity"
    return "debt_other"


SCHEME_TITLE = re.compile(r"^\s*scheme\s*(name)?\s*:", re.I)


def blocks(sheet, rows):
    """(label, rows) for each portfolio in a sheet: the whole sheet, or one block per 'SCHEME:' title when several
    schemes are stacked in it. A block starts two rows above its title (scheme code / AMC name lines) and ends
    where the next block starts."""
    starts = [i for i, r in enumerate(rows) if r and SCHEME_TITLE.match(_txt(next((c for c in r if c not in (None, "")), "")))]
    if len(starts) < 2:
        return [(sheet, rows, False)]
    cut = [max(0, s - 2) for s in starts] + [len(rows)]
    cut[0] = 0
    return [(f"{sheet} · block {k + 1}", rows[cut[k]:cut[k + 1]], True) for k in range(len(starts))]


def parse_file(path, schemes):
    """Parse every sheet (or every stacked scheme block) of one file. Returns a list of results."""
    results = []
    try:
        for sheet_name, sheet_rows in grids(path):
          for sheet, rows, stacked in blocks(sheet_name, sheet_rows):
            head = " ".join(_txt(c) for r in rows[:12] for c in r if c is not None)
            text = f"{Path(path).stem} {sheet} {head}"
            sid = match_scheme(head if stacked else text, schemes)  # a block is named by its own title, not the file's
            if stacked and not sid:
                continue  # one of the AMC's other schemes
            holdings, info = parse_sheet(head, rows)
            if holdings is None:
                continue
            pdate = find_date(head) or find_date(Path(path).stem) or find_date(sheet)
            for h in holdings:
                h["class"] = classify(h)
            eq = sum(h["weight"] for h in holdings if h["class"] in ("equity", "foreign_equity"))
            other = sum(h["weight"] for h in holdings if h["class"] == "debt_other")
            tot = eq + other
            warnings = list(info)
            if not sid:
                warnings.append("scheme not recognised; assign it before applying")
            if not pdate:
                warnings.append("portfolio date not found; assign it before applying")
            if tot > 101.5:
                warnings.append(f"weights add up to {tot:.1f}% (sub-totals may have been read as holdings)")
            results.append({"file": Path(path).name, "sheet": sheet, "scheme_id": sid, "portfolio_date": pdate.isoformat() if pdate else None,
                            "holdings": holdings, "n": len(holdings), "equity_pct": round(eq, 4), "debt_other_pct": round(other, 4),
                            "listed_total_pct": round(tot, 4), "title": head[:160], "warnings": warnings})
    except Exception as e:  # noqa: BLE001
        log.warning("Could not read %s: %s", path, e)
        results.append({"file": Path(path).name, "sheet": None, "error": str(e), "warnings": [str(e)]})
    return results


def scan_folder(folder, schemes):
    out = []
    for p in sorted(Path(folder).glob("*")):
        if p.suffix.lower() in (".xlsx", ".xlsm", ".xls", ".csv") and not p.name.startswith("~$"):
            out.extend(parse_file(p, schemes))
    return out
