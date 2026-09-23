"""
Trial Balance Variance Checker - ICAI AICA Level 2 Capstone Project

Compares actual tax/compliance payments (from Compliance_Master.xlsx ->
"Task Instances") against a Trial Balance file the user uploads/exports
each month, GL-code by GL-code, and flags any difference as a variance.

Usage:
    python generate_variance_report.py Trial_Balance.xlsx

Trial Balance file must have these columns (any sheet/csv):
    Period (mmm-yyyy), GL Code, GL Name, TB Balance
"""

import sys
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

FONT_NAME = "Arial"
MASTER_FILE = "Compliance_Master.xlsx"

HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(name=FONT_NAME, bold=True, color="FFFFFF", size=11)
OK_FILL = PatternFill("solid", fgColor="E2EFDA")
VARIANCE_FILL = PatternFill("solid", fgColor="FCE4E4")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def load_trial_balance(path):
    if path.lower().endswith(".csv"):
        tb = pd.read_csv(path)
    else:
        tb = pd.read_excel(path, engine="openpyxl")
    required = {"Period (mmm-yyyy)", "GL Code", "GL Name", "TB Balance"}
    missing = required - set(tb.columns)
    if missing:
        raise ValueError(f"Trial Balance file is missing columns: {missing}")
    return tb


def load_actual_payments():
    df = pd.read_excel(MASTER_FILE, sheet_name="Task Instances", engine="openpyxl")
    df["Payment Date"] = pd.to_datetime(df["Payment Date"], errors="coerce")
    df["Amount Paid"] = pd.to_numeric(df["Amount Paid"], errors="coerce").fillna(0)
    df = df[df["Payment Date"].notna()].copy()
    df["Period (mmm-yyyy)"] = df["Payment Date"].dt.strftime("%b-%Y")
    actual = (
        df.groupby(["Period (mmm-yyyy)", "GL Code"])["Amount Paid"]
        .sum()
        .reset_index()
        .rename(columns={"Amount Paid": "Actual Amount Paid"})
    )
    return actual


def build_report(tb, actual, out_path):
    merged = tb.merge(actual, on=["Period (mmm-yyyy)", "GL Code"], how="left")
    merged["Actual Amount Paid"] = merged["Actual Amount Paid"].fillna(0)
    merged["Variance (TB - Paid)"] = merged["TB Balance"] - merged["Actual Amount Paid"]
    merged["Flag"] = merged["Variance (TB - Paid)"].abs().le(1).map({True: "OK", False: "VARIANCE"})

    wb = Workbook()
    ws = wb.active
    ws.title = "Variance Report"
    headers = ["Period", "GL Code", "GL Name", "Trial Balance Amount",
               "Actual Amount Paid", "Variance (TB - Paid)", "Flag"]
    for i, h in enumerate(headers, start=1):
        ws.cell(row=1, column=i, value=h)
        ws.cell(row=1, column=i).fill = HEADER_FILL
        ws.cell(row=1, column=i).font = HEADER_FONT
        ws.cell(row=1, column=i).alignment = Alignment(horizontal="center", wrap_text=True)

    for r, row in enumerate(merged.itertuples(index=False), start=2):
        values = [row[0], row[1], row[2], row[3], row[4], row[5], row[6]]
        for c, val in enumerate(values, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.font = Font(name=FONT_NAME, size=10)
            cell.border = BORDER
            if c in (4, 5, 6):
                cell.number_format = "#,##0"
        fill = OK_FILL if row[6] == "OK" else VARIANCE_FILL
        for c in range(1, 8):
            ws.cell(row=r, column=c).fill = fill

    n_variance = int((merged["Flag"] == "VARIANCE").sum())
    total_row = len(merged) + 3
    ws.cell(row=total_row, column=1,
            value=f"{n_variance} of {len(merged)} GL lines show a variance"
                  " (difference > 1) between Trial Balance and actual tax paid.").font = \
        Font(name=FONT_NAME, italic=True, bold=n_variance > 0,
             color="C00000" if n_variance > 0 else "595959")

    widths = [14, 12, 26, 20, 20, 20, 12]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"

    wb.save(out_path)
    return merged, n_variance


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_variance_report.py <TrialBalanceFile.xlsx|.csv>")
        sys.exit(1)
    tb_path = sys.argv[1]
    tb = load_trial_balance(tb_path)
    actual = load_actual_payments()
    out_path = "Variance_Report.xlsx"
    merged, n_variance = build_report(tb, actual, out_path)
    print(f"Saved {out_path}: {len(merged)} GL lines compared, {n_variance} variance(s) flagged.")


if __name__ == "__main__":
    main()
