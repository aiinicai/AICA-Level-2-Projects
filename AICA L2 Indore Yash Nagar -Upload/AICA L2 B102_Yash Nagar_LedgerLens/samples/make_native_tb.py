"""Write a trial balance in TallyPrime's own Excel export layout for the sample company (full year FY 2024-25).

Mimics a real export: company and address rows, 'Trial Balance', the period, a merged header block
(Particulars | Opening Balance | Transactions Debit/Credit | Closing Balance), Dr/Cr carried in each cell's number
format, and stock shown as a single 'Opening Stock' line.

Usage: python samples/make_native_tb.py
"""
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font

HERE = Path(__file__).parent
BAL = {"Dr": '""0.00" Dr"', "Cr": '""0.00" Cr"'}
TX = '""0.00'


def build(period_text: str = "For 1-Apr-24 to 31-Mar-25", single_stock_line: bool = True) -> Workbook:
    df = pd.read_csv(HERE / "rpi_trial_balance.csv")
    if single_stock_line:   # Tally's TB shows stock-in-hand as one 'Opening Stock' line
        stock = df[df["group"] == "Stock-in-Hand"]
        merged = {"name": "Opening Stock", "group": "Stock-in-Hand", "primary_group": "Stock-in-Hand",
                  "opening_amount": stock["opening_amount"].sum(), "opening_dr_cr": "Dr", "period_debit": 0.0,
                  "period_credit": 0.0, "closing_amount": stock["closing_amount"].sum(), "closing_dr_cr": "Dr"}
        df = pd.concat([df[df["group"] != "Stock-in-Hand"], pd.DataFrame([merged])], ignore_index=True)
    df = pd.concat([df[df["name"] == "Opening Stock"], df[df["name"] != "Opening Stock"].sort_values("name", key=lambda s: s.str.lower())])

    wb = Workbook()
    ws = wb.active
    ws.title = "Trial Balance"
    company = "Rajasthan Precision Industries Private Limited"
    ws["A1"], ws["A2"], ws["A3"], ws["A4"] = company, "Plot No. 45, Sitapura Industrial Area, Jaipur", "Trial Balance", period_text
    for r in range(1, 5):
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    ws["A1"].font = ws["A3"].font = Font(bold=True)
    ws["B5"] = company
    ws.merge_cells("B5:E5")
    ws["A6"], ws["B6"] = "Particulars", period_text
    ws.merge_cells("B6:E6")
    ws["B7"], ws["C7"], ws["E7"] = "Opening", "Transactions", "Closing"
    ws.merge_cells("C7:D7")
    ws["B8"], ws["C8"], ws["D8"], ws["E8"] = "Balance", "Debit", "Credit", "Balance"
    for row in ws["A6:E8"]:
        for c in row:
            c.font = Font(bold=True)

    r = 9
    for x in df.itertuples(index=False):
        ws.cell(r, 1, x.name)
        if x.opening_amount:
            c = ws.cell(r, 2, float(x.opening_amount))
            c.number_format = BAL[x.opening_dr_cr]
        if x.period_debit:
            ws.cell(r, 3, float(x.period_debit)).number_format = TX
        if x.period_credit:
            ws.cell(r, 4, float(x.period_credit)).number_format = TX
        if x.closing_amount:
            c = ws.cell(r, 5, float(x.closing_amount))
            c.number_format = BAL[x.closing_dr_cr]
        r += 1
    ws.column_dimensions["A"].width = 40
    for col in "BCDE":
        ws.column_dimensions[col].width = 20
    return wb


if __name__ == "__main__":
    out = HERE / "tally_trial_balance_export.xlsx"
    build().save(out)
    print(f"Wrote {out}")
