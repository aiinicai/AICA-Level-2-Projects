"""Makes tests/excel_check.xlsx: an independent check of the dashboard's value of funds and shares, done with
ordinary Excel formulas (no Python, no JavaScript) on the same database tables.

On the Check sheet: type an 'As on' date (a month end or the latest date). Excel works out, for every holding,
units = purchases and SIPs up to the date less sales, price = latest price on or before the date, value = units x price.
Compare the total with the dashboard's Mutual funds + Equity shares on the same date.
Needs Excel 2019 or Microsoft 365 (MAXIFS). Open it and let it calculate.
"""
import csv
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

ROOT = Path(__file__).resolve().parent.parent


def rows(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main(db=ROOT / "db_dummy", out=ROOT / "tests" / "excel_check.xlsx", asof="2026-11-25"):
    ins = {r["key"]: r for r in rows(Path(db) / "instruments.csv")}
    tx = rows(Path(db) / "transactions.csv")
    px = rows(Path(db) / "prices.csv")
    wb = Workbook()
    ws = wb.active
    ws.title = "Check"
    wt = wb.create_sheet("Transactions")
    wp = wb.create_sheet("Prices")
    wt.append(["date", "account", "key", "action", "qty", "price"])
    for r in tx:
        wt.append([date.fromisoformat(r["date"]), r["account"], r["key"], r["action"], float(r["qty"]), float(r["price"])])
    wp.append(["date", "key", "price"])
    for r in px:
        wp.append([date.fromisoformat(r["date"]), r["key"], float(r["price"])])
    for w in (wt, wp):
        for c in w["A"][1:]:
            c.number_format = "yyyy-mm-dd"
    n_t, n_p = len(tx) + 1, len(px) + 1
    pairs = sorted({(r["account"], r["key"]) for r in tx})
    ws["A1"] = "Independent Excel check of the dashboard: value of mutual funds and shares"
    ws["A1"].font = Font(bold=True, size=13)
    ws["A3"], ws["B3"] = "As on (type a date)", date.fromisoformat(asof)
    ws["B3"].number_format = "yyyy-mm-dd"
    ws["B3"].fill = PatternFill("solid", fgColor="FFF2CC")
    ws["A4"], ws["B4"] = "Dashboard says: Mutual funds + Equity shares value (type it)", None
    ws["B4"].fill = PatternFill("solid", fgColor="FFF2CC")
    ws["A5"], ws["B5"] = "Excel total (below)", None
    ws["A6"], ws["B6"] = "Difference", "=IF(B4=\"\",\"type the dashboard value in B4\",ROUND(B5-B4,0))"
    hdr = ["Account", "Key", "Name", "Kind", "Units on date", "Price date used", "Price", "Value"]
    ws.append([])
    ws.append(hdr)
    h = ws.max_row
    for c in ws[h]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1E3A5F")
    T = f"Transactions!$A$2:$A${n_t}"
    A, K, X, Q = (f"Transactions!${c}$2:${c}${n_t}" for c in "BCDE")
    PD, PK, PP = (f"Prices!${c}$2:${c}${n_p}" for c in "ABC")
    first = h + 1
    for acct, key in pairs:
        r = ws.max_row + 1
        units = (f'=SUMIFS({Q},{A},$A{r},{K},$B{r},{X},"<>SELL",{T},"<="&$B$3)-SUMIFS({Q},{A},$A{r},{K},$B{r},{X},"SELL",{T},"<="&$B$3)')
        ws.append([acct, key, ins[key]["name"], ins[key]["kind"], units,
                   f'=_xlfn.MAXIFS({PD},{PK},$B{r},{PD},"<="&$B$3)', f"=SUMIFS({PP},{PK},$B{r},{PD},$F{r})", f"=E{r}*G{r}"])
        ws[f"F{r}"].number_format = "yyyy-mm-dd"
        for col in "EGH":
            ws[f"{col}{r}"].number_format = "#,##0.0000" if col == "G" else "#,##0.000" if col == "E" else "#,##,##0"
    last = ws.max_row
    ws["B5"] = f"=ROUND(SUM(H{first}:H{last}),0)"
    ws["B5"].number_format = "#,##0"
    ws["B5"].font = Font(bold=True)
    for col, w in zip("ABCDEFGH", (46, 16, 48, 8, 16, 16, 14, 16)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = ws.cell(row=h + 1, column=1)
    wb.calculation.fullCalcOnLoad = True
    wb.save(out)
    print("saved", out, len(pairs), "holdings")


if __name__ == "__main__":
    main(*sys.argv[1:2] and [sys.argv[1]])
