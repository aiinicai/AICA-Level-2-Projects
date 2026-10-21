"""Make the DEMO filed-return PDFs (GSTR-1, GSTR-3B, GSTR-9) for Demo Traders, FY 2026-27, laid out like the
GST portal downloads, so the reconciliation can be shown without real client data.

    python tools/make_demo_returns.py  [output folder]

All figures are made up. July matches the July Master Template exactly. In August the GSTR-3B under-reports the
B2C sales by Rs 30 (tax Rs 2.40). September has no returns yet. No GSTR-9 is made for FY 2026-27: the year is not
over, so a GSTR-9 cannot exist yet (G9 / g9_rows are kept only for the automated tests).
"""
import sys
from decimal import Decimal
from pathlib import Path

GSTIN = "33DEMOA1234B1ZD"
NAME = "DEMO TRADERS"


def inr(v) -> str:
    """Indian grouping: 1,50,000.00"""
    v = Decimal(str(v)).quantize(Decimal("0.01"))
    neg = v < 0
    s = f"{abs(v):.2f}"
    whole, frac = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return ("-" if neg else "") + whole + "." + frac


def g1_rows(month, fy, arn, d):
    """d: figures of the month. Returns [(text, [cells])] - a row with cells is a table row."""
    z = ["0.00"] * 5
    v5 = lambda x: [inr(a) for a in x]   # noqa: E731
    r = [("FORM GSTR-1", []), ("[See rule 59(1)]", []), ("Details of outward supplies of goods or services", []),
         (f"Financial year {fy}", []), (f"Tax period {month}", []), (f"1 GSTIN {GSTIN}", []),
         (f"2 (a) Legal name of the registered person {NAME}", []), (f"(d) ARN date {arn}", []),
         ("Description No. of records Document Type Value Integrated Tax Central Tax State/UT Tax Cess", []),
         ("4A - Taxable outward supplies made to registered persons (other than reverse charge supplies) - B2B Regular", []),
         ("Total", [str(d.get("n4a", 0)), "Invoice"] + v5(d.get("4A", z))),
         ("4B - Taxable outward supplies made to registered persons attracting tax on reverse charge - B2B Reverse charge", []),
         ("Total", ["0", "Invoice"] + z),
         ("5 - Taxable outward inter-state supplies made to unregistered persons (invoice value above Rs. 1 lakh) - B2CL (Large)", []),
         ("Total", [str(d.get("n5", 0)), "Invoice"] + v5(d.get("5", z))[:2] + [inr(0)]),
         ("6A - Exports (with/without payment)", []),
         ("Total", [str(d.get("n6a", 0)), "Invoice", inr(d.get("expwp", [0, 0])[0] + d.get("expwop", 0)),
                    inr(d.get("expwp", [0, 0])[1]), "0.00"]),
         ("- EXPWP", ["1" if d.get("expwp") else "0", "Invoice", inr(d.get("expwp", [0, 0])[0]),
                      inr(d.get("expwp", [0, 0])[1]), "0.00"]),
         ("- EXPWOP", ["1" if d.get("expwop") else "0", "Invoice", inr(d.get("expwop", 0))]),
         ("6B - Supplies made to SEZ unit or SEZ developer - SEZWP/SEZWOP", []),
         ("Total", ["1" if d.get("sezwp") else "0", "Invoice", inr(d.get("sezwp", [0, 0])[0]),
                    inr(d.get("sezwp", [0, 0])[1]), "0.00"]),
         ("- SEZWP", ["1" if d.get("sezwp") else "0", "Invoice", inr(d.get("sezwp", [0, 0])[0]),
                      inr(d.get("sezwp", [0, 0])[1]), "0.00"]),
         ("- SEZWOP", ["0", "Invoice", "0.00"]),
         ("6C - Deemed Exports - DE", []), ("Total", ["0", "Invoice"] + z),
         ("7 - Taxable supplies (Net of debit and credit notes) to unregistered persons - B2CS (Others)", []),
         ("Total", [str(d.get("n7", 0)), "Net Value"] + v5(d.get("7", z))),
         ("8 - Nil rated, exempted and non GST outward supplies", []),
         ("Total", [inr(sum(d.get("8", [0, 0, 0])))]),
         ("- Nil", [inr(d.get("8", [0, 0, 0])[0])]), ("- Exempted", [inr(d.get("8", [0, 0, 0])[1])]),
         ("- Non-GST", [inr(d.get("8", [0, 0, 0])[2])]),
         ("9A - Amendment to taxable outward supplies made to registered person in returns of earlier tax periods in table 4 - B2B Regular", []),
         ("Amended amount - Total", ["0", "Invoice"] + z), ("Net differential amount (Amended - Original)", z),
         ("9B - Credit/Debit Notes (Registered) - CDNR", []),
         ("Total - Net off debit/credit notes (Debit notes - Credit notes)", [str(d.get("ncdnr", 0)), "Note"] + v5(d.get("cdnr", z))),
         ("Credit / Debit notes issued to registered person for taxable outward supplies in table 4 other than table 6 - B2B Regular", []),
         ("Net Total (Debit notes - Credit notes)", [str(d.get("ncdnr", 0)), "Note"] + v5(d.get("cdnr", z))),
         ("Credit / Debit notes issued to registered person for taxable outward supplies in table 4 other than table 6 - B2B Reverse charge", []),
         ("Net Total (Debit notes - Credit notes)", ["0", "Note"] + z),
         ("9B - Credit/Debit Notes (Unregistered) - CDNUR", []),
         ("Total - Net off debit/credit notes (Debit notes - Credit notes)", [str(d.get("ncdnur", 0)), "Note"]
          + v5(d.get("cdnur", [0, 0]))[:2] + ["0.00"]),
         ("- B2CL", [str(d.get("ncdnur", 0)), "Note"] + v5(d.get("cdnur", [0, 0]))[:2] + ["0.00"]),
         ("- EXPWP", ["0", "Note", "0.00", "0.00", "0.00"]), ("- EXPWOP", ["0", "Note", "0.00"]),
         ("10 - Amendment to taxable outward supplies made to unregistered person in returns for earlier tax periods in table 7 - B2C (Others)", []),
         ("Amended amount - Total", ["0", "Net Value"] + z), ("Net differential amount (Amended - Original)", z),
         ("11A(1), 11A(2) - Advances received for which invoice has not been issued (tax amount to be added to the output tax liability)", []),
         ("Total", ["1" if d.get("11A") else "0", "Net Value"] + v5(d.get("11A", z))),
         ("11B(1), 11B(2) - Advance amount received in earlier tax period and adjusted against the supplies being shown in this tax period", []),
         ("Total", ["1" if d.get("11B") else "0", "Net Value"] + v5(d.get("11B", z))),
         ("12 - HSN-wise summary of outward supplies", []),
         ("Total", [str(d.get("nhsn", 0)), "NA"] + v5(d.get("12", z))),
         ("13 - Documents issued", []), ("Net issued documents", [str(d.get("13", 0)), "All Documents"]),
         ("Total Liability (Outward supplies other than Reverse charge)", v5(d["liab"])),
         ("Verification: I hereby solemnly affirm ... (DEMO - made-up figures, not a real return)", [])]
    return r


def g3b_rows(month, fy, arn, d):
    dash = "-"
    a, b, c, e = d["a"], d["b"], d["c"], d["e"]
    r = [("Form GSTR-3B", []), ("[See rule 61(5)]", []), (f"Year {fy}", []), (f"Period {month}", []),
         (f"GSTIN of the supplier {GSTIN}", []), (f"2(a). Legal name of the registered person {NAME}", []),
         (f"2(d). Date of ARN {arn}", []),
         ("3.1 Details of Outward supplies and inward supplies liable to reverse charge (other than those covered by Table 3.1.1)", []),
         ("Nature of Supplies Total taxable value Integrated tax Central tax State/UT tax Cess", []),
         ("(a) Outward taxable supplies (other than zero rated, nil rated and exempted)", [inr(x) for x in a]),
         ("(b) Outward taxable supplies (zero rated)", [inr(b[0]), inr(b[1]), dash, dash, "0.00"]),
         ("(c) Other outward supplies (nil rated, exempted)", [inr(c), dash, dash, dash, dash]),
         ("(d) Inward supplies (liable to reverse charge)", ["0.00"] * 5),
         ("(e) Non-GST outward supplies", [inr(e), dash, dash, dash, dash]),
         ("3.1.1 Details of Supplies notified under section 9(5) of the CGST Act, 2017", []),
         ("(i) Taxable supplies on which electronic commerce operator pays tax u/s 9(5)", ["0.00"] * 5),
         ("(ii) Taxable supplies made by registered person through electronic commerce operator", ["0.00", dash, dash, dash, dash]),
         ("4. Eligible ITC", []), ("A. ITC Available (whether in full or part)", []),
         ("(1) Import of goods", ["0.00"] * 4), ("(2) Import of services", ["0.00"] * 4),
         ("(3) Inward supplies liable to reverse charge (other than 1 & 2 above)", ["0.00"] * 4),
         ("(4) Inward supplies from ISD", ["0.00"] * 4), ("(5) All other ITC", [inr(x) for x in d["itc"]]),
         ("B. ITC Reversed", []), ("(1) As per rules 38,42 & 43 of CGST Rules and section 17(5)", ["0.00"] * 4),
         ("(2) Others", ["0.00"] * 4), ("C. Net ITC available (A-B)", [inr(x) for x in d["itc"]]),
         ("6.1 Payment of tax", []), ("(A) Other than reverse charge", [])]
    for head, row in zip(("Integrated tax", "Central tax", "State/UT tax", "Cess"), d["pay"]):
        payable, itc, cash = row
        r.append((head, [inr(payable), "0.00", inr(payable)] + [inr(x) for x in itc] + [inr(cash), "0.00", "0.00"]))
    r.append(("(B) Reverse charge and supplies made u/s 9(5)", []))
    for head in ("Integrated tax", "Central tax", "State/UT tax", "Cess"):
        r.append((head, ["0.00", "0.00", "0.00", dash, dash, dash, dash, "0.00", dash, dash]))
    r.append(("Breakup of tax liability declared (for interest computation)", []))
    r.append(("DEMO - made-up figures, not a real return", []))
    return r


def g9_rows(fy, d):
    r = [("Form GSTR-9", []), ("[See rule 80]", []), ("System Drafted Annual Return (Normal Taxpayer) - DEMO", []),
         (f"1. Financial Year {fy}", []), (f"2. GSTIN {GSTIN}", []), (f"3(a). Legal name of the registered person {NAME}", []),
         ("Pt. II Details of Outward and inward supplies made during the financial year", []),
         ("Sr.No Nature of Supplies Taxable Value Central Tax State Tax / UT Tax Integrated Tax Cess", []),
         ("4 Details of advances, inward and outward supplies made during the financial year on which tax is payable", [])]
    names4 = {"A": "Supplies made to un-registered persons (B2C)", "B": "Supplies made to registered persons (B2B)",
              "C": "Zero rated supply (Export) on payment of tax (Except supplies to SEZs)",
              "D": "Supplies to SEZs on payment of tax", "E": "Deemed Exports",
              "F": "Advances on which tax has been paid but invoice has not been issued",
              "G": "Inward supplies on which tax is to be paid on the reverse charge basis",
              "I": "Credit notes issued in respect of transactions specified in (B) to (E) above (-)",
              "J": "Debit notes issued in respect of transactions specified in (B) to (E) above (+)",
              "K": "Supplies / tax declared through Amendments (+)", "L": "Supplies / tax reduced through Amendments (-)"}
    for k, label in names4.items():
        v = d["4"].get(k, [0, 0, 0, 0, 0])            # taxable, central, state, integrated, cess
        r.append((f"{k} {label}", [inr(x) for x in v]))
    r.append(("5 Details of Outward supplies made during the financial year on which tax is not payable", []))
    names5 = {"A": "Zero rated supply (Export) without payment of tax", "B": "Supply to SEZs without payment of tax",
              "C": "Supplies on which tax is to be paid by the recipient on reverse charge", "D": "Exempted",
              "E": "Nil Rated", "F": "Non-GST supply (includes no supply)",
              "H": "Credit Notes issued in respect of transactions specified in A to F above (-)",
              "I": "Debit Notes issued in respect of transactions specified in A to F above (+)",
              "J": "Supplies declared through Amendments (+)", "K": "Supplies reduced through Amendments (-)"}
    for k, label in names5.items():
        r.append((f"{k} {label}", [inr(d["5"].get(k, 0))]))
    r.append(("Pt. III Details of ITC for the financial year", []))
    r.append(("6 Details of ITC availed during the financial year", []))
    r.append(("A Total amount of input tax credit availed through FORM GSTR-3B (sum total of Table 4A)",
              [inr(x) for x in d["6A"]]))                # central, state, integrated, cess
    r.append(("Pt. IV Details of tax paid as declared in returns filed during the financial year", []))
    r.append(("9 Description Tax Payable Paid through Cash Paid through ITC Total Tax Paid Difference", []))
    for k, label in (("A", "Integrated Tax"), ("B", "Central Tax"), ("C", "State/UT Tax"), ("D", "Cess"),
                     ("E", "Interest"), ("F", "Late Fees"), ("G", "Penalty"), ("H", "Other")):
        payable, cash, itc = d["9"].get(k, (0, 0, [0, 0, 0, 0]))
        paid = cash + sum(itc)
        r.append((f"{k} {label}", [inr(payable), inr(cash)] + [inr(x) for x in itc] + [inr(paid), inr(payable - paid)]))
    r.append(("DEMO - made-up figures, not a real return", []))
    return r


def to_text(rows) -> str:
    return "\n".join("  ".join([t] + cells) for t, cells in rows)


def to_pdf(rows, path, watermark):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    W, H = landscape(A4)
    c = canvas.Canvas(str(path), pagesize=(W, H))
    y = H - 40

    def mark():
        c.saveState()
        c.setFillGray(0.85)
        c.setFont("Helvetica-Bold", 110)
        c.translate(W / 2, H / 2)
        c.rotate(35)
        c.drawCentredString(0, -40, watermark)
        c.restoreState()
    mark()
    for text, cells in rows:
        if y < 40:
            c.showPage()
            mark()
            y = H - 40
        if not cells:
            c.setFont("Helvetica-Bold" if len(text) < 60 else "Helvetica", 7.5)
            c.drawString(30, y, text)
        else:
            c.setFont("Helvetica", 7.5)
            c.drawString(30, y, text[:95])
            x = W - 30
            for cell in reversed(cells):
                c.drawRightString(x, y, cell)
                x -= 62
        y -= 13
    c.save()


# ------------------------------------------------------------------ the demo figures
FY = "2026-27"
JUL_G1 = {"n4a": 2, "4A": [15500, 2725, 0, 0, 0], "n5": 1, "5": [150000, 27000], "n6a": 2, "expwp": [200000, 36000],
          "expwop": 100000, "sezwp": [10000, 1800], "n7": 4, "7": [75000, 12200, 0, 0, 0], "8": [7000, 4000, 500],
          "ncdnr": 2, "cdnr": [-500, -90, 0, 0, 0], "ncdnur": 1, "cdnur": [-10000, -1800],
          "11A": [10000, 1800, 0, 0, 0], "11B": [5000, 900, 0, 0, 0], "nhsn": 5, "12": [551500, 77835, 0, 0, 0],
          "13": 200, "liab": [556500, 78735, 0, 0, 0]}
JUL_3B = {"a": [235000, 40935, 0, 0, 0], "b": [310000, 37800], "c": 11000, "e": 500, "itc": [20000, 1500, 1500, 0],
          "pay": [(78735, [20000, 0, 0, 0], 58735), (0, [0, 0, 0, 0], 0), (0, [0, 0, 0, 0], 0), (0, [0, 0, 0, 0], 0)]}
AUG_G1 = {"n7": 2, "7": [330, 0, 10.20, 10.20, 0], "8": [0, 50, 0], "nhsn": 3, "12": [380, 0, 10.20, 10.20, 0],
          "13": 11, "liab": [380, 0, 10.20, 10.20, 0]}
AUG_3B = {"a": [300, 0, 9, 9, 0], "b": [0, 0], "c": 50, "e": 0, "itc": [0, 300, 300, 0],
          "pay": [(0, [0, 0, 0, 0], 0), (9, [0, 0, 0, 0], 9), (9, [0, 0, 0, 0], 9), (0, [0, 0, 0, 0], 0)]}
G9 = {"4": {"A": [225330, 10.20, 10.20, 39200, 0], "B": [15500, 0, 0, 2725, 0], "C": [200000, 0, 0, 36000, 0],
            "D": [10000, 0, 0, 1800, 0], "F": [5000, 0, 0, 900, 0], "I": [11000, 0, 0, 1980, 0], "J": [500, 0, 0, 90, 0]},
      "5": {"A": 100000, "D": 4050, "E": 7000, "F": 500},
      "6A": [1800, 1800, 20000, 0],
      "9": {"A": (78735, 58735, [0, 0, 20000, 0]), "B": (Decimal("10.20"), 9, [0, 0, 0, 0]),
            "C": (Decimal("10.20"), 9, [0, 0, 0, 0])}}

FILES = {
    f"GSTR1_{GSTIN}_072026.pdf": (lambda: g1_rows("July", FY, "11/08/2026", JUL_G1), "FILED"),
    f"GSTR3B_{GSTIN}_072026.pdf": (lambda: g3b_rows("July", FY, "20/08/2026", JUL_3B), "FILED"),
    f"GSTR1_{GSTIN}_082026.pdf": (lambda: g1_rows("August", FY, "11/09/2026", AUG_G1), "FILED"),
    f"GSTR3B_{GSTIN}_082026.pdf": (lambda: g3b_rows("August", FY, "20/09/2026", AUG_3B), "FILED"),
}

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    for name, (rows, mark) in FILES.items():
        to_pdf(rows(), out / name, mark)
        print("written", out / name)
