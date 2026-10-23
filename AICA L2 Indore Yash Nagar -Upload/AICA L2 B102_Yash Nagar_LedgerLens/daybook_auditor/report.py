"""Excel report: Summary, Findings and the normalised Day Book."""
from __future__ import annotations

import io

import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

FILL = {"High": "F8CBAD", "Medium": "FFE699", "Low": "DDEBF7"}


def ai_sheet(findings: pd.DataFrame, ai_sent: int = 0) -> pd.DataFrame:
    """The AI's remarks beside what the rules found on the same voucher, for reading and sorting in Excel."""
    ai = findings[findings["source"] == "AI"] if len(findings) else findings
    if not ai_sent:
        return pd.DataFrame({"AI analysis": ["The AI review was not run for this file. Run it on the Day Book page and download again."]})
    if ai.empty:
        return pd.DataFrame({"AI analysis": [f"The AI reviewed {ai_sent} voucher(s) and found nothing to add."]})
    rules_on = findings[findings["source"] != "AI"].groupby("voucher_id")["rule"].agg(lambda x: "; ".join(sorted(set(x))))
    out = ai.assign(rules=ai["voucher_id"].map(rules_on).fillna(""))
    out["Also flagged by rules"] = out["rules"].map(lambda x: "Yes" if x else "No: raised only by the AI")
    out = out.rename(columns={"severity": "Severity", "rule": "AI category", "date": "Date", "vch_type": "Voucher type", "vch_no": "Voucher no.",
                              "amount": "Amount (Rs)", "detail": "AI observation", "reference": "AI suggestion", "rules": "Rule findings on the same voucher"})
    return out[["Severity", "AI category", "Date", "Voucher type", "Voucher no.", "Amount (Rs)", "AI observation", "AI suggestion",
                "Also flagged by rules", "Rule findings on the same voucher"]].reset_index(drop=True)


def build_excel(findings: pd.DataFrame, daybook: pd.DataFrame, meta: dict, ai_sent: int = 0) -> bytes:
    f = findings.copy()
    f.insert(0, "No.", range(1, len(f) + 1))
    f = f.rename(columns={"vch_type": "Voucher type", "vch_no": "Voucher no.", "voucher_id": "Voucher ID",
                          "detail": "Observation", "reference": "Reference / suggestion"})
    f.columns = [c.capitalize() if c.islower() else c for c in f.columns]

    summary = (findings.groupby(["severity", "rule"]).size().rename("Count").reset_index()
               .rename(columns={"severity": "Severity", "rule": "Check"}) if len(findings)
               else pd.DataFrame(columns=["Severity", "Check", "Count"]))
    summary["_r"] = summary["Severity"].map({"High": 0, "Medium": 1, "Low": 2})
    summary = summary.sort_values(["_r", "Count"], ascending=[True, False]).drop(columns="_r")

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl", datetime_format="DD-MMM-YYYY") as xw:
        summary.to_excel(xw, sheet_name="Summary", index=False)
        f.to_excel(xw, sheet_name="Findings", index=False)
        ai_sheet(findings, ai_sent).to_excel(xw, sheet_name="AI analysis", index=False)
        daybook.to_excel(xw, sheet_name="Day Book", index=False)
        for ws in xw.book.worksheets:
            for c in ws[1]:
                c.font = Font(bold=True)
            ws.freeze_panes = "A2"
            for i, col in enumerate(ws.columns, start=1):
                width = max((len(str(c.value)) for c in col[:200] if c.value is not None), default=8)
                ws.column_dimensions[get_column_letter(i)].width = min(width + 2, 70)
        for row in xw.book["AI analysis"].iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        for col in ("G", "H"):
            xw.book["AI analysis"].column_dimensions[col].width = 70
        ws = xw.book["Findings"]
        sev_col = [c.value for c in ws[1]].index("Severity") + 1
        for row in ws.iter_rows(min_row=2):
            colour = FILL.get(row[sev_col - 1].value)
            if colour:
                row[sev_col - 1].fill = PatternFill("solid", fgColor=colour)
    return buf.getvalue()
