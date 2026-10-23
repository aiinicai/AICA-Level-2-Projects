"""Generate draft financial statements (Word) for the SAME fictional entity as sample_daybook.xml.

Figures are computed from the Day Book vouchers, so the two documents reconcile. Two files:
  sample_fs_clean.docx   - consistent fonts, dd/mm/yyyy dates, negatives in brackets
  sample_fs_errors.docx  - the same statements with seeded formatting defects

Usage: python samples/make_sample_fs.py
"""
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

import make_sample as ms

ENTITY = "Meridian Components Private Limited"
FY_END = date(2026, 3, 31)
FONT = "Times New Roman"
OPENING_CAPITAL = 1_000_000  # introduced in cash at the start; held at HDFC Bank on 01/04/2025


def indian(n: float, brackets: bool = True) -> str:
    """12,34,567 style grouping; negatives in brackets (or with a minus when brackets=False)."""
    n = round(n)
    s = str(abs(n))
    head, tail = s[:-3], s[-3:]
    if head:
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    if n < 0:
        return f"({s})" if brackets else f"-{s}"
    return s


def balances() -> dict:
    nets: dict[str, float] = {"HDFC Bank": OPENING_CAPITAL}  # Dr positive
    for d, _t, _n, lines in ms.V:
        if d > FY_END:
            continue
        for ledger, amt, side in lines:
            nets[ledger] = nets.get(ledger, 0.0) + (amt if side == "Dr" else -amt)
    return nets


def statements() -> dict:
    b = balances()
    g = lambda *names: sum(b.get(n, 0.0) for n in names)  # noqa: E731
    revenue = -g("Sales")
    employee = g("Salaries")
    other_exp = g("Office Rent", "Staff Welfare", "Miscellaneous Expenses", "Repairs & Maintenance",
                  "Professional Fees", "Insurance", "Electricity")
    loss = revenue - employee - other_exp
    other_cl = -g("Salary Payable", "TDS Payable", "CGST", "SGST", "IGST", "Suspense A/c", "Gupta Enterprises")
    assets = {
        "Trade receivables": g("Alpha Industries"),
        "Cash and cash equivalents": g("Cash", "HDFC Bank"),
        "Short-term loans and advances": g("Sharma Traders", "Verma Transport", "Kumar Loaders"),
    }
    total_assets = sum(assets.values())
    diff = total_assets - (OPENING_CAPITAL + loss + other_cl)  # unreconciled voucher (Dr != Cr)
    return dict(revenue=revenue, employee=employee, other_exp=other_exp, loss=loss, other_cl=other_cl + diff,
                diff=diff, assets=assets, total_assets=total_assets, nets=b)


def _cell(cell, text, size=10, bold=False, right=False, font=FONT):
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if right else WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(text)
    r.font.name, r.font.size, r.font.bold = font, Pt(size), bold


def _para(doc, text, size=11, bold=False, font=FONT, align=None):
    p = doc.add_paragraph()
    if align:
        p.alignment = align
    r = p.add_run(text)
    r.font.name, r.font.size, r.font.bold = font, Pt(size), bold
    return p


def _table(doc, rows, header, defects, tag):
    t = doc.add_table(rows=0, cols=4)
    t.style = "Table Grid"
    for i, row in enumerate([header] + rows):
        cells = t.add_row().cells
        bold = i == 0 or row[0].isupper() or row[0].startswith("Total")
        for j, text in enumerate(row):
            font, size = FONT, 10
            if defects and (tag, i, j) in defects.get("font", {}):
                font, size = defects["font"][(tag, i, j)]
            _cell(cells[j], text, size=size, bold=bold, right=j >= 2, font=font)
    return t


def build(errors: bool) -> Document:
    s = statements()
    neg = (lambda n: indian(n, brackets=True))
    bad = {"font": {}, "minus": set()}
    if errors:
        bad["font"] = {("BS", 6, 2): ("Calibri", 10), ("BS", 9, 2): (FONT, 12), ("PL", 4, 2): ("Arial", 10)}
        bad["minus"] = {("BS", 4), ("PL", 8)}

    def money(tag, i, n):
        return indian(n, brackets=False) if (tag, i) in bad["minus"] else neg(n)

    d_end = "31/03/2026"
    d_a, d_b, d_c = ("31-Mar-2026", "March 31, 2026", "2026-03-31") if errors else ("31/03/2026",) * 3
    doc = Document()
    doc.styles["Normal"].font.name, doc.styles["Normal"].font.size = FONT, Pt(11)

    _para(doc, ENTITY, 14, True, align=WD_ALIGN_PARAGRAPH.CENTER)
    _para(doc, f"CIN: U29100MH2019PTC123456 | Balance Sheet as at {d_end}", 12, True, align=WD_ALIGN_PARAGRAPH.CENTER)

    reserves = s["loss"]
    bs = [
        ["EQUITY AND LIABILITIES", "", "", ""],
        ["Shareholders' funds", "", "", ""],
        ["(a) Share capital", "1", indian(OPENING_CAPITAL), indian(OPENING_CAPITAL)],
        ["(b) Reserves and surplus", "2", money("BS", 4, reserves), "-"],
        ["Current liabilities", "", "", ""],
        ["(a) Other current liabilities", "3", money("BS", 6, s["other_cl"]), "-"],
        ["Total", "", money("BS", 7, OPENING_CAPITAL + reserves + s["other_cl"]), indian(OPENING_CAPITAL)],
        ["ASSETS", "", "", ""],
    ]
    for k, (name, val) in enumerate(s["assets"].items()):
        bs.append([f"({'abc'[k]}) {name}", str(4 + k), money("BS", 9 + k, val), "-"])
    bs.append(["Total", "", money("BS", 12, s["total_assets"]), indian(OPENING_CAPITAL)])
    _table(doc, bs, ["Particulars", "Note", f"As at {d_end}", "As at 31/03/2025"], bad, "BS")

    doc.add_paragraph()
    _para(doc, f"Statement of Profit and Loss for the year ended {d_a}", 12, True, align=WD_ALIGN_PARAGRAPH.CENTER)
    total_exp = s["employee"] + s["other_exp"]
    pl = [
        ["INCOME", "", "", ""],
        ["Revenue from operations", "7", money("PL", 2, s["revenue"]), "-"],
        ["EXPENSES", "", "", ""],
        ["Employee benefit expense", "8", money("PL", 4, s["employee"]), "-"],
        ["Other expenses", "9", money("PL", 5, s["other_exp"]), "-"],
        ["Total expenses", "", money("PL", 6, total_exp), "-"],
        ["", "", "", ""],
        ["Profit / (loss) for the year", "", money("PL", 8, s["loss"]), "-"],
    ]
    _table(doc, pl, ["Particulars", "Note", f"Year ended {d_end}", "Year ended 31/03/2025"], bad, "PL")

    doc.add_paragraph()
    _para(doc, "Notes forming part of the financial statements", 12, True)
    _para(doc, f"Note 1: The authorised and paid-up share capital as at {d_end} is Rs {indian(OPENING_CAPITAL)}.")
    _para(doc, f"Note 2: The deficit in the statement of profit and loss for the year ended {d_end} is "
               f"Rs {money('N', 0, abs(reserves) * -1)}.")
    _para(doc, f"Note 3: Other current liabilities include unreconciled difference of Rs {indian(s['diff'])}, "
               f"suspense balances and statutory dues outstanding as at {d_b}.")
    _para(doc, f"The financial statements were approved by the Board of Directors on {'15/05/2026' if not errors else '15.05.26'} "
               f"and signed on {d_c}.")
    if errors:  # a stray paragraph in a different font and size
        _para(doc, "Figures in this statement are in Indian Rupees.", 9, False, font="Verdana")
    return doc


def build_xlsx(errors: bool):
    """Same statements as an Excel workbook. Errors: 3 font, 3 date, 2 negative-number-format defects."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    s = statements()
    bracket_fmt, plain_fmt = "#,##0_);(#,##0)", "#,##0"
    wb = Workbook()
    wb.remove(wb.active)

    def sheet(title, heading, rows, date_cell_fmt, text_date, minus_rows, font_defects):
        ws = wb.create_sheet(title)
        base = lambda **kw: Font(name=kw.pop("name", FONT), size=kw.pop("size", 10), **kw)  # noqa: E731
        ws["A1"], ws["A1"].font = ENTITY, base(size=14, bold=True)
        ws["A2"], ws["A2"].font = heading, base(size=12, bold=True)
        ws["A3"], ws["A3"].font = "As at", base(bold=True)
        ws["C3"] = date(2026, 3, 31)
        ws["C3"].number_format, ws["C3"].font = date_cell_fmt, base(bold=True)
        ws["D3"], ws["D3"].font = text_date, base(bold=True)
        for j, h in enumerate(["Particulars", "Note", "Current year", "Previous year"], start=1):
            ws.cell(5, j, h).font = base(bold=True)
        for i, (label, note, cur, prev) in enumerate(rows, start=6):
            ws.cell(i, 1, label).font = base(bold=not note and cur is None)
            ws.cell(i, 2, note).font = base()
            for col, val in ((3, cur), (4, prev)):
                c = ws.cell(i, col, val)
                c.number_format = plain_fmt if i in minus_rows else bracket_fmt
                c.font = base()
            if (title, i) in font_defects:
                name, size = font_defects[(title, i)]
                ws.cell(i, 3).font = base(name=name, size=size)
        ws.column_dimensions["A"].width = 38
        ws.column_dimensions["C"].width = 16
        ws.column_dimensions["D"].width = 16

    eq = OPENING_CAPITAL
    bs_rows = [("Share capital", 1, eq, eq), ("Reserves and surplus", 2, s["loss"], 0),
               ("Other current liabilities", 3, s["other_cl"], 0),
               ("Total equity and liabilities", None, eq + s["loss"] + s["other_cl"], eq)]
    bs_rows += [(k, 4 + n, v, 0) for n, (k, v) in enumerate(s["assets"].items())]
    bs_rows.append(("Total assets", None, s["total_assets"], eq))
    pl_rows = [("Revenue from operations", 7, s["revenue"], 0), ("Employee benefit expense", 8, s["employee"], 0),
               ("Other expenses", 9, s["other_exp"], 0), ("Profit / (loss) for the year", None, s["loss"], 0)]
    # rows start at 6: BS reserves = row 7, PL loss = row 9
    bad = errors
    sheet("Balance Sheet", "Balance Sheet", bs_rows, "mm/dd/yyyy" if bad else "dd/mm/yyyy",
          "March 31, 2026" if bad else "31/03/2026", {7} if bad else set(),
          {("Balance Sheet", 8): ("Calibri", 10), ("Balance Sheet", 11): (FONT, 12)} if bad else {})
    sheet("P&L", "Statement of Profit and Loss", pl_rows, "dd/mm/yyyy",
          "31-Mar-2026" if bad else "31/03/2026", {9} if bad else set(),
          {("P&L", 7): ("Arial", 10)} if bad else {})
    return wb


if __name__ == "__main__":
    out = Path(__file__).parent
    build(False).save(out / "sample_fs_clean.docx")
    build(True).save(out / "sample_fs_errors.docx")
    build_xlsx(False).save(out / "sample_fs_clean.xlsx")
    build_xlsx(True).save(out / "sample_fs_errors.xlsx")
    s = statements()
    print(f"Revenue {s['revenue']:,.0f} | Loss {s['loss']:,.0f} | Total assets {s['total_assets']:,.0f} | diff {s['diff']:,.0f}")
    print("Wrote sample_fs_clean.docx and sample_fs_errors.docx")
