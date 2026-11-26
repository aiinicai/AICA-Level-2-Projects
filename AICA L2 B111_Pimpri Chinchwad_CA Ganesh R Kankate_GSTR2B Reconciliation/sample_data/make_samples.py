"""
Builds two DUMMY input files for demonstrating / testing app.py:

  Sample_Tally_Purchase_Register.xlsx  - Tally columnar Purchase Register layout
                                         (title rows, header row, Grand Total row)
  Sample_GSTR2B.xlsx                   - GST portal layout ("Read me" + "B2B" sheet
                                         with a two-row merged header)

All party names and GSTINs are fictitious.
Run:  python make_samples.py
"""

import os
from datetime import datetime

from openpyxl import Workbook

HERE = os.path.dirname(os.path.abspath(__file__))

ALPHA = "27AAACA1111A1Z5"   # Alpha Steels     - Tier 1 exact (+ 2B invoice split over 2 rates)
BETA = "27AAACB2222B1Z6"    # Beta Services    - Tier 1 exact, TDS "100.00 Cr", ISO date
GAMMA = "24AAACG3333C1Z7"   # Gamma Traders    - Tier 2 normalised (inv-0005 = INV/5), 16% CHECK
DELTA = "29AAACD4444D1Z8"   # Delta Industries - Tier 3 GSTIN total within Rs 1
EPS = "27AAACE5555E1Z9"     # Epsilon Agencies - duplicate booking in books
ZETA = "33AAACZ6666F1Z1"    # Zeta Logistics   - only in 2B


def make_tally(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Purchase Register"
    ws.append(["Demo Manufacturing Pvt Ltd"])
    ws.append(["Purchase Register"])
    ws.append(["1-Apr-2026 to 31-Oct-2026"])
    ws.append([])
    header = [
        "Date", "Particulars", "Voucher Type", "Voucher No.", "Supplier Invoice No.",
        "Supplier Invoice Date", "GSTIN/UIN", "Narration", "Gross Total",
        "Purchase IGST 18%", "Input IGST 18%", "Labour Charges IGST",
        "Purchase Local CGST SGST", "Input CGST 9% Local", "Input SGST",
        "TDS on Labour Charges 194C", "Round Off",
    ]
    ws.append(header)

    def row(dt, party, vno, inv, inv_dt, gstin, narr, gross, **led):
        cols = {h: None for h in header}
        cols.update({"Date": dt, "Particulars": party, "Voucher Type": "Purchase",
                     "Voucher No.": vno, "Supplier Invoice No.": inv,
                     "Supplier Invoice Date": inv_dt, "GSTIN/UIN": gstin,
                     "Narration": narr, "Gross Total": gross})
        cols.update(led)
        ws.append([cols[h] for h in header])

    d = datetime
    row(d(2026, 4, 5), "Alpha Steels", 1, "INV/001", d(2026, 4, 4), ALPHA, "Steel rods", 19824,
        **{"Purchase IGST 18%": 16800, "Input IGST 18%": 3024})
    row(d(2026, 4, 8), "Alpha Steels", 2, "INV/002", d(2026, 4, 7), ALPHA, "Mixed-rate bill", 2300,
        **{"Purchase IGST 18%": 2000, "Input IGST 18%": 300})
    row("2026-10-03", "Beta Services", 3, "B-77", d(2026, 10, 2), BETA, "Labour job", 11700,
        **{"Labour Charges IGST": 10000, "Input IGST 18%": 1800,
           "TDS on Labour Charges 194C": "100.00 Cr"})
    row(d(2026, 5, 10), "Gamma Traders", 4, "inv-0005", d(2026, 5, 9), GAMMA, "16% wrong ledger", 11600,
        **{"Purchase Local CGST SGST": 10000, "Input CGST 9% Local": 800, "Input SGST": 800})
    row(d(2026, 6, 1), "Delta Industries", 5, "D1", d(2026, 6, 1), DELTA, "", 5900,
        **{"Purchase Local CGST SGST": 5000, "Input CGST 9% Local": 450, "Input SGST": 450})
    row(d(2026, 6, 2), "Delta Industries", 6, "D2", d(2026, 6, 2), DELTA, "", 11800,
        **{"Purchase Local CGST SGST": 10000, "Input CGST 9% Local": 900, "Input SGST": 900})
    row(d(2026, 7, 1), "Epsilon Agencies", 7, "E-10", d(2026, 7, 1), EPS, "", 1180,
        **{"Purchase Local CGST SGST": 1000, "Input CGST 9% Local": 90, "Input SGST": 90})
    row(d(2026, 7, 3), "Epsilon Agencies", 8, "E-10", d(2026, 7, 1), EPS, "Booked twice", 1180,
        **{"Purchase Local CGST SGST": 1000, "Input CGST 9% Local": 90, "Input SGST": 90})
    row(d(2026, 8, 1), "Local Kirana (URD)", 9, "C-1", d(2026, 8, 1), None, "Unregistered", 500,
        **{"Purchase Local CGST SGST": 500})
    row(d(2026, 8, 2), "Typo Supplier", 10, "T-1", d(2026, 8, 2), "27ABCDE1234", "Bad GSTIN", 1180,
        **{"Purchase Local CGST SGST": 1000, "Input CGST 9% Local": 90, "Input SGST": 90})
    ws.append([None, "Grand Total", None, None, None, None, None, None, 67164])
    wb.save(path)


def make_2b(path):
    wb = Workbook()
    rm = wb.active
    rm.title = "Read me"
    rm.append(["Goods and Services Tax - GSTR-2B (dummy file for demo)"])
    ws = wb.create_sheet("B2B")
    ws.append(["Goods and Services Tax - GSTR 2B"])
    ws.append(["Taxable inward supplies received from registered persons"])
    ws.append(["GSTIN of supplier", "Trade/Legal name", "Invoice details", None, None, None,
               "Place of supply", "Supply Attract Reverse Charge", "Taxable Value (₹)",
               "Tax Amount", None, None, None, "GSTR-1/IFF/GSTR-5 Period",
               "GSTR-1/IFF/GSTR-5 Filing Date", "ITC Availability"])
    ws.append([None, None, "Invoice number", "Invoice type", "Invoice Date", "Invoice Value(₹)",
               None, None, None, "Integrated Tax(₹)", "Central Tax(₹)", "State/UT Tax(₹)",
               "Cess(₹)", None, None, None])
    ws.merge_cells("C3:F3")
    ws.merge_cells("J3:M3")

    def r(g, name, inv, dt, val, pos, taxable, igst=0, cgst=0, sgst=0, period="Apr'26"):
        ws.append([g, name, inv, "Regular", dt, val, pos, "No", taxable, igst, cgst, sgst, 0,
                   period, "11-05-2026", "Yes"])

    r(ALPHA, "ALPHA STEELS", "INV/001", "04-04-2026", 19824, "27-Maharashtra", 16800, igst=3024)
    # INV/002 split over two tax-rate rows (invoice value repeats on each row)
    r(ALPHA, "ALPHA STEELS", "INV/002", "07-04-2026", 2300, "27-Maharashtra", 1000, igst=120)
    r(ALPHA, "ALPHA STEELS", "INV/002", "07-04-2026", 2300, "27-Maharashtra", 1000, igst=180)
    r(BETA, "BETA SERVICES", "B-77", "02-10-2026", 11800, "27-Maharashtra", 10000, igst=1800, period="Oct'26")
    r(GAMMA, "GAMMA TRADERS", "INV/5", "09-05-2026", 11600, "24-Gujarat", 10000, cgst=800, sgst=800)
    r(DELTA, "DELTA INDUSTRIES", "DX-01", "01-06-2026", 5900.50, "29-Karnataka", 5000, cgst=450, sgst=450)
    r(DELTA, "DELTA INDUSTRIES", "DX-02", "02-06-2026", 11800, "29-Karnataka", 10000, cgst=900, sgst=900)
    r(EPS, "EPSILON AGENCIES", "E10", "01-07-2026", 1180, "27-Maharashtra", 1000, cgst=90, sgst=90)
    r(ZETA, "ZETA LOGISTICS", "Z-99", "15-07-2026", 2360, "33-Tamil Nadu", 2000, igst=360)
    ws.append(["Total", None, None, None, None, 66964.5])
    wb.save(path)


if __name__ == "__main__":
    make_tally(os.path.join(HERE, "Sample_Tally_Purchase_Register.xlsx"))
    make_2b(os.path.join(HERE, "Sample_GSTR2B.xlsx"))
    print("Sample files written to", HERE)
