import io
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import importer as I  # noqa: E402

MASTER = ["Sri Lakshmi Plastics", "Kaveri Packaging", "Anand Die Casting"]


def xlsx(rows, sheet="Sheet1"):
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False, header=False, sheet_name=sheet)
    return buf.getvalue()


def run(data, name, perspective="vendor", default_kind=None, default_vendor=None):
    sh, det = I.best_sheet(I.read_raw(data, name))
    assert det.header_idx is not None, "header not detected"
    rows = I.build_rows(sh.df, det.header_idx, det.mapping)
    cl = I.classify(rows, perspective, default_kind)
    dv = default_vendor or I.guess_vendor(det.preamble, MASTER)
    bills, pays, notes = I.to_inputs(cl, dv, MASTER)
    return cl, bills, pays, notes, det


STATEMENT = [
    ["Sri Lakshmi Plastics"], ["Statement of Account for Led Lum Lighting Solutions LLP"], ["Period 01-04-2026 to 30-09-2026"], [],
    ["Date", "Particulars", "Vch No", "Debit", "Credit", "Balance"],
    ["01-04-2026", "Opening Balance", None, 10000, None, 10000],
    ["05-04-2026", "Sales Invoice", "SL/001", 50000, None, 60000],
    ["20-04-2026", "Receipt NEFT against SL/001", "UTR998", None, 50000, 10000],
    ["10-05-2026", "Tax Invoice", "SL/002", "1,18,000.00", None, 128000],
    ["15-06-2026", "Credit Note", "CN/01", None, 8000, 120000],
    ["30-09-2026", "Total", None, 168000, 58000, None],
]


def test_vendor_statement_debit_credit():
    cl, bills, pays, notes, det = run(xlsx(STATEMENT), "stmt.xlsx")
    assert det.layout.startswith("Ledger")
    assert list(bills["Bill No"]) == ["SL/001", "SL/002"] and list(bills["Bill Amount"]) == [50000, 118000]
    assert set(bills["Vendor Name"]) == {"Sri Lakshmi Plastics"}          # vendor guessed from preamble
    assert list(pays["Amount Paid"]) == [50000, 8000]
    assert pays.iloc[0]["Bill No"] == "SL/001"                            # linked from narration
    assert pd.isna(pays.iloc[1]["Bill No"])
    assert set(cl.loc[cl["Kind"] == "Skip", "Basis"]) == {"Opening/closing/total row"}


def test_perspective_inference_and_our_ledger():
    # our own ledger of the vendor: invoices in Credit, payments in Debit
    ours = [["Date", "Narration", "Voucher No", "Debit", "Credit"],
            ["05-04-2026", "Purchase Invoice", "SL/001", None, 50000],
            ["20-04-2026", "Payment by NEFT", "PV1", 50000, None],
            ["10-05-2026", "Purchase Invoice", "SL/002", None, 118000],
            ["12-05-2026", "Payment by cheque", "PV2", 118000, None]]
    sh, det = I.best_sheet(I.read_raw(xlsx(ours), "o.xlsx"))
    rows = I.build_rows(sh.df, det.header_idx, det.mapping)
    assert I.infer_perspective(rows) == "ours"
    cl = I.classify(rows, "ours")
    assert list(cl["Kind"]) == ["Bill", "Payment", "Bill", "Payment"]
    cl_wrong = I.classify(rows, "vendor")
    assert cl_wrong["Check"].str.len().gt(0).all()        # mismatches flagged for review


def test_type_column_multi_vendor_export():
    rows = [["Voucher Date", "Supplier Name", "Voucher Type", "Voucher No", "Amount", "Narration"],
            ["2026-04-05", "sri lakshmi plastics", "Purchase", "P-1", 1000, "goods"],
            ["2026-04-25", "Sri Lakshmi Plastic", "Payment", "PV-9", 1000, "against P-1 treds"],
            ["2026-05-02", "Kaveri Packaging", "Purchase", "P-2", 2500, None],
            ["2026-05-02", "Unknown Traders", "Purchase", "P-3", 700, None]]
    cl, bills, pays, notes, _ = run(xlsx(rows), "x.xlsx")
    assert list(bills["Vendor Name"]) == ["Sri Lakshmi Plastics", "Kaveri Packaging", "Unknown Traders"]
    assert pays.iloc[0]["Payment Mode"] == "TReDS" and pays.iloc[0]["Bill No"] == "P-1"
    assert any("approximately" in n for n in notes)


def test_single_type_lists_and_negative_amounts():
    bills_only = [["Invoice No", "Invoice Date", "Supplier", "Invoice Amount"], ["A1", "01/07/2026", "Kaveri Packaging", "5,000"]]
    cl, b, p, _, _ = run(xlsx(bills_only), "b.xlsx", default_kind="Bill")
    assert len(b) == 1 and len(p) == 0 and b.iloc[0]["Bill Amount"] == 5000
    unknown = I.classify(I.build_rows(*[I.read_raw(xlsx(bills_only), "b.xlsx")[0].df, 0, {"Date": 1, "Amount": 3, "Ref": 0, "Vendor": 2}]), "vendor", None)
    assert list(unknown["Kind"]) == ["Review"]
    signed = [["Date", "Details", "Amount"], ["01-07-2026", "Item one", 900], ["05-07-2026", "Item two", -400]]
    cl, b, p, _, _ = run(xlsx(signed), "s.xlsx", default_vendor="Kaveri Packaging")
    assert len(b) == 1 and len(p) == 1


def test_running_balance_only():
    rows = [["Date", "Particulars", "Amount", "Balance"],
            ["01-04-2026", "Opening Balance", None, 0],
            ["05-04-2026", "Goods", 500, 500],
            ["10-04-2026", "Settled", 200, 300],
            ["12-04-2026", "Goods", 100, 400]]
    cl, *_ = run(xlsx(rows), "bal.xlsx", default_vendor="Kaveri Packaging")
    assert list(cl.loc[cl["Kind"] != "Skip", "Kind"]) == ["Bill", "Payment", "Bill"]


def test_header_detected_below_preamble_and_csv_ragged():
    csvtxt = "Report: Vendor ledger\nGenerated 01-10-2026\n\nDate,Particulars,Debit,Credit\n05-04-2026,Invoice INV-7,1000,\n09-04-2026,NEFT,,1000\n"
    cl, b, p, _, det = run(csvtxt.encode(), "l.csv", default_vendor="Kaveri Packaging")
    assert det.header_idx == 3 and len(b) == 1 and len(p) == 1


def test_parse_amount():
    assert I.parse_amount("1,23,456.50") == (123456.5, None)
    assert I.parse_amount("(500.00)") == (-500.0, None)
    assert I.parse_amount("750 Cr") == (750.0, "Cr")
    assert pd.isna(I.parse_amount("abc")[0])


def _pdf_table(rows):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    buf = io.BytesIO()
    t = Table(rows)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    SimpleDocTemplate(buf, pagesize=A4).build([Paragraph("Sri Lakshmi Plastics - Ledger", getSampleStyleSheet()["Title"]), t])
    return buf.getvalue()


def _pdf_text(lines):
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for ln in lines:
        c.drawString(40, y, ln)
        y -= 16
    c.save()
    return buf.getvalue()


def test_pdf_ruled_table():
    rows = [["Date", "Particulars", "Ref No", "Debit", "Credit", "Balance"],
            ["05-04-2026", "Sales Invoice", "SL/001", "50,000.00", "", "50,000.00"],
            ["20-04-2026", "Receipt NEFT", "UTR1", "", "50,000.00", "0.00"],
            ["10-05-2026", "Sales Invoice", "SL/002", "20,000.00", "", "20,000.00"]]
    cl, b, p, _, det = run(_pdf_table(rows), "s.pdf", default_vendor="Sri Lakshmi Plastics")
    assert list(b["Bill No"]) == ["SL/001", "SL/002"] and list(p["Amount Paid"]) == [50000]


def test_pdf_plain_text_lines():
    lines = ["Sri Lakshmi Plastics - Statement of Account", "Date Particulars Amount Balance",
             "05-04-2026 Opening Balance 0.00",
             "06-04-2026 Invoice SL/001 50,000.00 50,000.00",
             "20-04-2026 Receipt NEFT SL/001 50,000.00 0.00",
             "10-05-2026 Invoice SL/002 20,000.00 20,000.00"]
    cl, b, p, _, det = run(_pdf_text(lines), "t.pdf", default_vendor="Sri Lakshmi Plastics")
    assert len(b) == 2 and len(p) == 1 and p.iloc[0]["Bill No"] == "SL/001"


def test_scanned_pdf_gives_clear_error():
    from reportlab.pdfgen import canvas
    buf = io.BytesIO(); c = canvas.Canvas(buf); c.showPage(); c.save()
    with pytest.raises(ValueError, match="scanned"):
        I.read_raw(buf.getvalue(), "scan.pdf")
