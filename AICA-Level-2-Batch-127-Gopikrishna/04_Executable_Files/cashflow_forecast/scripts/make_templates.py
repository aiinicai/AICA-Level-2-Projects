"""Generate the blank input templates in input_templates/ from app/importers/specs.py.

    python scripts/make_templates.py

Each template has three sheets:
  Data          - header row only; this is the sheet the app reads
  Example       - a few synthetic rows showing the format (never imported)
  Instructions  - what each column means, accepted ERP header spellings, upload rules
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import xlsxwriter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.importers.specs import BD_TYPES, SPECS, SourceSpec  # noqa: E402

OUT = ROOT / "input_templates"

EXAMPLES: dict[str, list[list]] = {
    "collections": [
        ["INV-26-0001", "Customer A (synthetic)", "PRJ-10", date(2026, 12, 5), 12500.250, "", "N", "N"],
        ["INV-26-0002", "Customer B (synthetic)", "PRJ-11", date(2026, 12, 18), 8400.000, "", "Y", "N"],
        ["INV-26-0003", "Customer C (synthetic)", "PRJ-12", date(2027, 1, 9), 22000.000, "", "N", "Y"],
    ],
    "additional": [
        ["ADD-001", "PRJ-12", "Customer C (synthetic)", date(2026, 12, 10), 15000.000, "Advance on variation", ""],
        ["ADD-002", "PRJ-14", "", date(2027, 1, 15), 7250.500, "Retention release", ""],
    ],
    "vendor_pdc": [
        ["PV-26-1001", "Vendor 01 (synthetic)", "000101", date(2026, 12, 3), 4350.000, "Bank A", ""],
        ["PV-26-1001", "Vendor 01 (synthetic)", "000102", date(2027, 1, 3), 4350.000, "Bank A", ""],
        ["PV-26-1002", "Vendor 02 (synthetic)", "000215", date(2026, 12, 12), 9120.750, "Bank B", ""],
    ],
    "allocation": [
        ["Vendor 31 (synthetic)", "PINV-5501", date(2026, 12, 4), 27800.000, ""],
        ["Vendor 32 (synthetic)", "PINV-5502", date(2026, 12, 18), 35250.000, ""],
    ],
    "bill_discount": [
        ["DISC-7781", "Bank A", "Discount proceeds", date(2026, 11, 26), 45000.000, "INV-26-0003", ""],
        ["DISC-0912", "Bank A", "Discount maturity", date(2026, 12, 8), 52000.000, "", ""],
        ["LC-4471", "Bank B", "LC maturity", date(2026, 11, 29), 38400.000, "", ""],
    ],
    "other": [
        ["PAY-DEC", "Payroll", "Staff salaries December", date(2026, 12, 28), 78500.000, "Outflow"],
        ["RENT-JAN", "Rent & utilities", "Office rent January", date(2027, 1, 1), 12400.000, "Outflow"],
        ["CLM-04", "Other inflows", "Insurance claim", date(2026, 12, 14), 6250.000, "Inflow"],
    ],
    "category_list": [
        ["Customer collections", "Inflow", "Collections", 10, "Fixed", "collections", "Receivables; AR"],
        ["Vendor PDCs", "Outflow", "Suppliers", 110, "Deferrable", "vendor_pdc", "PDC; Cheques"],
        ["Payroll", "Outflow", "Staff costs", 140, "Fixed", "", "Salaries; WPS"],
    ],
    "payment_history": [
        ["INV-25-0901", "Customer A (synthetic)", "PRJ-10", date(2025, 9, 1), date(2025, 10, 1), date(2025, 10, 20), 9800.000],
        ["INV-25-0902", "Customer B (synthetic)", "PRJ-11", date(2025, 9, 5), date(2025, 10, 5), date(2025, 11, 30), 15200.000],
    ],
    "bank_balances": [
        ["Bank A", "Current 0101", "OMR", date(2026, 11, 24), 182450.250, 1],
        ["Bank D", "USD 0404", "USD", date(2026, 11, 24), 40000.000, 0.3845],
    ],
    "bank_facility": [
        ["Bank A", "Overdraft", date(2026, 11, 24), 150000.000, 100000.000, 50000.000],
    ],
}
WIDE_OTHER = (["Date", "Description", "Payroll", "Rent & utilities", "VAT & taxes"],
              [[date(2026, 12, 28), "Month-end payments", 78500.000, "", ""],
               [date(2027, 1, 1), "Rent", "", 12400.000, ""],
               [date(2027, 1, 31), "VAT return Q4", "", "", 39800.000]])

TYPE_TEXT = {"str": "Text", "date": "Date", "amount": "Amount (OMR, 3 dp)", "rate": "Rate (up to 6 dp)",
             "int": "Whole number", "bool": "Y or N", "direction": "Inflow or Outflow",
             "treatment": "Fixed or Deferrable", "bd_type": "Discount proceeds / Discount maturity / LC maturity"}


def build(spec: SourceSpec, out: Path = OUT) -> Path:
    path = out / spec.template_file
    wb = xlsxwriter.Workbook(path)
    wb.set_properties({"title": spec.title, "comments": "Cash Flow Forecast input template"})
    navy = "#1F3864"
    f_req = wb.add_format({"bold": True, "bg_color": navy, "font_color": "white", "border": 1})
    f_opt = wb.add_format({"bold": True, "bg_color": "#8497B0", "font_color": "white", "border": 1})
    f_date = wb.add_format({"num_format": "dd-mmm-yyyy"})
    f_amt = wb.add_format({"num_format": "#,##0.000"})
    f_rate = wb.add_format({"num_format": "0.000000"})
    f_title = wb.add_format({"bold": True, "font_size": 14, "font_color": navy})
    f_bold = wb.add_format({"bold": True})
    f_wrap = wb.add_format({"text_wrap": True, "valign": "top"})
    f_hdr = wb.add_format({"bold": True, "bg_color": "#D9E1F2", "border": 1, "text_wrap": True, "valign": "top"})
    col_fmt = {"date": f_date, "amount": f_amt, "rate": f_rate}

    def header(ws, with_validation: bool, rows: int = 5000):
        for i, c in enumerate(spec.columns):
            ws.write(0, i, c.label, f_req if c.required else f_opt)
            ws.set_column(i, i, max(14, len(c.label) + 4), col_fmt.get(c.type))
            tip = f"{'Required' if c.required else 'Optional'} - {TYPE_TEXT[c.type]}." + (f" {c.help}" if c.help else "")
            ws.write_comment(0, i, tip, {"x_scale": 2, "y_scale": 1.2})
            if not with_validation:
                continue
            v = None
            if c.type == "date":
                v = {"validate": "date", "criteria": ">=", "value": date(2000, 1, 1),
                     "error_message": "Enter a date (dd-mmm-yyyy)."}
            elif c.type == "amount":
                v = {"validate": "decimal", "criteria": ">=", "value": 0,
                     "error_message": "Enter a positive amount (3 decimals)."}
            elif c.type == "rate":
                v = {"validate": "decimal", "criteria": ">", "value": 0, "error_message": "Rate must be > 0."}
            elif c.type == "int":
                v = {"validate": "integer", "criteria": ">=", "value": 0}
            elif c.type == "bool":
                v = {"validate": "list", "source": ["Y", "N"]}
            elif c.type == "direction":
                v = {"validate": "list", "source": ["Inflow", "Outflow"]}
            elif c.type == "treatment":
                v = {"validate": "list", "source": ["Fixed", "Deferrable"]}
            elif c.type == "bd_type":
                v = {"validate": "list", "source": [t.capitalize() if t != "lc maturity" else "LC maturity"
                                                    for t in BD_TYPES]}
            if v:
                ws.data_validation(1, i, rows, i, v)
        ws.freeze_panes(1, 0)

    ds = wb.add_worksheet("Data")
    header(ds, True)
    ex = wb.add_worksheet("Example")
    header(ex, False)
    for r, row in enumerate(EXAMPLES.get(spec.source_type, []), 1):
        for c, val in enumerate(row):
            if isinstance(val, date):
                ex.write_datetime(r, c, val, f_date)
            elif val != "":
                ex.write(r, c, val)
    ex.write(len(EXAMPLES.get(spec.source_type, [])) + 2, 0,
             "Synthetic example only - this sheet is never imported.", wb.add_format({"italic": True}))
    if spec.source_type == "other":
        wx = wb.add_worksheet("Example (wide)")
        for c, h in enumerate(WIDE_OTHER[0]):
            wx.write(0, c, h, f_req if c < 2 else f_opt); wx.set_column(c, c, 18)
        for r, row in enumerate(WIDE_OTHER[1], 1):
            wx.write_datetime(r, 0, row[0], f_date); wx.write(r, 1, row[1])
            for c, val in enumerate(row[2:], 2):
                if val != "":
                    wx.write_number(r, c, val, f_amt)
        wx.write(5, 0, "WIDE layout: each column after Description is a category (the header IS the category).",
                 wb.add_format({"italic": True}))

    ins = wb.add_worksheet("Instructions")
    ins.set_column(0, 0, 22); ins.set_column(1, 1, 10); ins.set_column(2, 2, 22); ins.set_column(3, 4, 48)
    ins.write(0, 0, spec.title, f_title)
    r = 2
    for line in spec.notes:
        ins.write(r, 0, line); r += 1
    key = " + ".join(spec.column(k).label for k in spec.key_columns) if spec.key_columns else "row content"
    rules = [
        f"Fill the 'Data' sheet (row 1 = headers). Unique key: {key}.",
        "Dark headers are required, light headers optional. Column order does not matter.",
        "ERP exports can be uploaded as they are: the headers listed below are recognised; others go to Exceptions.",
        "Amounts in OMR with up to 3 decimals, positive figures. Dates as Excel dates or dd-mm-yyyy.",
        "Upload as .xlsx or .csv only (no macros, size limit applies). Synthetic or real data stays on your PC.",
    ]
    for line in rules:
        ins.write(r, 0, line); r += 1
    r += 1
    ins.write_row(r, 0, ["Column", "Required", "Type", "Also accepted as header", "Notes"], f_hdr)
    for c in spec.columns:
        r += 1
        ins.write_row(r, 0, [c.label, "Yes" if c.required else "No", TYPE_TEXT[c.type],
                             ", ".join(c.aliases), c.help], f_wrap)
    ds.activate()
    wb.close()
    return path


def write_doc() -> Path:
    """docs/input_formats.md, generated from the same specs so it can never drift."""
    lines = ["# Input file formats", "",
             "_Generated by `python scripts/make_templates.py` from `app/importers/specs.py`. Do not edit by hand._",
             "", "General rules:",
             "- Upload `.xlsx` or `.csv` only. Macro-enabled files are refused. There is a size limit (`CFF_UPLOAD_MAX_MB`).",
             "- ERP exports can be uploaded as they are. The app finds the header row, even below report title rows, and skips "
             "`Total` rows. It recognises the header spellings listed below; any other header goes to the Exceptions screen "
             "with a suggested match.",
             "- Amounts are in OMR with up to 3 decimals and entered as positive figures. Direction comes from the source type, "
             "or from the Type or Inflow/Outflow column.",
             "- The **key** identifies a row across daily uploads, so your holds, defers and other changes survive a re-upload.",
             ""]
    for s in SPECS.values():
        key = " + ".join(s.column(k).label for k in s.key_columns) or "row content"
        lines += [f"## {s.title}", "", f"Template: `input_templates/{s.template_file}` | Key: **{key}**", ""]
        lines += [f"- {n}" for n in s.notes] + ([""] if s.notes else [])
        lines += ["| Column | Required | Type | Also accepted as header | Notes |", "|---|---|---|---|---|"]
        for c in s.columns:
            lines.append(f"| {c.label} | {'Yes' if c.required else 'No'} | {TYPE_TEXT[c.type]} | "
                         f"{', '.join(c.aliases)} | {c.help} |")
        lines.append("")
    path = ROOT / "docs" / "input_formats.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for spec in SPECS.values():
        print("wrote", build(spec).relative_to(ROOT))
    print("wrote", write_doc().relative_to(ROOT))


if __name__ == "__main__":
    main()
