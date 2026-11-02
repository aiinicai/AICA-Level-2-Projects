"""Structured model of the financial statements under review.

Turns an uploaded workbook (or text PDF) into located line items, so that every check can
(1) establish applicability from the company's own figures before it runs, and
(2) cite exact evidence - sheet / page, row, caption and current / previous year amounts.

Also infers the entity profile from the statements themselves (framework, Schedule III division,
private / public / listed from the CIN, reporting date, rounding unit, small company status), so a
wrong sidebar selection cannot drive the review.
"""

import io
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

ERROR_VALUES = ("#REF!", "#DIV/0!", "#VALUE!", "#N/A", "#NAME?", "#NUM!", "#NULL!")
_YEAR_HDR = re.compile(r"(?:31(?:st)?[\s\-]*mar(?:ch)?[\s,\-]*|march\s+31,?\s*|year\s+ended\s+.*?)(20\d{2})", re.I)
_YEAR_ONLY = re.compile(r"\b(20\d{2})\b")
_NOTE_REF = re.compile(r"^\s*(?:note\s*)?(\d{1,2}(?:\.\d{1,2})?|[1-9]\d?\s*[a-z]?)\s*$", re.I)


@dataclass
class Line:
    sheet: str
    row: int
    label: str
    cy: Optional[float] = None
    py: Optional[float] = None
    note: str = ""
    numbers: List[float] = field(default_factory=list)
    raw: List[Any] = field(default_factory=list)
    section: str = ""

    @property
    def loc(self) -> str:
        return f"{self.sheet}, row {self.row}" if self.row else self.sheet

    def cite(self, unit: str = "") -> str:
        parts = []
        if self.cy is not None:
            parts.append(f"CY {self.cy:,.2f}")
        if self.py is not None:
            parts.append(f"PY {self.py:,.2f}")
        amt = f" - {', '.join(parts)}" if parts else ""
        note = f" (Note {self.note})" if self.note else ""
        return f"{self.loc}: \"{self.label}\"{note}{amt}{(' ' + unit) if unit and parts else ''}"


class _Cell:
    """Minimal cell (value, column, row, coordinate) built from streamed read-only rows."""
    __slots__ = ("value", "column", "row")

    def __init__(self, value: Any, column: int, row: int) -> None:
        self.value, self.column, self.row = value, column, row

    @property
    def coordinate(self) -> str:
        from openpyxl.utils import get_column_letter
        return f"{get_column_letter(self.column)}{self.row}"


_ENUM = re.compile(r"^\s*(?:[IVX]{1,4}\.?|\(?[a-h]\)|\(?[ivx]{1,4}\)|\(?[A-H]\)|\d{1,2}[.)]?|[-–•*])\s+")


def _clean_label(label: str) -> str:
    """Drops Schedule III enumerators such as 'II.', '(a)', '(iii)', '1' from the start of a caption."""
    prev = None
    label = label.strip()
    while prev != label:
        prev, label = label, _ENUM.sub("", label, count=1).strip()
    return label


def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        m = re.fullmatch(r"\(?(-?\d+(?:\.\d+)?)\)?", s)
        if m:
            val = float(m.group(1))
            return -abs(val) if s.startswith("(") else val
    return None


class FSModel:
    """Located line items + inferred profile for one set of financial statements."""

    def __init__(self) -> None:
        self.lines: List[Line] = []
        self.texts: List[Tuple[str, int, str]] = []        # (sheet, row, text) for narrative search
        self.errors: List[Tuple[str, str, str]] = []       # (sheet, cell, error value)
        self.sheet_titles: Dict[str, str] = {}
        self.year_end: Optional[int] = None
        self.unit = ""
        self.unit_factor = 1.0
        self.profile: Dict[str, Any] = {}
        self.full_text = ""

    # ------------------------------------------------------------------ build
    @classmethod
    def from_bytes(cls, data: bytes, filename: str, pages: Optional[List[Dict[str, Any]]] = None) -> "FSModel":
        m = cls()
        if filename.lower().endswith((".xlsx", ".xlsm")):
            m._load_excel(data)
        else:
            m._load_text_pages(pages or [])
        m._infer_profile()
        return m

    def _load_excel(self, data: bytes) -> None:
        import openpyxl
        # read-only (streaming) mode keeps memory low; links to other workbooks are not needed for reading values
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True, keep_links=False)
        chunks = []
        for ws in wb.worksheets:
            if re.search(r"trial\s*balance|\btb\b|working|mapping", ws.title, re.I):
                continue                     # internal workings are not part of the published statements
            cy_col = py_col = note_col = None
            section = ""
            ws.reset_dimensions()            # stored sheet dimensions are often wrong; read every row
            for r_idx, values in enumerate(ws.iter_rows(min_row=1, min_col=1, values_only=True), start=1):
                row = [_Cell(v, c_idx, r_idx) for c_idx, v in enumerate(values, start=1)]
                if not row:
                    continue
                cells = [c for c in row if c.value is not None and str(c.value).strip() != ""]
                if not cells:
                    continue
                for c in cells:
                    if isinstance(c.value, str) and c.value.strip() in ERROR_VALUES:
                        self.errors.append((ws.title, c.coordinate, c.value.strip()))
                texts = list(dict.fromkeys(re.sub(r"\s+", " ", str(c.value)).strip() for c in cells
                                           if isinstance(c.value, str) and _num(c.value) is None))
                row_text = " | ".join(str(c.value).strip() for c in cells)
                chunks.append(f"[{ws.title} r{row[0].row}] {row_text}")
                for t in texts:
                    if len(t) > 3:
                        self.texts.append((ws.title, row[0].row, t))
                # header rows define which columns hold the current and previous year
                year_cells = [(c.column, int(_YEAR_HDR.search(str(c.value)).group(1)))
                              for c in cells if isinstance(c.value, str) and _YEAR_HDR.search(str(c.value))]
                if len(year_cells) >= 2:
                    year_cells.sort(key=lambda x: x[0])
                    cy_col, py_col = year_cells[0][0], year_cells[1][0]
                    for c in cells:
                        if isinstance(c.value, str) and re.search(r"note", c.value, re.I) and len(c.value) < 20:
                            note_col = c.column
                    continue
                if ws.title not in self.sheet_titles and texts:
                    self.sheet_titles[ws.title] = texts[0]
                label = _clean_label(" ".join(t for t in texts if not t.startswith("#"))[:200])
                if (label and re.fullmatch(r"[A-Z\s&'’,()\-]{4,}", label.strip()) and len(label) < 60
                        and not label.strip().startswith("TOTAL")):
                    section = label.strip()
                nums = [(c.column, _num(c.value)) for c in cells if _num(c.value) is not None]
                cy = py = None
                note = ""
                if cy_col:
                    by_col = dict(nums)
                    cy, py = by_col.get(cy_col), by_col.get(py_col)
                    if note_col and by_col.get(note_col) is not None:
                        note = str(int(by_col[note_col])) if float(by_col[note_col]).is_integer() else str(by_col[note_col])
                    for c in cells:
                        if note_col and c.column == note_col and isinstance(c.value, str) and _NOTE_REF.match(c.value):
                            note = _NOTE_REF.match(c.value).group(1)
                embedded = re.search(r"\b(?:note|refer note)\s*(?:no\.?\s*)?(\d{1,2}(?:\.\d{1,2})?)\b", label, re.I)
                if embedded and not note:
                    note = embedded.group(1)
                    label = label.replace(embedded.group(0), "").strip(" -|")
                if cy is None and py is None and nums:
                    # rows outside a dated header block (e.g. ratio workings): first two amounts, ignoring a serial number
                    vals = [n for _, n in nums]
                    if _num(cells[0].value) is not None and float(vals[0]).is_integer() and 0 < vals[0] <= 40 and len(vals) > 1:
                        vals = vals[1:]
                    cy, py = vals[0], (vals[1] if len(vals) > 1 else None)
                if label:
                    self.lines.append(Line(ws.title, row[0].row, label, cy, py, note,
                                           [n for _, n in nums], [c.value for c in cells], section))
        wb.close()
        self.full_text = "\n".join(chunks)

    def _load_text_pages(self, pages: List[Dict[str, Any]]) -> None:
        chunks = []
        headings = [(r"statement\s+of\s+cash\s+flows?|cash\s+flow\s+statement", "Cash Flow Statement"),
                    (r"statement\s+of\s+changes\s+in\s+equity", "Statement of Changes in Equity"),
                    (r"statement\s+of\s+profit\s+and\s+loss|profit\s+and\s+loss\s+account", "Statement of Profit and Loss"),
                    (r"balance\s+sheet\s+as\s+at", "Balance Sheet")]
        for p in pages:
            sheet = p.get("sheet_name") or f"Page {p.get('page_num')}"
            head = (p.get("text", "") or "")[:600]
            for rx, title in headings:
                if re.search(rx, head, re.I) and not re.search(r"notes?\s+(to|forming)", head[:200], re.I):
                    self.sheet_titles[sheet] = title
                    break
            for i, raw in enumerate(p.get("text", "").splitlines(), start=1):
                s = raw.strip()
                if not s:
                    continue
                chunks.append(f"[{sheet} l{i}] {s}")
                self.texts.append((sheet, i, s))
                m = re.match(r"^(.*?[A-Za-z].*?)\s+((?:\(?-?[\d,]+(?:\.\d+)?\)?\s*){1,4})$", s)
                if m:
                    vals = [_num(v) for v in m.group(2).split()]
                    vals = [v for v in vals if v is not None]
                    note = ""
                    if len(vals) >= 3 and vals[0] is not None and float(vals[0]).is_integer() and abs(vals[0]) < 60:
                        note, vals = str(int(vals[0])), vals[1:]
                    cy = vals[-2] if len(vals) >= 2 else vals[0] if vals else None
                    py = vals[-1] if len(vals) >= 2 else None
                    self.lines.append(Line(sheet, i, m.group(1).strip()[:160], cy, py, note, vals))
        self.full_text = "\n".join(chunks)

    # ------------------------------------------------------------------ profile
    def _infer_profile(self) -> None:
        t = self.full_text
        p: Dict[str, Any] = {}
        cin = re.search(r"\b([LU])(\d{5})([A-Z]{2})(\d{4})(PLC|PTC|OPC|NPL|GOI|SGC|FLC|GAP|ULL|ULT)(\d{6})\b", t)
        if cin:
            p["cin"] = cin.group(0)
            p["listed"] = cin.group(1) == "L"
            p["company_type"] = "Private Company" if cin.group(5) in ("PTC", "OPC") else "Public Company"
            p["one_person_company"] = cin.group(5) == "OPC"
        elif re.search(r"\bprivate\s+limited\b|\bpvt\.?\s*ltd\b", t, re.I):
            p["company_type"] = "Private Company"
            p["listed"] = False
        ind_as = len(re.findall(r"\bInd\s?AS\b|other comprehensive income|\bother equity\b", t, re.I))
        legacy = len(re.findall(r"reserves\s+and\s+surplus|shareholders[’']?\s+funds|accounting\s+standard\s*[-–]?\s*\d|\bAS[\s-]\d{1,2}\b|indian gaap", t, re.I))
        if ind_as or legacy:
            p["framework"] = "Indian Accounting Standards (Ind AS)" if ind_as > legacy else "Accounting Standards (AS)"
            p["framework_evidence"] = f"{ind_as} Ind AS indicators vs {legacy} AS indicators"
        if re.search(r"non[- ]banking financial|\bNBFC\b", t, re.I) and p.get("framework", "").startswith("Indian"):
            p["schedule_iii_division"] = "Division III"
        elif p.get("framework"):
            p["schedule_iii_division"] = "Division II" if p["framework"].startswith("Indian") else "Division I"
        years = [int(y) for y in re.findall(r"(?:balance sheet as at|as at)\s+31(?:st)?\s*march,?\s*(20\d{2})", t, re.I)]
        years += [int(y) for y in re.findall(r"(?:balance sheet as at|as at)\s+march\s+31,?\s*(20\d{2})", t, re.I)]
        if years:
            self.year_end = max(years)
            p["financial_year"] = f"FY {self.year_end - 1}-{str(self.year_end)[2:]}"
        unit_m = re.search(r"(?:amt\.?|amount|figures|rs\.?|₹|inr)[^\n]{0,25}?(?:in\s+)?(?:rs\.?|₹|inr)?\s*[‘'’]?\s*(000|thousands?|lakhs?|lacs?|crores?|millions?)", t, re.I)
        if unit_m:
            u = unit_m.group(1).lower()
            self.unit, self.unit_factor = (("Rs '000", 1e3) if u.startswith(("000", "thousand")) else
                                           ("Rs lakhs", 1e5) if u.startswith(("lakh", "lac")) else
                                           ("Rs crores", 1e7) if u.startswith("crore") else ("Rs million", 1e6))
        p["unit"] = self.unit or "not stated"
        revenue = self.amount(r"^revenue\s+from\s+operations", statement="pl")
        capital = self.amount(r"^(equity\s+)?share\s+capital$|^\(?a?\)?\s*share\s+capital", statement="bs")
        if revenue is not None and capital is not None and self.unit_factor:
            rev_rs, cap_rs = revenue * self.unit_factor, capital * self.unit_factor
            p["turnover_rs"], p["paid_up_capital_rs"] = rev_rs, cap_rs
            # Section 2(85) small company (thresholds as amended w.e.f. 15.09.2022)
            p["small_company"] = (p.get("company_type") == "Private Company" and cap_rs <= 4e7 and rev_rs <= 4e8)
            # Companies (Accounting Standards) Rules, 2021 - Small and Medium-sized Company
            p["smc"] = (not p.get("listed", False) and rev_rs <= 2.5e9)
        self.profile = p

    # ------------------------------------------------------------------ queries
    def statement_of(self, line: Line) -> str:
        title = (line.sheet + " " + self.sheet_titles.get(line.sheet, "")).lower()
        if re.search(r"balance\s*sheet|financial position", title):
            return "bs"
        if re.search(r"profit|loss|income statement", title) and not re.search(r"note", title):
            return "pl"
        if re.search(r"cash\s*_?flow", title):
            return "cf"
        if re.search(r"changes in equity|soce", title):
            return "soce"
        return "notes"

    def find(self, pattern: str, statement: Optional[str] = None, with_amount: bool = False) -> List[Line]:
        rx = re.compile(pattern, re.I)
        out = []
        for ln in self.lines:
            if statement and self.statement_of(ln) != statement:
                continue
            if with_amount and ln.cy is None and ln.py is None:
                continue
            if rx.search(ln.label.strip()):
                out.append(ln)
        return out

    def first(self, pattern: str, statement: Optional[str] = None) -> Optional[Line]:
        hits = self.find(pattern, statement, with_amount=True)
        return hits[0] if hits else None

    def amount(self, pattern: str, statement: Optional[str] = None, year: str = "cy") -> Optional[float]:
        ln = self.first(pattern, statement)
        return getattr(ln, year) if ln else None

    def has_value(self, pattern: str, statement: Optional[str] = None) -> Optional[Line]:
        for ln in self.find(pattern, statement, with_amount=True):
            if (ln.cy or 0) != 0 or (ln.py or 0) != 0:
                return ln
        return None

    def text_hits(self, pattern: str, limit: int = 5) -> List[Tuple[str, int, str]]:
        rx = re.compile(pattern, re.I)
        return [t for t in self.texts if rx.search(t[2])][:limit]

    def mentions(self, pattern: str) -> bool:
        return bool(re.search(pattern, self.full_text, re.I))
