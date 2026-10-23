"""Write a Model to Word (.docx) and Excel (.xlsx).

One font family and size throughout, dates as dd/mm/yyyy, negatives in brackets, so the output
passes our own formatting checker (daybook_auditor.fs_format).
"""
from __future__ import annotations

import contextvars
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.hyperlink import Hyperlink

from .format import UNITS, as_unit, dmy
from .model import Model

FONT, SIZE = "Times New Roman", 10
GREY = RGBColor(0x59, 0x59, 0x59)
# The presentation unit in force while a file is being written (Schedule III requires rounding off; one unit throughout).
_UNIT: contextvars.ContextVar = contextvars.ContextVar("unit", default=UNITS["rupees"])


def _unit_line() -> str:
    return f"({_UNIT.get().heading})"
DRAFT = "DRAFT: generated from Tally data for review. Unaudited. Items marked [R#] need a reviewer's decision."


def _marker(flags: list) -> str:
    return f"  [{', '.join(flags)}]" if flags else ""


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


# =============================== Word ===================================================

def _run(p, text, bold=False, italic=False, size=SIZE, color=None):
    r = p.add_run(text)
    r.font.name, r.font.size, r.bold, r.italic = FONT, Pt(size), bold, italic
    r._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    if color is not None:
        r.font.color.rgb = color
    return r


def _para(doc, text="", bold=False, italic=False, size=SIZE, align=None, space_after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    if align is not None:
        p.alignment = align
    if text:
        _run(p, text, bold, italic, size)
    return p


_bookmark_ids = iter(range(1, 10_000))


def _bookmark(paragraph, name):
    """Mark a paragraph as a link target (Word bookmark)."""
    i = str(next(_bookmark_ids))
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), i)
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), i)
    p = paragraph._p
    p.insert(1 if p.pPr is not None else 0, start)
    p.append(end)


def _hyperlink(paragraph, text, anchor, bold=False, size=SIZE):
    """Clickable text that jumps to a bookmark in the same document."""
    h = OxmlElement("w:hyperlink")
    h.set(qn("w:anchor"), anchor)
    h.set(qn("w:history"), "1")
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(a), FONT)
    rpr.append(fonts)
    if bold:
        rpr.append(OxmlElement("w:b"))
    colour = OxmlElement("w:color")
    colour.set(qn("w:val"), "1F4E79")
    rpr.append(colour)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), str(int(size * 2)))
    rpr.append(sz)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    rpr.append(underline)
    r.append(rpr)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    r.append(t)
    h.append(r)
    paragraph._p.append(h)


def _link_cell(cell, text, width, anchor, bookmark):
    """A right-aligned table cell holding a link to `anchor`; the cell itself is a target named `bookmark`."""
    cell.width = Inches(width)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(1)
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _hyperlink(p, text, anchor)
    _bookmark(p, bookmark)


def _shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def _cell(cell, text, width, bold=False, italic=False, right=False, indent=0.0, marker=""):
    cell.width = Inches(width)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.left_indent = Inches(indent)
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if right else WD_ALIGN_PARAGRAPH.LEFT
    _run(p, text, bold, italic)
    if marker:
        _run(p, marker, italic=True, color=GREY)


def _table(doc, widths):
    t = doc.add_table(rows=0, cols=len(widths))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    return t


def _money_cells(row_cells, values, widths, bold):
    for c, v, w in zip(row_cells, values, widths):
        _cell(c, v if isinstance(v, str) else _UNIT.get().fmt(v), w, bold=bold, right=True)


def _statement_table(doc, rows, headers, prev_col=True, note_col=True, linkable=frozenset()):
    if note_col:
        widths = [3.4, 0.5, 1.3, 1.3] if prev_col else [3.4, 0.5, 1.5, 1.2]
    else:
        widths = [4.0, 1.2, 1.2]
    t = _table(doc, widths)
    for i, (c, h, w) in enumerate(zip(t.add_row().cells, headers, widths)):
        _cell(c, h, w, bold=True, right=i > 0)
        _shade(c, "D9E2F3")
    for r in rows:
        if r.kind == "blank":
            continue
        cells = t.add_row().cells
        bold = r.kind in ("head", "sub", "total")
        indent = {"item": 0.15, "subitem": 0.35}.get(r.kind, 0.0)
        _cell(cells[0], r.label, widths[0], bold=bold, indent=indent, marker=_marker(r.flags))
        k = 1
        if note_col:
            if r.note and r.note in linkable:
                _link_cell(cells[1], str(r.note), widths[1], f"note_{r.note}", f"face_{r.note}")
            else:
                _cell(cells[1], str(r.note) if r.note else "", widths[1], right=True)
            k = 2
        if r.kind in ("head", "sub") or (r.cur is None and r.prev is None and r.kind == "item" and not r.note):
            for c, w in zip(cells[k:], widths[k:]):
                _cell(c, "", w)
        else:
            vals = [r.cur, r.prev] if prev_col else [r.cur, "-"]
            _money_cells(cells[k:], vals, widths[k:], bold)
        if r.kind == "head":
            for c in cells:
                _shade(c, "F2F2F2")
    return t


def _note_table(doc, header, rows, total, widths=None):
    n = len(header)
    first = 2.6 if n > 3 else 3.4
    rest = (6.4 - first) / (n - 1)
    widths = widths or [first] + [rest] * (n - 1)
    t = _table(doc, widths)
    cells = t.add_row().cells
    for i, (c, h, w) in enumerate(zip(cells, header, widths)):
        _cell(c, h, w, bold=True, right=i > 0)
        _shade(c, "D9E2F3")
    for r in rows:
        cells = t.add_row().cells
        if len(r) == 1:  # sub-heading row
            _cell(cells[0], r[0], widths[0], bold=True)
            for c, w in zip(cells[1:], widths[1:]):
                _cell(c, "", w)
            continue
        _cell(cells[0], r[0], widths[0])
        _money_cells(cells[1:], [(v if v is not None else "-") for v in r[1:]], widths[1:], False)
    if total:
        cells = t.add_row().cells
        _cell(cells[0], total[0], widths[0], bold=True)
        _money_cells(cells[1:], total[1:], widths[1:], True)
    return t


def _text_table(doc, header, rows, rel_widths, total_width=6.9):
    """A wrapped table of words (the disclosures); rel_widths are relative column widths."""
    k = total_width / sum(rel_widths)
    widths = [w * k for w in rel_widths]
    t = _table(doc, widths)
    for c, h, w in zip(t.add_row().cells, header, widths):
        _cell(c, h, w, bold=True)
        _shade(c, "D9E2F3")
    for r in rows:
        for c, v, w in zip(t.add_row().cells, r, widths):
            _cell(c, v, w)
    return t


def _build_docx(m: Model, path: Path) -> Path:
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Inches(0.8)
        s.top_margin = s.bottom_margin = Inches(0.8)
        hp = s.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(hp, DRAFT, italic=True, size=8, color=GREY)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = FONT, Pt(SIZE)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    _para(doc, m.company, True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
    _para(doc, f"Balance Sheet as at {dmy(m.as_at)}", True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
    _para(doc, _unit_line(), italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    linkable = {n.no for n in m.notes}
    _statement_table(doc, m.bs, ["Particulars", "Note", f"As at {dmy(m.as_at)}", f"As at {dmy(m.prev_as_at)}"],
                     linkable=linkable)
    _para(doc, "The accompanying notes form an integral part of these financial statements.", italic=True)
    _doc_signatures(doc, m)

    doc.add_page_break()
    _para(doc, m.company, True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
    _para(doc, f"Statement of Profit and Loss for the year ended {dmy(m.as_at)}", True, size=12,
          align=WD_ALIGN_PARAGRAPH.CENTER)
    _para(doc, _unit_line(), italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    _statement_table(doc, m.pl, ["Particulars", "Note", f"Year ended {dmy(m.as_at)}", f"Year ended {dmy(m.prev_as_at)}"],
                     prev_col=False, linkable=linkable)
    _para(doc, "Previous-year figures for the statement of profit and loss were not loaded; see open item O1.",
          italic=True)
    _doc_signatures(doc, m)

    doc.add_page_break()
    _para(doc, m.company, True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER)
    _para(doc, f"Cash Flow Statement for the year ended {dmy(m.as_at)}", True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
    _para(doc, _unit_line() + ". Prepared under AS 3 (indirect method).", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    _statement_table(doc, m.cashflow, ["Particulars", f"Year ended {dmy(m.as_at)}", f"Year ended {dmy(m.prev_as_at)}"],
                     prev_col=False, note_col=False)
    _para(doc, "")
    _note_table(doc, ["Cash and cash equivalents comprise:", f"As at {dmy(m.as_at)}", f"As at {dmy(m.prev_as_at)}"], m.cce,
                ["Total", sum(r[1] for r in m.cce), sum(r[2] for r in m.cce)])
    _para(doc, "")
    _para(doc, "Basis of the cash flow statement", True, space_after=2)
    for text in m.cf_notes:
        _para(doc, f"• {text}", space_after=1)
    _doc_signatures(doc, m)

    doc.add_page_break()
    _para(doc, "Notes forming part of the financial statements", True, size=12)
    for n in m.notes:
        title = _para(doc, f"Note {n.no}: {n.title}", True, space_after=2)
        _bookmark(title, f"note_{n.no}")
        if n.kind != "text":                  # the ratios note has no statement line to go back to
            _hyperlink(title, "   ↩ back to the statement", f"face_{n.no}")
        _note_table(doc, n.header, n.rows, n.total, [1.8, 0.8, 0.8, 0.7, 2.3] if n.kind == "text" else None)
        if n.comment:
            _para(doc, n.comment, italic=True)
        if n.movement:
            mv = n.movement
            _para(doc, mv["title"], True, space_after=2)
            _note_table(doc, mv["header"], mv["rows"], mv["total"], [1.9, 2.3, 2.2] if n.kind == "text" else None)
            _para(doc, mv["comment"], italic=True)
        if n.gaps:
            _para(doc, "Information required (not available in Tally):", italic=True, space_after=1)
            for g in n.gaps:
                _para(doc, f"• {g}", space_after=1)
        _para(doc, "")

    if m.disclosures:
        doc.add_page_break()
        _para(doc, "Additional regulatory information and other statutory disclosures", True, size=12)
        _para(doc, "Schedule III, Division I, the Companies Act 2013 and the accounting standards ask for disclosures that a Tally trial "
                   "balance only partly holds. Where the books show a fact it is stated and its source given; where only management can "
                   "answer, the cell says so. A blank or bracketed cell is not a statement that the item is nil.", italic=True)
        for d in m.disclosures:
            _para(doc, f"{d.no}. {d.title}", True, space_after=0)
            _para(doc, d.ref, italic=True, space_after=2)
            _text_table(doc, d.header, d.rows, d.widths or [1] * len(d.header))
            if d.comment:
                _para(doc, d.comment, italic=True)
            _para(doc, "")
        _doc_signatures(doc, m)

    doc.add_page_break()
    _para(doc, "Open items for the reviewer", True, size=12)
    _para(doc, "Classification judgements [R#] mark ledgers where the mapping to Schedule III depends on facts "
               "Tally does not hold. Observations [O#] are matters visible from the numbers alone.")
    widths = [0.5, 1.3, 1.3, 0.9, 2.4]
    t = _table(doc, widths)
    for c, h, w in zip(t.add_row().cells, ["Ref", "Area", "Ledger", "Amount", "Matter"], widths):
        _cell(c, h, w, bold=True)
        _shade(c, "D9E2F3")
    for f in m.flags:
        cells = t.add_row().cells
        _cell(cells[0], f.ref, widths[0])
        _cell(cells[1], f.area, widths[1])
        _cell(cells[2], f.ledger or "-", widths[2])
        _cell(cells[3], _UNIT.get().fmt(f.amount), widths[3], right=True)
        _cell(cells[4], f.text, widths[4])
    _para(doc, "")
    _para(doc, "General disclosures still to be prepared", True, space_after=2)
    for g in m.general_gaps:
        _para(doc, f"• {g}", space_after=1)
    if m.basis:
        _para(doc, "")
        _para(doc, "Basis of preparation: adjustments and warnings", True, space_after=2)
        _para(doc, f"Amounts are rounded to the nearest rupee. {m.company} figures are taken from the Tally trial "
                   f"balance for the period ending {dmy(m.as_at)}.")
        for b in m.basis:
            _para(doc, f"• {b}", space_after=1)
    doc.save(path)
    return path


# =============================== Excel ==================================================
# The face of every statement is linked to the notes: a figure with a note is a formula that reads the
# note's total, so a change in a note flows through. Totals and subtotals are formulas as well.

BLANK = "______________"


def sign_lines(m):
    """(left, right) lines of the signature block: the auditors, and the Board of the company."""
    from .model import Signatories
    s = m.sign or Signatories()
    d = list(s.directors) + [("", ""), ("", "")]
    day = lambda x: dmy(x) if x else BLANK        # noqa: E731
    left = [f"For {s.firm or BLANK}", "Chartered Accountants", f"Firm Registration No.: {s.frn or BLANK}", "",
            f"Partner: {s.partner or BLANK}", f"Membership No.: {s.membership or BLANK}", f"Place: {s.place or BLANK}",
            f"Date of signing: {day(s.sign_date)}"]
    right = ["For and on behalf of the Board of Directors of", s.company or m.company, "",
             f"Director: {d[0][0] or BLANK}", f"DIN: {d[0][1] or BLANK}", f"Director: {d[1][0] or BLANK}", f"DIN: {d[1][1] or BLANK}",
             f"Date of signing: {day(s.board_date)}"]
    return left, right


def _doc_signatures(doc, m):
    left, right = sign_lines(m)
    _para(doc, "")
    t = doc.add_table(rows=1, cols=2)
    t.autofit = False
    keep = OxmlElement("w:cantSplit")                 # the block moves to the next page whole rather than splitting
    t.rows[0]._tr.get_or_add_trPr().append(keep)
    for cell, lines in zip(t.rows[0].cells, (left, right)):
        cell.width = Inches(3.4)
        first = True
        for i, line in enumerate(lines):
            p = cell.paragraphs[0] if first else cell.add_paragraph()
            first = False
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.keep_with_next = True
            _run(p, line, bold=i == 0)


def _xl_signatures(ws, m, r, right_col="C"):
    left, right = sign_lines(m)
    for i, (a, b) in enumerate(zip(left, right)):
        if a:
            _x(ws, f"A{r + i}", a, bold=i == 0)
        if b:
            _x(ws, f"{right_col}{r + i}", b, bold=i == 0)
    return r + len(left)


THIN = Side(style="thin", color="808080")
LINK_COLOUR = "1F4E79"
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
SHEET_ORDER = ["Balance Sheet", "P&L", "Cash Flow", "Notes", "Disclosures", "AI analysis", "Open items", "Mapping"]


class Book:
    """Keeps the value of every formula cell so viewers that do not calculate (previews, some mail clients) still
    show numbers. Excel recalculates everything on open regardless."""

    def __init__(self):
        self.cache: dict[str, dict[str, float]] = {}

    def fx(self, ws, ref, formula, value, **style):
        c = _x(ws, ref, formula, **style)
        self.cache.setdefault(ws.title, {})[ref] = _UNIT.get().value(value)
        return c


def _x(ws, ref, value, bold=False, italic=False, size=SIZE, num=False, indent=0, fill=None, top=False, wrap=False,
       right=False):
    c = ws[ref]
    c.value = _UNIT.get().value(value) if num and isinstance(value, (int, float)) and not isinstance(value, bool) else value
    c.font = Font(name=FONT, size=size, bold=bold, italic=italic)
    if num:
        c.number_format = _UNIT.get().number_format
    c.alignment = Alignment(horizontal="right" if (num or right) else "left", indent=indent, wrap_text=wrap,
                            vertical="top")
    if fill:
        c.fill = PatternFill("solid", fgColor=fill)
    if top:
        c.border = Border(top=THIN)
    return c


def _link(ws, ref, text, sheet, target_ref, right=False, bold=False):
    """A cell that jumps to another place in the workbook."""
    c = ws[ref]
    c.value = text
    c.hyperlink = Hyperlink(ref=ref, location=f"'{sheet}'!{target_ref}", display=str(text))
    c.font = Font(name=FONT, size=SIZE, bold=bold, underline="single", color=LINK_COLOUR)
    c.alignment = Alignment(horizontal="right" if right else "left", vertical="top")
    return c


def _sheet_setup(ws, widths):
    for col, w in zip("ABCDEFGHIJ", widths):
        ws.column_dimensions[col].width = w
    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def _sum_formula(col: str, rows: list[int]) -> str:
    if len(rows) == 1:
        return f"={col}{rows[0]}"
    if rows == list(range(rows[0], rows[-1] + 1)):
        return f"=SUM({col}{rows[0]}:{col}{rows[-1]})"
    return "=SUM(" + ",".join(f"{col}{r}" for r in rows) + ")"


def _xl_notes(wb, m, book):
    """Notes sheet. Returns {note no: {"title": row, "total": row}} so the statements can link to it."""
    ws = wb.create_sheet("Notes")
    _sheet_setup(ws, [50, 17, 17, 17, 17, 22])
    _x(ws, "A1", "Notes forming part of the financial statements", True, size=12)
    pos, r = {}, 3
    for n in m.notes:
        title_row = r
        _x(ws, f"A{r}", f"Note {n.no}: {n.title}", True)
        r += 1
        for col, h in zip("ABCDE", n.header):
            _x(ws, f"{col}{r}", h, True, fill="D9E2F3", right=col != "A")
        r += 1
        counted = []
        for row in n.rows:
            _x(ws, f"A{r}", row[0], bold=len(row) == 1, indent=0 if len(row) == 1 else 1)
            for col, v in zip("BCDE", row[1:]):
                _x(ws, f"{col}{r}", v if v is not None else "-", num=v is not None, right=True)
            if len(row) > 1 and not row[0].startswith(("Opening", "Add")):
                counted.append(r)
            r += 1
        if n.total:
            _x(ws, f"A{r}", n.total[0], True, top=True)
            for i, col in enumerate("BCDE"[:len(n.total) - 1]):
                book.fx(ws, f"{col}{r}", _sum_formula(col, counted), n.total[i + 1], bold=True, num=True, top=True)
            pos[n.no] = {"title": title_row, "total": r}
            r += 1
        if n.movement:
            mv = n.movement
            r += 1
            _x(ws, f"A{r}", mv["title"], True)
            r += 1
            for col, h in zip("ABCDE", mv["header"]):
                _x(ws, f"{col}{r}", h, True, fill="D9E2F3", right=col != "A")
            r += 1
            first = r
            for row in mv["rows"]:
                _x(ws, f"A{r}", row[0], indent=1)
                for col, v in zip("BCDE", row[1:]):
                    _x(ws, f"{col}{r}", v, num=True, right=True)
                r += 1
            if mv["total"]:
                _x(ws, f"A{r}", mv["total"][0], True, top=True)
                for i, col in enumerate("BCDE"):
                    book.fx(ws, f"{col}{r}", f"=SUM({col}{first}:{col}{r - 1})", mv["total"][i + 1], bold=True, num=True, top=True)
                r += 1
        for text in ([n.comment] if n.comment else []) + (["Information required (not available in Tally):"] if n.gaps else []):
            _x(ws, f"A{r}", text, italic=True)
            r += 1
        for g in n.gaps:
            _x(ws, f"A{r}", f"• {g}", indent=1)
            r += 1
        r += 1
    return ws, pos


def _xl_ai(wb, m):
    """The reviewer's ratio analysis and the AI's remarks, in the same workbook, for reading beside the statements."""
    from .reviewer.ratios import fmt_value, fmt_variance
    rv = m.review
    ws = wb.create_sheet("AI analysis")
    _sheet_setup(ws, [34, 18, 18, 12, 10, 90, 34, 12])
    _x(ws, "A1", "Ratio analysis and AI remarks", True, size=12)
    ran = bool(getattr(rv, "ai_requested", False))
    _x(ws, "A2", ("AI review run. Reasons marked 'AI draft' and the observations below are drafts for the reviewer to confirm with management; "
                  "the model saw figures and labels only and cited the facts it relied on.") if ran else
       "AI review not run for this file. The ratios below are computed by code; each reason over 25% is left for management. "
       "Run the AI review on the statements page and download again to add the AI remarks.", italic=True)
    r = 4
    _x(ws, f"A{r}", "Schedule III ratios (ICAI Guidance Note, Annexure B)", True)
    r += 1
    for col, h in zip("ABCDEFG", ["Ratio", "Current year", "Previous year", "% change", "Over 25%", "Reason for change / note", "Source of the reason"]):
        _x(ws, f"{col}{r}", h, True, fill="D9E2F3", wrap=True)
    r += 1
    for x in rv.ratios:
        reason = x.explanation if x.flagged else (x.note or "")
        vals = [x.name, fmt_value(x, x.cur), fmt_value(x, x.prev), fmt_variance(x.variance), "Yes" if x.flagged else "",
                reason, (x.explanation_source or "Computed by code") if x.flagged else ""]
        for col, v in zip("ABCDEFG", vals):
            _x(ws, f"{col}{r}", v, wrap=col in "FG", right=col in "BCD")
        ws.row_dimensions[r].height = 15 * max(1, -(-len(str(reason)) // 90))
        r += 1
    r += 1
    _x(ws, f"A{r}", "Analytical observations", True)
    r += 1
    for col, h in zip("ABCDEFG", ["Observation", "Severity", "Figures verified", "", "", "Why it matters and the procedure", "Facts relied on"]):
        if h:
            _x(ws, f"{col}{r}", h, True, fill="D9E2F3", wrap=True)
    r += 1
    obs = list(rv.ai.observations) if ran else []
    if not obs:
        _x(ws, f"A{r}", "The AI raised no observations." if ran else "Not run.", italic=True)
        r += 1
    for o in obs:
        facts = "; ".join(f"{rv.facts.get(i).label}: {rv.facts.get(i).text}" for i in o.fact_ids if rv.facts.get(i))
        body = f"{o.why}\nProcedure: {o.procedure}"
        for col, v in zip("ABCFG", [o.title, o.severity, "Yes" if o.grounded else "No: contains figures not in the books", body, facts]):
            _x(ws, f"{col}{r}", v, wrap=True)
        ws.row_dimensions[r].height = 15 * max(2, -(-len(body) // 80), -(-len(facts) // 30))
        r += 1
    for e in getattr(rv.ai, "errors", []):
        _x(ws, f"A{r}", f"Note: {e}", italic=True)
        r += 1
    ws.freeze_panes = "A4"
    return ws


def _xl_statement(wb, title, m, rows, headers, prev_col, pos, book, formula_for=None, note_col=True):
    """One statement sheet. A figure with a note reads the note's total; a total row uses formula_for(...)."""
    ws = wb.create_sheet(title)
    _sheet_setup(ws, [62, 7 if note_col else 2, 18, 18])
    _x(ws, "A1", m.company, True, size=14)
    _x(ws, "A2", headers[0], True, size=12)
    _x(ws, "A3", _unit_line(), italic=True)
    for col, h in zip("ABCD", ["Particulars", "Note" if note_col else "", headers[1], headers[2]]):
        _x(ws, f"{col}5", h, True, fill="D9E2F3", right=col != "A")
    r, rowpos, section_start, face = 6, {}, 6, {}
    for row in rows:
        bold = row.kind in ("head", "sub", "total")
        indent = {"item": 1, "subitem": 2}.get(row.kind, 0)
        _x(ws, f"A{r}", row.label + _marker(row.flags), bold, indent=indent, top=row.kind == "total",
           fill="F2F2F2" if row.kind == "head" else None)
        rowpos[row.label] = r
        if row.kind == "head":
            section_start = r + 1
        if row.note and row.note in pos:
            _link(ws, f"B{r}", row.note, "Notes", f"A{pos[row.note]['title']}", right=True)
            face[row.note] = (title, r)
        if row.kind in ("head", "sub") or (row.cur is None and row.prev is None):
            r += 1
            continue
        for col, val, note_col_letter in (("C", row.cur, "B"), ("D", row.prev, "C")):
            if col == "D" and not prev_col:
                _x(ws, f"D{r}", "-", right=True)
                continue
            if row.kind == "total" and formula_for and (f := formula_for(row, r, col, rowpos, section_start)):
                book.fx(ws, f"{col}{r}", f, val, bold=True, num=True, top=True)
            elif row.note and row.note in pos and (col == "C" or prev_col):
                book.fx(ws, f"{col}{r}", f"=Notes!{note_col_letter}{pos[row.note]['total']}", val, bold=bold, num=True,
                        top=row.kind == "total")
            else:
                _x(ws, f"{col}{r}", val, bold, num=True, top=row.kind == "total")
        r += 1
    ws.freeze_panes = "A6"
    return ws, r, rowpos, face


def _bs_totals(row, r, col, rowpos, section_start):
    return f"=SUM({col}{section_start}:{col}{r - 1})"


def _pl_totals(row, r, col, rowpos, section_start):
    L = row.label
    if col != "C":
        return None
    if L.startswith("III. Total income"):
        return f"=C{rowpos['I. Revenue from operations']}+C{rowpos['II. Other income']}"
    if L == "Total expenses":
        return f"=SUM(C{rowpos['IV. Expenses:'] + 1}:C{r - 1})"
    if L.startswith("V. Profit"):
        return f"=C{rowpos['III. Total income (I + II)']}-C{rowpos['Total expenses']}"
    if L.startswith("VII. Profit"):
        return f"=C{rowpos['V. Profit / (loss) before tax (III - IV)']}-C{rowpos['(1) Current tax']}-C{rowpos['(2) Deferred tax']}"
    return None


def _cf_totals(pl_rows):
    def f(row, r, col, rowpos, section_start):
        L = row.label
        if col != "C":
            return None
        if L.startswith("Operating profit before"):
            return f"=SUM(C{rowpos['Net profit / (loss) before tax']}:C{r - 1})"
        if L.startswith("Cash generated"):
            return f"=C{rowpos['Operating profit before working capital changes']}+SUM(C{rowpos['Operating profit before working capital changes'] + 1}:C{r - 1})"
        if L.startswith("Net cash from / (used in) operating"):
            return f"=C{rowpos['Cash generated from operations']}+C{rowpos['Direct taxes paid (net of refunds)']}"
        if "investing activities (B)" in L:
            return f"=SUM(C{rowpos['B. CASH FLOW FROM INVESTING ACTIVITIES'] + 1}:C{r - 1})"
        if "financing activities (C)" in L:
            return f"=SUM(C{rowpos['C. CASH FLOW FROM FINANCING ACTIVITIES'] + 1}:C{r - 1})"
        if L.startswith("D. NET"):
            a = rowpos["Net cash from / (used in) operating activities (A)"]
            b = rowpos["Net cash from / (used in) investing activities (B)"]
            c = rowpos["Net cash from / (used in) financing activities (C)"]
            return f"=C{a}+C{b}+C{c}"
        if L.startswith("Cash and cash equivalents at the end"):
            return f"=C{rowpos['Cash and cash equivalents at the beginning of the year']}+C{rowpos[[k for k in rowpos if k.startswith('D. NET')][0]]}"
        return None
    return f


def _inject_cached_values(path, sheet_names, cache):
    """openpyxl writes formulas without their results. Insert the results so previews that do not calculate still
    show the numbers (Excel recalculates on open anyway)."""
    import xml.etree.ElementTree as ET
    import zipfile
    ET.register_namespace("", MAIN_NS)
    ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")
    with zipfile.ZipFile(path) as z:
        files = {n: z.read(n) for n in z.namelist()}
    for i, name in enumerate(sheet_names, start=1):
        values = cache.get(name)
        part = f"xl/worksheets/sheet{i}.xml"
        if not values or part not in files:
            continue
        root = ET.fromstring(files[part])
        for c in root.iter(f"{{{MAIN_NS}}}c"):
            ref = c.get("r")
            if ref in values and c.find(f"{{{MAIN_NS}}}f") is not None:
                v = c.find(f"{{{MAIN_NS}}}v")
                if v is None:
                    v = ET.SubElement(c, f"{{{MAIN_NS}}}v")
                v.text = repr(float(values[ref])) if not float(values[ref]).is_integer() else str(int(values[ref]))
                c.attrib.pop("t", None)
        files[part] = ET.tostring(root, xml_declaration=True, encoding="UTF-8")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in files.items():
            z.writestr(n, data)


def _build_xlsx(m: Model, path: Path) -> Path:
    wb = Workbook()
    wb.remove(wb.active)
    book = Book()
    cur, prv = f"As at {dmy(m.as_at)}", f"As at {dmy(m.prev_as_at)}"

    notes_ws, pos = _xl_notes(wb, m, book)     # first, so the statements can link to it

    ws, r, bs_rows, bs_face = _xl_statement(wb, "Balance Sheet", m, m.bs, [f"Balance Sheet as at {dmy(m.as_at)}", cur, prv],
                                            True, pos, book, _bs_totals)
    ta, tel = bs_rows["TOTAL ASSETS"], bs_rows["TOTAL EQUITY AND LIABILITIES"]
    tot = {row.label: row for row in m.bs if row.kind == "total"}
    _x(ws, f"A{r + 1}", "Check: total assets less total equity and liabilities", italic=True)
    book.fx(ws, f"C{r + 1}", f"=C{ta}-C{tel}", tot["TOTAL ASSETS"].cur - tot["TOTAL EQUITY AND LIABILITIES"].cur, num=True)
    book.fx(ws, f"D{r + 1}", f"=D{ta}-D{tel}", tot["TOTAL ASSETS"].prev - tot["TOTAL EQUITY AND LIABILITIES"].prev, num=True)
    _x(ws, f"A{r + 3}", DRAFT, italic=True)
    _xl_signatures(ws, m, r + 5)

    ws, r, pl_rows, pl_face = _xl_statement(
        wb, "P&L", m, m.pl, [f"Statement of Profit and Loss for the year ended {dmy(m.as_at)}", f"Year ended {dmy(m.as_at)}",
                             f"Year ended {dmy(m.prev_as_at)}"], False, pos, book, _pl_totals)
    _x(ws, f"A{r + 1}", "Previous-year figures were not loaded; see open item O1.", italic=True)
    _xl_signatures(ws, m, r + 3)

    ws, r, cf_rows, _ = _xl_statement(
        wb, "Cash Flow", m, m.cashflow, [f"Cash Flow Statement for the year ended {dmy(m.as_at)}", f"Year ended {dmy(m.as_at)}",
                                         f"Year ended {dmy(m.prev_as_at)}"], False, pos, book, _cf_totals(pl_rows), note_col=False)
    # profit before tax is the P&L figure, not a retyped number
    pbt_row = cf_rows["Net profit / (loss) before tax"]
    pbt_val = next(x.cur for x in m.cashflow if x.label == "Net profit / (loss) before tax")
    book.fx(ws, f"C{pbt_row}", f"='P&L'!C{pl_rows['V. Profit / (loss) before tax (III - IV)']}", pbt_val, num=True)
    r += 1
    for col, h in zip("ACD", ["Cash and cash equivalents comprise:", cur, prv]):
        _x(ws, f"{col}{r}", h, True, fill="D9E2F3", right=col != "A")
    r += 1
    first = r
    for label, c, p in m.cce:
        _x(ws, f"A{r}", label, indent=1)
        _x(ws, f"C{r}", c, num=True)
        _x(ws, f"D{r}", p, num=True)
        r += 1
    _x(ws, f"A{r}", "Total", True, top=True)
    book.fx(ws, f"C{r}", f"=SUM(C{first}:C{r - 1})", sum(x[1] for x in m.cce), bold=True, num=True, top=True)
    book.fx(ws, f"D{r}", f"=SUM(D{first}:D{r - 1})", sum(x[2] for x in m.cce), bold=True, num=True, top=True)
    cce_total = r
    # opening cash is last year's cash; the check proves closing cash agrees to the components above
    begin, end = cf_rows["Cash and cash equivalents at the beginning of the year"], cf_rows["Cash and cash equivalents at the end of the year"]
    book.fx(ws, f"C{begin}", f"=D{cce_total}", sum(x[2] for x in m.cce), num=True)
    r += 1
    _x(ws, f"A{r}", "Check: closing cash less cash and cash equivalents above", italic=True)
    end_val = next(x.cur for x in m.cashflow if x.label.startswith("Cash and cash equivalents at the end"))
    book.fx(ws, f"C{r}", f"=C{end}-C{cce_total}", end_val - sum(x[1] for x in m.cce), num=True)
    r += 2
    _x(ws, f"A{r}", "Basis of the cash flow statement", True)
    for text in m.cf_notes:
        r += 1
        _x(ws, f"A{r}", f"• {text}", wrap=True)
        ws.row_dimensions[r].height = 28
    _xl_signatures(ws, m, r + 3)

    # back-links from each note to the line that uses it
    for no, (sheet, row) in {**bs_face, **pl_face}.items():
        _link(notes_ws, f"F{pos[no]['title']}", f"↩ {sheet}", sheet, f"A{row}")

    if m.disclosures:
        ws = wb.create_sheet("Disclosures")
        _sheet_setup(ws, [46, 34, 34, 28, 16, 16, 16, 16])
        _x(ws, "A1", "Additional regulatory information and other statutory disclosures", True, size=12)
        _x(ws, "A2", "Facts the books show are stated with their source; where only management can answer the cell says so. "
                     "A blank or bracketed cell is not a statement that the item is nil.", italic=True)
        r = 4
        for d in m.disclosures:
            _x(ws, f"A{r}", f"{d.no}. {d.title}", True)
            _x(ws, f"B{r}", d.ref, italic=True, wrap=True)
            r += 1
            for col, h in zip("ABCDEFGH", d.header):
                _x(ws, f"{col}{r}", h, True, fill="D9E2F3", wrap=True)
            r += 1
            for row in d.rows:
                for col, v in zip("ABCDEFGH", row):
                    _x(ws, f"{col}{r}", v, wrap=True)
                ws.row_dimensions[r].height = 15 * max(1, max(-(-len(str(v)) // 40) for v in row))
                r += 1
            if d.comment:
                _x(ws, f"A{r}", d.comment, italic=True, wrap=True)
                ws.merge_cells(f"A{r}:D{r}")
                ws.row_dimensions[r].height = 15 * max(1, -(-len(d.comment) // 120))
                r += 1
            r += 1
        _xl_signatures(ws, m, r + 1, "B")

    if m.review is not None:
        _xl_ai(wb, m)

    ws = wb.create_sheet("Open items")
    _sheet_setup(ws, [7, 16, 22, 26, 14, 80, 28])
    _x(ws, "A1", "Open items for the reviewer", True, size=12)
    for col, h in zip("ABCDEFG", ["Ref", "Type", "Area", "Ledger", "Amount", "Matter", "Reviewer response"]):
        _x(ws, f"{col}3", h, True, fill="D9E2F3", right=col == "E")
    r = 4
    for f in m.flags:
        for col, v in zip("ABCDEF", [f.ref, f.kind, f.area, f.ledger, f.amount, f.text]):
            _x(ws, f"{col}{r}", v if v is not None or col != "E" else "-", num=col == "E" and v is not None,
               wrap=col == "F", right=col == "E")
        r += 1
    r += 1
    _x(ws, f"A{r}", "Information required for the notes (not available in Tally)", True)
    r += 1
    for n in m.notes:
        for g in n.gaps:
            _x(ws, f"A{r}", f"Note {n.no}", right=False)
            _x(ws, f"C{r}", n.title)
            _x(ws, f"F{r}", g, wrap=True)
            r += 1
    for g in m.general_gaps:
        _x(ws, f"A{r}", "General")
        _x(ws, f"F{r}", g, wrap=True)
        r += 1
    ws.freeze_panes = "A4"

    ws = wb.create_sheet("Mapping")
    mapping_token = _UNIT.set(UNITS["rupees"])      # raw ledger balances stay in exact rupees
    _sheet_setup(ws, [36, 22, 40, 44, 16, 16, 10, 12, 70])
    _x(ws, "A1", "Ledger to Schedule III mapping (balances shown Dr / (Cr), as in Tally)", True, size=12)
    heads = ["Ledger", "Tally group", "Schedule III line", "Sub-head", "Opening", "Closing", "Source", "Rule", "Review note"]
    for col, h in zip("ABCDEFGHI", heads):
        _x(ws, f"{col}3", h, True, fill="D9E2F3", right=col in "EF")
    r = 4
    for row in m.mapping.itertuples(index=False):
        vals = [row.ledger, row.group, row.line_label, row.sub, round(row.opening), round(row.closing), row.source,
                row.rule_id, row.review]
        for col, v in zip("ABCDEFGHI", vals):
            _x(ws, f"{col}{r}", v, num=col in "EF", wrap=col == "I")
        r += 1
    ws.freeze_panes = "A4"
    ws.auto_filter.ref = f"A3:I{r - 1}"
    _UNIT.reset(mapping_token)

    wb._sheets.sort(key=lambda s: SHEET_ORDER.index(s.title))
    wb.calculation.fullCalcOnLoad = True
    wb.save(path)
    _inject_cached_values(path, wb.sheetnames, book.cache)
    return path


def build_docx(m: Model, path: Path) -> Path:
    token = _UNIT.set(m.unit)
    try:
        return _build_docx(m, path)
    finally:
        _UNIT.reset(token)


def build_xlsx(m: Model, path: Path) -> Path:
    token = _UNIT.set(m.unit)
    try:
        return _build_xlsx(m, path)
    finally:
        _UNIT.reset(token)


def write_all(m: Model, out_dir) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"{safe_name(m.company)}_FS_{m.as_at:%Y%m%d}"
    return build_docx(m, out / f"{stem}.docx"), build_xlsx(m, out / f"{stem}.xlsx")
