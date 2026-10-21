"""Make a COMPLETE demo year, FY 2025-26 (April 2025 - March 2026), for Demo Traders - all figures made up:

    sample_data/Demo_Full_Year_FY2025-26/
        2025-04 April ... 2026-03 March   one filled Master Template per month (the books)
        Filed returns/                    GSTR-1 and GSTR-3B for all 12 months + GSTR-9 for the year

    python tools/make_demo_fy2025.py  [output folder]

Planted differences (what the reconciliation should find):
  * Oct 2025  an invoice of Rs 25,000 (tax Rs 4,500) is in the books but was missed in GSTR-1 and GSTR-3B.
              The GSTR-9 is the SYSTEM COMPUTED draft, auto-filled from GSTR-1 / 3B, so it does not have it either:
              GSTR-9 agrees with the returns, and Books vs GSTR-9 shows the Rs 25,000 / Rs 4,500 (to be declared in
              GSTR-9 Table 4B and the tax paid through DRC-03 with interest).
  * Aug 2025  GSTR-3B 3.1(a) is Rs 10,000 short (tax Rs 1,800) ...
  * Sep 2025  ... and Rs 10,000 more in the next GSTR-3B (the shortfall made good) - the year agrees.
  * Jan 2026  a credit note of Rs 10,000 (Table 9B / GSTR-9 4I).
Everything else agrees.
"""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_demo_returns import GSTIN, NAME, g1_rows, g3b_rows, g9_rows, to_pdf  # noqa: E402
from app.gstin import checksum_char  # noqa: E402

FY = "2025-26"
MONTHS = [(4, 2025), (5, 2025), (6, 2025), (7, 2025), (8, 2025), (9, 2025), (10, 2025), (11, 2025), (12, 2025),
          (1, 2026), (2, 2026), (3, 2026)]
MNAME = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
         "November", "December"]
CUST_TN = "33AAACB1234C1Z"
CUST_TN += checksum_char(CUST_TN)
CUST_KA = "29AAACK5678D1Z"
CUST_KA += checksum_char(CUST_KA)
D = Decimal


def month_data(i):
    """Books of month i (0 = April 2025)."""
    m, y = MONTHS[i]
    b2b = [("A", CUST_TN, "Chennai Hardware Mart", D(100000 + 5000 * i), "33"),
           ("B", CUST_KA, "Bengaluru Traders", D(50000), "29")]
    if i == 6:                                                      # October: the invoice later missed in GSTR-1
        b2b.append(("C", CUST_TN, "Chennai Hardware Mart", D(25000), "33"))
    return {"m": m, "y": y, "b2b": b2b, "b2cs": D(40000 + 2000 * i), "exempt": D(5000), "bills": 20,
            "cn": D(10000) if i == 9 else D(0)}


def tax18(v, pos):
    t = (v * D("0.18")).quantize(D("0.01"))
    return (t, D(0), D(0)) if pos != "33" else (D(0), t / 2, t / 2)


def books_template(i, path):
    from openpyxl import load_workbook
    from app import gstr1
    from app.schema import load_schema
    d = month_data(i)
    m, y = d["m"], d["y"]
    gstr1.write_master_template(path, load_schema(), {"gstin": GSTIN, "name": NAME, "legal_name": "Demo Traders"},
                                {"month": m, "year": y, "fy": FY, "frequency": "Monthly"}, sample=False)
    wb = load_workbook(path)
    from datetime import datetime
    first = 1 + sum(len(month_data(k)["b2b"]) + month_data(k)["bills"] for k in range(i))
    n = first
    for tag, g, name, v, pos in d["b2b"]:
        st = "33-Tamil Nadu" if pos == "33" else "29-Karnataka"
        wb["B2B"].append([g, name, f"INV/25-26/{n:04d}", datetime(y, m, 5 + len(tag) + ord(tag) - 65), float(v * D("1.18")),
                          st, "N", None, "Regular B2B", None, 18, float(v), None])
        n += 1
    wb["B2CS"].append(["OE", "33-Tamil Nadu", None, 18, float(d["b2cs"]), None, None])
    wb["Exempt-Nil-NonGST"].append(["Intra-State supplies to unregistered persons", 0, float(d["exempt"]), 0])
    if d["cn"]:
        wb["CDNR"].append([CUST_TN, "Chennai Hardware Mart", "CN/25-26/001", datetime(y, m, 20), "C", "33-Tamil Nadu",
                           "N", "Regular B2B", float(d["cn"] * D("1.18")), None, 18, float(d["cn"]), None])
    # HSN: one taxable line + one exempt line
    taxable = sum((x[3] for x in d["b2b"]), D(0)) + d["b2cs"] - d["cn"]
    igst = sum((tax18(x[3], x[4])[0] for x in d["b2b"]), D(0))
    cg = sum((tax18(x[3], x[4])[1] for x in d["b2b"]), D(0)) + tax18(d["b2cs"], "33")[1] - tax18(d["cn"], "33")[1]
    wb["HSN"].append(["39231090", "Plastic storage boxes", "NOS-NUMBERS", 100 + i, float(taxable + igst + 2 * cg), 18,
                      float(taxable), float(igst), float(cg), float(cg), None])
    wb["HSN"].append(["0401", "Milk", "LTR-LITRES", 500, float(d["exempt"]), 0, float(d["exempt"]), None, None, None, None])
    last = n - 1 + d["bills"]
    wb["Documents"].append(["Invoices for outward supply", f"INV/25-26/{first:04d}", f"INV/25-26/{last:04d}",
                            last - first + 1, 0])
    if d["cn"]:
        wb["Documents"].append(["Credit Note", "CN/25-26/001", "CN/25-26/001", 1, 0])
    wb.save(path)


def returns_of(i):
    """(GSTR-1 figures, GSTR-3B figures) as filed for month i."""
    d = month_data(i)
    filed_b2b = [x for x in d["b2b"] if x[0] != "C"]               # October's invoice C was missed
    v4a = sum((x[3] for x in filed_b2b), D(0))
    t = [sum((tax18(x[3], x[4])[k] for x in filed_b2b), D(0)) for k in range(3)]
    cs = tax18(d["b2cs"], "33")
    cn = tax18(d["cn"], "33")
    g1 = {"n4a": len(filed_b2b), "4A": [v4a, t[0], t[1], t[2], 0], "n7": 1, "7": [d["b2cs"], 0, cs[1], cs[2], 0],
          "8": [0, d["exempt"], 0], "nhsn": 2,
          "12": [v4a + d["b2cs"] - d["cn"] + d["exempt"], t[0], t[1] + cs[1] - cn[1], t[2] + cs[2] - cn[2], 0],
          "13": len(d["b2b"]) + d["bills"] + (1 if d["cn"] else 0) - (1 if i == 6 else 0)}
    if d["cn"]:
        g1.update(ncdnr=1, cdnr=[-d["cn"], 0, -cn[1], -cn[2], 0])
    a_val = v4a + d["b2cs"] - d["cn"]
    a_i, a_c = t[0], t[1] + cs[1] - cn[1]
    g1["liab"] = [a_val + d["exempt"], a_i, a_c, a_c, 0]
    adj = {4: D(-10000), 5: D(10000)}.get(i, D(0))                 # Aug short, Sep made good
    adj_t = (adj * D("0.09")).quantize(D("0.01"))
    a3 = [a_val + adj, a_i, a_c + adj_t, a_c + adj_t, 0]
    itc = [D(3000), D(6000), D(6000), D(0)]
    pay = []
    for payable, credit in ((a3[1], itc[0]), (a3[2], itc[1]), (a3[3], itc[2]), (D(0), D(0))):
        use = min(payable, credit)
        k = len(pay)
        row = [D(0)] * 4
        row[k] = use
        pay.append((payable, row, payable - use))
    g3 = {"a": a3, "b": [0, 0], "c": d["exempt"], "e": 0, "itc": itc, "pay": pay}
    return g1, g3


def gstr9():
    t4a = [D(0)] * 5
    t4b = [D(0)] * 5
    cn = [D(0)] * 5
    pay = {"A": [D(0), D(0), [D(0)] * 4], "B": [D(0), D(0), [D(0)] * 4], "C": [D(0), D(0), [D(0)] * 4]}
    itc = [D(0)] * 4
    exempt = D(0)
    for i in range(12):
        d = month_data(i)
        cs = tax18(d["b2cs"], "33")
        t4a = [t4a[0] + d["b2cs"], t4a[1] + cs[1], t4a[2] + cs[2], t4a[3], 0]
        for x in [x for x in d["b2b"] if x[0] != "C"]:              # auto-filled from GSTR-1: no missed invoice
            tx = tax18(x[3], x[4])
            t4b = [t4b[0] + x[3], t4b[1] + tx[1], t4b[2] + tx[2], t4b[3] + tx[0], 0]
        if d["cn"]:
            c = tax18(d["cn"], "33")
            cn = [cn[0] + d["cn"], cn[1] + c[1], cn[2] + c[2], cn[3], 0]
        exempt += d["exempt"]
        _, g3 = returns_of(i)
        for k, h in zip(("A", "B", "C"), range(3)):
            payable, row, cash = g3["pay"][h]
            pay[k][0] += payable
            pay[k][1] += cash
            pay[k][2] = [a + b for a, b in zip(pay[k][2], [row[1], row[2], row[0], row[3]])]
        itc = [itc[0] + g3["itc"][1], itc[1] + g3["itc"][2], itc[2] + g3["itc"][0], 0]
    return {"4": {"A": t4a, "B": t4b, "I": cn}, "5": {"D": exempt}, "6A": itc,
            "9": {k: (v[0], v[1], v[2]) for k, v in pay.items()}}


def make(out):
    out = Path(out)
    files = []
    for i, (m, y) in enumerate(MONTHS):
        folder = out / f"{y}-{m:02d} {MNAME[m - 1]}"
        folder.mkdir(parents=True, exist_ok=True)
        books_template(i, folder / f"Master_Template_{MNAME[m - 1][:3]}{y}.xlsx")
        g1, g3 = returns_of(i)
        fr = out / "Filed returns"
        fr.mkdir(exist_ok=True)
        arn1, arn3 = f"11/{(m % 12) + 1:02d}/{y + (1 if m == 12 else 0)}", f"20/{(m % 12) + 1:02d}/{y + (1 if m == 12 else 0)}"
        to_pdf(g1_rows(MNAME[m - 1], FY, arn1, g1), fr / f"GSTR1_{GSTIN}_{m:02d}{y}.pdf", "FILED")
        to_pdf(g3b_rows(MNAME[m - 1], FY, arn3, g3), fr / f"GSTR3B_{GSTIN}_{m:02d}{y}.pdf", "FILED")
        files.append(m)
    to_pdf(g9_rows(FY, gstr9()), out / "Filed returns" / f"GSTR9_{GSTIN}_032026.pdf", "SYSTEM COMPUTED")
    return out


if __name__ == "__main__":
    print("written", make(sys.argv[1] if len(sys.argv) > 1 else "Demo_Full_Year_FY2025-26"))
