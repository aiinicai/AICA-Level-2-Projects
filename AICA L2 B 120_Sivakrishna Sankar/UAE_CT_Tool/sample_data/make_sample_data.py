"""Generates SYNTHETIC test data (a fictional company - none of this is real client data).

Run:  python sample_data/make_sample_data.py [output_dir] [--currency USD|EUR|AED ...]

Creates, in the output folder:
  Sample_TB_<CCY>.xlsx / .csv / .pdf / _scanned.pdf   trial balance (closing balances, 31 Dec 2025)
  Sample_GL_<CCY>.xlsx                                general ledger that reconciles exactly to the TB
  Sample_TB_prior_year_<CCY>.xlsx                     prior-year TB (for movement analysis)
  Sample_expected.json                                the figures the data were built to contain (used by the tests)

The data deliberately contain: entertainment, donations, fines, personal/director expenses, vague narrations,
round-sum and year-end entries, related-party management fees and interest, dividend income, a fair-value gain,
a bad-debt provision, foreign exchange differences, withholding tax suffered abroad, and one unmapped suspense account.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

ENTITY = "Sample Gulf Trading LLC (synthetic)"
YEAR = 2025

# (code, name, nature, closing balance in TB currency [debit +, credit -])
# P&L amounts are for the year; balance sheet amounts are closing balances.
BS = [
    ("1000", "Cash at bank - current account", 4_700_000.00),
    ("1010", "Petty cash", 4_500.00),
    ("1100", "Trade receivables", 2_400_000.00),
    ("1110", "Allowance for doubtful debts", -120_000.00),
    ("1200", "Due from related party - Sample Holdings Ltd", 650_000.00),
    ("1300", "Prepayments and deposits", 210_000.00),
    ("1400", "Investment in subsidiary - Sample Trading UK Ltd", 1_200_000.00),
    ("1410", "Investments at fair value through profit or loss - quoted equities", 980_000.00),
    ("1500", "Property, plant and equipment - cost", 1_100_000.00),
    ("1510", "Accumulated depreciation", -420_000.00),
    ("1900", "Suspense account", 18_250.00),
    ("2000", "Trade payables", -1_350_000.00),
    ("2100", "Accrued expenses", -310_000.00),
    ("2200", "Loan from shareholder - Sample Holdings Ltd", -1_500_000.00),
    ("2300", "Bank loan", -900_000.00),
    ("2400", "Provision for employees' end of service benefits", -240_000.00),
    ("2500", "VAT payable", -95_000.00),
    ("3000", "Share capital", -1_000_000.00),
]
PL = [
    ("4000", "Sales - goods", -14_800_000.00),
    ("4100", "Service revenue", -2_900_000.00),
    ("4200", "Dividend income - Sample Trading UK Ltd", -300_000.00),
    ("4300", "Unrealised gain on fair value of investments", -85_000.00),
    ("4500", "Interest income - bank deposits", -42_000.00),
    ("4600", "Foreign exchange gain", -37_500.00),
    ("5000", "Cost of goods sold", 10_200_000.00),
    ("6000", "Salaries and wages", 2_150_000.00),
    ("6010", "Office rent", 420_000.00),
    ("6020", "Client entertainment and hospitality", 96_000.00),
    ("6030", "Donations", 40_000.00),
    ("6040", "Fines and penalties", 15_500.00),
    ("6050", "Professional and legal fees", 180_000.00),
    ("6060", "Depreciation expense", 160_000.00),
    ("6070", "Interest expense - shareholder loan", 75_000.00),
    ("6080", "Bank interest and charges", 66_000.00),
    ("6090", "Impairment of trade receivables - provision for doubtful debts", 70_000.00),
    ("6100", "Repairs and maintenance", 55_000.00),
    ("6110", "Miscellaneous expenses", 48_000.00),
    ("6120", "Management fee - Sample Holdings Ltd", 240_000.00),
    ("6130", "Foreign exchange loss", 21_000.00),
    ("6140", "Withholding tax suffered abroad", 30_000.00),
    ("6150", "Director personal expenses", 27_500.00),
    ("6160", "Staff end of service benefit expense", 60_000.00),
]
RETAINED_CODE, RETAINED_NAME = "3100", "Retained earnings - opening"

SUPPLIERS = ["Gulf Wholesale FZE", "Al Reem Supplies LLC", "Dubai Office Rentals", "Orient Logistics", "Noor Legal Consultants", "City Auto Care", "Bright Stationery"]
CUSTOMERS = ["Hamdan Trading Co", "Skyline Contracting LLC", "Desert Retail FZE", "Pearl Distribution", "Falcon Industries LLC"]
COUNTERPARTIES = ["Gulf Wholesale FZE", "Al Reem Supplies LLC", "Dubai Office Rentals", "Marina Hospitality LLC", "Orient Logistics",
                  "Noor Legal Consultants", "City Auto Care", "Sample Holdings Ltd", "Sample Trading UK Ltd", "Bright Stationery"]


def build(currency: str = "USD", scale: float = 1.0, seed: int = 7):
    rnd = random.Random(seed)
    sc = lambda x: round(x * scale, 2)
    bs = [(c, n, sc(v)) for c, n, v in BS]
    pl = [(c, n, sc(v)) for c, n, v in PL]
    pl_total = sum(v for _, _, v in pl)                      # negative = profit
    bs_total = sum(v for _, _, v in bs)
    retained = -(bs_total + pl_total)                        # opening RE (credit negative) so that TB balances
    retained = round(retained, 2)
    tb = bs + [(RETAINED_CODE, RETAINED_NAME, retained)] + pl
    assert abs(sum(v for _, _, v in tb)) < 0.01, sum(v for _, _, v in tb)

    # ---------------- general ledger ----------------
    lines = []
    n = [0]

    def add(d, code, name, desc, amount, cp="", ref=""):
        n[0] += 1
        lines.append({"date": d, "code": code, "name": name, "desc": desc, "debit": round(max(amount, 0), 2), "credit": round(max(-amount, 0), 2),
                      "cp": cp, "ref": ref or f"JV{n[0]:05d}"})

    start = date(YEAR, 1, 1)
    # opening balances for BS accounts: 85% of closing, except share capital & suspense which are unchanged
    opening = {}
    for c, nm, v in bs:
        opening[c] = v if c in ("3000",) else (0.0 if c == "1900" else round(v * 0.85, 2))
    opening[RETAINED_CODE] = retained                      # RE in the TB is the opening RE (current profit sits in P&L accounts)
    opening["1000"] = round(opening["1000"] - sum(opening.values()), 2)   # cash absorbs the difference so opening balances sum to zero
    for c, nm, v in bs + [(RETAINED_CODE, RETAINED_NAME, retained)]:
        if abs(opening[c]) > 0:
            add(start, c, nm, "Opening balance", opening[c], ref="OPENING")
    # BS retained earnings closing in TB = opening RE only (profit is in P&L accounts), so no movement
    # BS movements
    for c, nm, v in bs:
        mv = round(v - opening[c], 2)
        if abs(mv) < 0.005:
            continue
        parts = rnd.randint(3, 6)
        shares = [rnd.random() + 0.3 for _ in range(parts)]
        tot = sum(shares)
        amts = [round(mv * s / tot, 2) for s in shares]
        amts[-1] = round(mv - sum(amts[:-1]), 2)
        for i, a in enumerate(amts):
            d = start + timedelta(days=int((i + 1) * 340 / parts) + rnd.randint(0, 9))
            add(d, c, nm, "Movement for the period - " + nm.split(" - ")[0], a, cp=("Sample Holdings Ltd" if c in ("1200", "2200") else ""))
    # P&L accounts
    narr = {
        "4000": ["Invoice - customer sales", "Sales invoice batch", "Export sales"],
        "4100": ["Service invoice", "Consulting services rendered", "Maintenance contract income"],
        "4200": ["Dividend received from subsidiary"],
        "4300": ["Revaluation of quoted equities to market price at year end"],
        "4500": ["Interest credited by bank"],
        "4600": ["Exchange gain on settlement of foreign currency balances"],
        "5000": ["Purchase of goods for resale", "Cost of sales", "Freight and clearing"],
        "6000": ["Payroll - month", "Salaries and allowances"],
        "6010": ["Office rent - quarter"],
        "6020": ["Client dinner", "Hospitality - customers", "Entertainment - event tickets", "Customer gifts and hospitality"],
        "6030": ["Donation to charity", "Donation - school fundraising"],
        "6040": ["Traffic fine - company vehicle", "VAT late registration penalty"],
        "6050": ["Legal fees - contract review", "Audit and tax advisory fees"],
        "6060": ["Depreciation charge for the year"],
        "6070": ["Interest on shareholder loan accrued"],
        "6080": ["Bank interest", "Bank charges"],
        "6090": ["Provision for doubtful debts - year end"],
        "6100": ["Repairs - office", "Vehicle repairs"],
        "6110": ["Misc expenses", "Sundry adjustment", "Expenses as per management", "Various"],
        "6120": ["Management fee charged by shareholder"],
        "6130": ["Exchange loss on revaluation of foreign currency payables"],
        "6140": ["Withholding tax deducted at source on foreign income"],
        "6150": ["Director - personal expenses paid by company", "Director holiday ticket", "Family expense - paid by company"],
        "6160": ["End of service benefit charge"],
    }
    for c, nm, v in pl:
        ns = narr.get(c, ["Entry"])
        k = {"4200": 1, "4300": 1, "6060": 1, "6090": 1, "6070": 4, "6030": 3, "6040": 2, "6120": 4, "6010": 4, "6150": 3, "6020": 12, "6110": 8,
             "6000": 12, "4000": 14, "4100": 10, "5000": 14}.get(c, 4)
        shares = [rnd.random() + 0.5 for _ in range(k)]
        tot = sum(shares)
        amts = [round(v * s / tot, 2) for s in shares]
        amts[-1] = round(v - sum(amts[:-1]), 2)
        for i, a in enumerate(amts):
            d = start + timedelta(days=min(364, int((i + 0.5) * 365 / k)))
            cp = ""
            if c in ("6120", "6070"):
                cp = "Sample Holdings Ltd"
            elif c == "4200":
                cp = "Sample Trading UK Ltd"
            elif c in ("4000", "4100"):
                cp = rnd.choice(CUSTOMERS)
            elif c == "6020":
                cp = rnd.choice(["Marina Hospitality LLC", "Corniche Restaurant", "Event Tickets Co"])
            elif c in ("6100", "6050", "5000", "6010"):
                cp = rnd.choice(SUPPLIERS)
            desc = ns[i % len(ns)]
            if c == "4300" or c == "6090" or c == "6060":
                d = date(YEAR, 12, 31)
            add(d, c, nm, desc, a, cp=cp)
    # make some deliberate test patterns by editing a few generated lines (amount-preserving)
    # 1. round-sum entries inside 6110
    ms = [l for l in lines if l["code"] == "6110"]
    if len(ms) >= 3:
        diff = round(ms[0]["debit"] - 10_000.00, 2)
        ms[0]["debit"], ms[1]["debit"] = 10_000.00, round(ms[1]["debit"] + diff, 2)
        ms[0]["desc"] = "Misc"
        ms[2]["desc"] = "Adjustment"
    # 2. year-end entries: move two entertainment lines to 30 Dec
    ent = [l for l in lines if l["code"] == "6020"]
    for l in ent[-2:]:
        l["date"] = date(YEAR, 12, 30)
    gl = sorted(lines, key=lambda l: (l["date"], l["code"]))
    # verify
    gl_net = {}
    for l in gl:
        gl_net[l["code"]] = gl_net.get(l["code"], 0.0) + l["debit"] - l["credit"]
    for c, nm, v in tb:
        got = round(gl_net.get(c, 0.0), 2)
        assert abs(got - v) < 0.02, (c, got, v)
    assert abs(sum(l["debit"] - l["credit"] for l in gl)) < 0.05
    expected = {
        "entity": ENTITY, "currency": currency, "scale": scale, "profit_before_tax": round(-pl_total, 2),
        "revenue": round(-sum(v for c, _, v in pl if c in ("4000", "4100")), 2),
        "entertainment": [v for c, _, v in pl if c == "6020"][0], "donations": [v for c, _, v in pl if c == "6030"][0],
        "fines": [v for c, _, v in pl if c == "6040"][0], "personal": [v for c, _, v in pl if c == "6150"][0],
        "dividend_income": -[v for c, _, v in pl if c == "4200"][0], "unrealised_gain": -[v for c, _, v in pl if c == "4300"][0],
        "tb_rows": len(tb), "gl_rows": len(gl), "suspense": [v for c, _, v in bs if c == "1900"][0],
    }
    return tb, gl, expected


def prior_year(tb, factor=0.8):
    out = []
    for c, n, v in tb:
        out.append((c, n, round(v * (factor if c[0] in "456" else 0.9 if c not in ("3000", "3100") else 1.0), 2)))
    return out


def write_tb_xlsx(path, tb, currency, title_year=YEAR):
    wb = Workbook()
    ws = wb.active
    ws.title = "Trial Balance"
    ws["A1"] = ENTITY
    ws["A1"].font = Font(bold=True, size=12)
    ws["A2"] = f"Trial Balance as at 31 December {title_year}"
    ws["A3"] = f"All amounts in {currency}"
    hdr = ["Account Code", "Account Name", "Debit", "Credit"]
    for i, h in enumerate(hdr, 1):
        ws.cell(5, i, h).font = Font(bold=True)
    r = 6
    td = tc = 0.0
    for c, n, v in tb:
        ws.cell(r, 1, c)
        ws.cell(r, 2, n)
        if v >= 0:
            ws.cell(r, 3, v)
            td += v
        else:
            ws.cell(r, 4, -v)
            tc += -v
        for col in (3, 4):
            ws.cell(r, col).number_format = "#,##0.00"
        r += 1
    ws.cell(r, 2, "Total").font = Font(bold=True)
    ws.cell(r, 3, round(td, 2)).number_format = "#,##0.00"
    ws.cell(r, 4, round(tc, 2)).number_format = "#,##0.00"
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 62
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 18
    wb.save(path)


def write_tb_csv(path, tb):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Account Code", "Account Name", "Debit", "Credit"])
        for c, n, v in tb:
            w.writerow([c, n, f"{v:.2f}" if v >= 0 else "", f"{-v:.2f}" if v < 0 else ""])


def write_gl_xlsx(path, gl, currency):
    wb = Workbook()
    ws = wb.active
    ws.title = "General Ledger"
    ws["A1"] = ENTITY
    ws["A2"] = f"General Ledger 1 Jan {YEAR} to 31 Dec {YEAR} ({currency})"
    hdr = ["Date", "Account Code", "Account Name", "Description", "Debit", "Credit", "Counterparty", "Reference"]
    for i, h in enumerate(hdr, 1):
        ws.cell(4, i, h).font = Font(bold=True)
    for r, l in enumerate(gl, 5):
        ws.cell(r, 1, l["date"]).number_format = "dd/mm/yyyy"
        ws.cell(r, 2, l["code"])
        ws.cell(r, 3, l["name"])
        ws.cell(r, 4, l["desc"])
        ws.cell(r, 5, l["debit"] or None).number_format = "#,##0.00"
        ws.cell(r, 6, l["credit"] or None).number_format = "#,##0.00"
        ws.cell(r, 7, l["cp"])
        ws.cell(r, 8, l["ref"])
    for k, w in zip("ABCDEFGH", (12, 12, 48, 52, 16, 16, 26, 12)):
        ws.column_dimensions[k].width = w
    wb.save(path)


def write_tb_pdf(path, tb, currency):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
    st = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
    data = [["Account Code", "Account Name", "Debit", "Credit"]]
    td = tc = 0.0
    for c, n, v in tb:
        data.append([c, n, f"{v:,.2f}" if v >= 0 else "", f"{-v:,.2f}" if v < 0 else ""])
        td += max(v, 0)
        tc += max(-v, 0)
    data.append(["", "Total", f"{td:,.2f}", f"{tc:,.2f}"])
    t = Table(data, colWidths=[70, 280, 90, 90], repeatRows=1)
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8), ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey)]))
    doc.build([Paragraph(ENTITY, st["Heading2"]), Paragraph(f"Trial Balance as at 31 December {YEAR} - amounts in {currency}", st["Normal"]),
               Spacer(1, 8), t])


def write_tb_plain_pdf(path, tb, currency):
    """Text-layer PDF WITHOUT table lines (typical accounting-system print): amounts right-aligned under Debit / Credit."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    y = h - 50
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, ENTITY)
    c.setFont("Helvetica", 9)
    y -= 16
    c.drawString(40, y, f"Trial Balance as at 31 December {YEAR} - amounts in {currency}")
    y -= 28

    def header():
        nonlocal y
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, "Account Code")
        c.drawString(110, y, "Account Name")
        c.drawRightString(460, y, "Debit")
        c.drawRightString(540, y, "Credit")
        c.setFont("Helvetica", 9)
        y -= 16
    header()
    td = tc = 0.0
    for code, name, v in tb:
        if y < 50:
            c.showPage()
            y = h - 50
            header()
        c.drawString(40, y, code)
        c.drawString(110, y, name)
        if v >= 0:
            c.drawRightString(460, y, f"{v:,.2f}")
            td += v
        else:
            c.drawRightString(540, y, f"{-v:,.2f}")
            tc += -v
        y -= 13
    c.setFont("Helvetica-Bold", 9)
    c.drawString(110, y - 4, "Total")
    c.drawRightString(460, y - 4, f"{td:,.2f}")
    c.drawRightString(540, y - 4, f"{tc:,.2f}")
    c.save()


def write_tb_scanned_pdf(path, tb_pdf_path):
    """Rasterise the text PDF and re-save it as an image-only PDF (simulates a scan; used to test OCR)."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(str(tb_pdf_path))
    imgs = [pdf[i].render(scale=300 / 72).to_pil().convert("L") for i in range(len(pdf))]
    imgs[0].save(str(path), save_all=True, append_images=imgs[1:], resolution=300)


def main(argv):
    out = Path(argv[1]) if len(argv) > 1 and not argv[1].startswith("--") else Path(__file__).parent / "generated"
    ccys = []
    if "--currency" in argv:
        i = argv.index("--currency")
        ccys = [a.upper() for a in argv[i + 1:] if not a.startswith("--")]
    ccys = ccys or ["USD", "EUR", "AED"]
    out.mkdir(parents=True, exist_ok=True)
    for ccy in ccys:
        tb, gl, exp = build(ccy)
        write_tb_xlsx(out / f"Sample_TB_{ccy}.xlsx", tb, ccy)
        write_gl_xlsx(out / f"Sample_GL_{ccy}.xlsx", gl, ccy)
        write_tb_xlsx(out / f"Sample_TB_prior_year_{ccy}.xlsx", prior_year(tb), ccy, YEAR - 1)
        if ccy == "USD":
            write_tb_csv(out / f"Sample_TB_{ccy}.csv", tb)
            write_tb_pdf(out / f"Sample_TB_{ccy}.pdf", tb, ccy)
            write_tb_plain_pdf(out / f"Sample_TB_{ccy}_plain.pdf", tb, ccy)
            try:
                write_tb_scanned_pdf(out / f"Sample_TB_{ccy}_scanned.pdf", out / f"Sample_TB_{ccy}_plain.pdf")
            except Exception as e:  # pragma: no cover
                print("scanned PDF not created:", e)
        (out / f"Sample_expected_{ccy}.json").write_text(json.dumps(exp, indent=2, default=str))
        print(f"{ccy}: {len(tb)} TB accounts, {len(gl)} GL lines, profit {exp['profit_before_tax']:,.2f}")
    print("Written to", out)


if __name__ == "__main__":
    main(sys.argv)
