"""
Creates the sample statement files in /samples (run: python samples/generate_samples.py):

  Sample_Publication_FY2023-24.xlsx / FY2024-25 / FY2025-26   T-form, the firm's own statement layout
  Sample_Company_Statements.xlsx                              Schedule III style, two years in columns
  Sample_Company_Statements.pdf                               the same as a searchable PDF
  CMA_Input_Template.xlsx                                     blank template, one row per CMA head
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from openpyxl import Workbook                                   # noqa: E402
from openpyxl.styles import Font, PatternFill, Alignment        # noqa: E402

from config.constants import PL_HEADS, BS_LIAB_HEADS, BS_ASSET_HEADS, CAPITAL_MOVEMENT_HEADS  # noqa: E402
from core.sample_data import TRADING_LINES, TRADING_NP, KALINGA_LINES, KALINGA_NP  # noqa: E402

B = Font(name="Cambria", size=12, bold=True)
N = Font(name="Cambria", size=12)
ACC = '_ * #,##0_ ;_ * \\-#,##0_ ;_ * "-"??_ ;_ @_ '


def tform_year(fy, path):
    L = {lab: (head, sec, amts) for st, lab, head, sec, amts in TRADING_LINES}
    v = lambda lab: L[lab][2][fy]   # noqa
    wb = Workbook()
    ws = wb.active
    ws.title = "Accounts"
    ws["B1"], ws["B2"], ws["B3"] = "M/S SAMPLE PUBLICATION HOUSE", "Prop : Mrs A. Sample", "PLOT NO-1, SAMPLE NAGAR"
    ws["B5"] = "TRADING AND PROFIT AND LOSS ACCOUNT FOR THE YEAR ENDED 31ST MARCH %d" % fy
    ws["B7"], ws["E7"], ws["F7"], ws["I7"] = "PARTICULARS", "AMOUNT [ RS.]", "PARTICULARS", "AMOUNT [ RS.]"
    trading_l = [("Opening Stock", v("Opening Stock")), ("Purchases", v("Purchases")),
                 ("Carriage Inward", v("Carriage Inward"))]
    gp = v("Sales") + v("Closing Stock") - sum(x for _, x in trading_l)
    trading_l.append(("Gross Profit c/d", gp))
    trading_r = [("Sales", v("Sales")), ("Closing Stock", v("Closing Stock"))]
    r = 9
    for i in range(len(trading_l)):
        ws["B%d" % r], ws["C%d" % r], ws["E%d" % r] = "To", trading_l[i][0], trading_l[i][1]
        if i < len(trading_r):
            ws["F%d" % r], ws["G%d" % r], ws["I%d" % r] = "By", trading_r[i][0], trading_r[i][1]
        r += 1
    ws["E%d" % r] = ws["I%d" % r] = sum(x for _, x in trading_l)
    ws["G%d" % r] = "(As certified by proprietor)"
    r += 2
    exp = [lab for st, lab, head, sec, amts in TRADING_LINES if st == "PL" and sec == "pl"]
    exp = exp[:7] + ["Bank Interest"] + exp[7:]
    exp.insert(exp.index("Repair & Maintenance") + 1, "Depreciation")
    first = True
    for lab in exp:
        ws["B%d" % r], ws["C%d" % r], ws["E%d" % r] = "To", lab, v(lab)
        if first:
            ws["F%d" % r], ws["G%d" % r], ws["I%d" % r] = "By", "Gross Profit b/d", gp
            first = False
        r += 1
    ws["B%d" % r], ws["C%d" % r], ws["E%d" % r] = "To", "Net Profit c/d", TRADING_NP[fy]
    bs = wb.create_sheet("Balance Sheet")
    bs["B1"] = "M/S SAMPLE PUBLICATION HOUSE"
    bs["B5"] = "BALANCE SHEET AS ON 31ST MARCH %d" % fy
    bs["B7"], bs["F7"] = "LIABILITIES", "ASSETS"
    cap, drw, np_ = v("Capital Account"), v("Less: Drawings"), TRADING_NP[fy]
    left = [("CAPITAL ACCOUNT", None, None), ("Opening Capital", cap - np_ + drw, None), ("Add: Net Profit", np_, None),
            ("", cap + drw, None), ("Less: Drawings", drw, cap), ("LOANS & BORROWING", None, None),
            ("Cash Credit Loan", None, v("Cash Credit Loan")), ("CURRENT LIABILITIES & PROVISIONS", None, None),
            ("Sundry Creditors", v("Sundry Creditors"), None), ("Audit Fees Payable", v("Audit Fees Payable"), None),
            ("GST Payable", v("GST Payable"), None)]
    right = [("FIXED ASSETS", None, None)]
    deps = {"Furniture & Fixture": 0.10, "Machinery": 0.15, "Two Wheeler": 0.15}
    for lab, rate in deps.items():
        net = v(lab)
        gross = round(net / (1 - rate))
        right += [(lab, gross, None), ("Less: Depreciation", gross - net, net)]
    right += [("CURRENT ASSETS, LOANS & ADVANCES", None, None), ("Closing Stock", None, v("Closing Stock"))]
    for lab in ("Sundry Debtors", "Security Dep. - Telephone Authority", "Security Dep. - Sales Tax Authority",
                "GST Receivable", "TDS Receivable", "Cash at Bank", "Cash in Hand"):
        right.append((lab, None, v(lab)))
    for i in range(max(len(left), len(right))):
        row = 9 + i
        if i < len(left):
            lab, a, b = left[i]
            bs["B%d" % row], bs["C%d" % row], bs["D%d" % row] = lab or None, a, b
        if i < len(right):
            lab, a, b = right[i]
            bs["F%d" % row], bs["H%d" % row], bs["I%d" % row] = lab, a, b
    wb.save(path)


def company_excel(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Balance Sheet"
    ws["A1"] = "SAMPLE AGRO FOODS PRIVATE LIMITED"
    ws["A2"] = "Balance Sheet as at 31st March 2026"
    ws.append([])
    ws.append(["Particulars", "Note", "31.03.2026", "31.03.2025"])
    for st, lab, head, sec, a in KALINGA_LINES:
        if st == "BS":
            ws.append([lab, None, a[2026], a[2025]])
    pl = wb.create_sheet("Profit and Loss")
    pl["A1"] = "SAMPLE AGRO FOODS PRIVATE LIMITED"
    pl["A2"] = "Statement of Profit and Loss for the year ended 31st March 2026"
    pl.append([])
    pl.append(["Particulars", "Note", "FY 2025-26", "FY 2024-25"])
    for st, lab, head, sec, a in KALINGA_LINES:
        if st == "PL":
            pl.append([lab, None, a[2026], a[2025]])
    pl.append(["Net Profit for the year", None, KALINGA_NP[2026], KALINGA_NP[2025]])
    for w in (ws, pl):
        w.column_dimensions["A"].width = 46
    wb.save(path)


def company_pdf(path):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path, pagesize=A4)
    W, H = A4
    for st, title in (("BS", "Balance Sheet as at 31st March 2026"),
                      ("PL", "Statement of Profit and Loss for the year ended 31st March 2026")):
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(W / 2, H - 50, "SAMPLE AGRO FOODS PRIVATE LIMITED")
        c.drawCentredString(W / 2, H - 66, title)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(50, H - 95, "Particulars")
        c.drawRightString(430, H - 95, "FY 2025-26")
        c.drawRightString(540, H - 95, "FY 2024-25")
        c.setFont("Helvetica", 9)
        y = H - 115
        rows = [(lab, a[2026], a[2025]) for s, lab, head, sec, a in KALINGA_LINES if s == st]
        if st == "PL":
            rows.append(("Net Profit for the year", KALINGA_NP[2026], KALINGA_NP[2025]))
        for lab, a, b in rows:
            c.drawString(50, y, lab)
            c.drawRightString(430, y, format(int(a), ","))
            c.drawRightString(540, y, format(int(b), ","))
            y -= 15
        c.showPage()
    c.save()


def input_template(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "CMA Input"
    ws["A1"] = "CMA Builder V2 - Input Template"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = "Enter audited / provisional figures in rupees under each year. Do not change column 'CMA Head Key'."
    ws.append([])
    ws.append(["Particulars", "Statement", "CMA Head Key", "FY 2024-25", "FY 2025-26"])
    for c in ws[4]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F3864")
    for title, st, heads in (("PROFIT & LOSS", "PL", [(k, l) for k, l, _, _ in PL_HEADS] +
                              [("_reported_net_profit", "Net Profit as per accounts (check only)")]),
                             ("LIABILITIES", "BS", [(k, l) for k, l, _, _ in BS_LIAB_HEADS if k != "new_term_loan"]),
                             ("CAPITAL ACCOUNT", "BS", CAPITAL_MOVEMENT_HEADS),
                             ("ASSETS", "BS", [(k, l) for k, l, _, _ in BS_ASSET_HEADS])):
        ws.append([title])
        ws.cell(ws.max_row, 1).font = Font(bold=True)
        for k, l in heads:
            ws.append([l, st, k])
            for j in (4, 5):
                ws.cell(ws.max_row, j).font = Font(color="0000FF")
    ws.column_dimensions["A"].width = 48
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 16
    ws.column_dimensions["E"].width = 16
    wb.save(path)


def main():
    for fy in (2024, 2025, 2026):
        tform_year(fy, os.path.join(HERE, "Sample_Publication_FY%d-%02d.xlsx" % (fy - 1, fy % 100)))
    company_excel(os.path.join(HERE, "Sample_Company_Statements.xlsx"))
    company_pdf(os.path.join(HERE, "Sample_Company_Statements.pdf"))
    input_template(os.path.join(HERE, "CMA_Input_Template.xlsx"))
    print("Samples written to", HERE)


if __name__ == "__main__":
    main()
