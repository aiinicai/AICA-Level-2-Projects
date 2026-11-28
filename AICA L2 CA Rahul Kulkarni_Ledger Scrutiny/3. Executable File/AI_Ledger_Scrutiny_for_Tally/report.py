"""
report.py  -  Audit working paper in Excel (one click download from the app).
Sheets: Summary, Exceptions (all), one sheet per High-risk rule, Benford, AI Anomalies.
"""

import io
from datetime import datetime

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

FILL = {"High": "F8D7DA", "Medium": "FFF3CD", "Low": "D1ECF1", "Info": "E2E3E5"}


def _format(ws, df):
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F3864")
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, col in enumerate(df.columns, 1):
        width = min(max(len(str(col)), *(len(str(v)) for v in df[col].head(300))) + 2, 60) if len(df) else 15
        ws.column_dimensions[get_column_letter(i)].width = width
    if "severity" in df.columns:
        si = list(df.columns).index("severity") + 1
        for row in ws.iter_rows(min_row=2):
            sev = row[si - 1].value
            if sev in FILL:
                for c in row:
                    c.fill = PatternFill("solid", fgColor=FILL[sev])
    if "amount" in df.columns:
        ai = list(df.columns).index("amount") + 1
        for row in ws.iter_rows(min_row=2, min_col=ai, max_col=ai):
            row[0].number_format = "#,##,##0.00"
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def build_excel(exc, summary, extras, company="", period=""):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        head = pd.DataFrame({
            "Particulars": ["Company", "Period", "Generated on", "Vouchers scrutinised",
                            "Ledger lines", "Total exceptions", "Benford verdict"],
            "Value": [company, period, datetime.now().strftime("%d-%b-%Y %H:%M"),
                      extras["stats"]["vouchers"], extras["stats"]["lines"], len(exc),
                      f"{extras['benford_verdict']} (MAD {extras['benford_mad']:.4f})"]})
        head.to_excel(xw, sheet_name="Summary", index=False)
        summary.to_excel(xw, sheet_name="Summary", index=False, startrow=len(head) + 2)
        exc.to_excel(xw, sheet_name="Exceptions", index=False)
        for rid, g in exc[exc["severity"] == "High"].groupby("rule_id"):
            g.to_excel(xw, sheet_name=f"{rid} {g['rule'].iloc[0]}"[:31].replace("/", "-"), index=False)
        extras["benford"].to_excel(xw, sheet_name="Benford", index=False)
        ai = exc[exc["rule_id"] == "R17"]
        ai.to_excel(xw, sheet_name="AI Anomalies", index=False)

        wb = xw.book
        _format(wb["Exceptions"], exc)
        _format(wb["Benford"], extras["benford"])
        _format(wb["AI Anomalies"], ai)
        for name in wb.sheetnames:
            if name not in ("Summary", "Exceptions", "Benford", "AI Anomalies"):
                _format(wb[name], exc.head(1))
        ws = wb["Summary"]
        ws["A1"].font = ws["B1"].font = Font(bold=True)
        ws.column_dimensions["A"].width = 34
        ws.column_dimensions["B"].width = 42
        for c in ws[len(head) + 3]:
            c.font = Font(bold=True)
        ws.cell(row=len(head) + len(summary) + 6, column=1,
                value="Prepared by: ____________    Reviewed by: ____________   (Audit working paper - ledger scrutiny)")
    return buf.getvalue()
