"""Command-line entry point: run every module and write the deliverables.

    python -m chs_audit.run_audit --data ../data/raw --out ../output [--as-of 2026-07-15] [--ai]
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

from . import audit_checks as ac
from . import compliance as cp
from . import tax as tx
from .ai_writer import AIWriter
from .config import FY_END, FY_START, SOCIETY
from .dashboard import build_dashboard
from .findings import number_findings
from .loaders import load
from .report_excel import write_workbook


def monthly_series(d) -> pd.DataFrame:
    b = d.bills.copy()
    b["month"] = pd.to_datetime(b.bill_date).dt.strftime("%b-%y")
    billed = b.groupby("month", sort=False).bill_total.sum()
    r = d.receipts[(d.receipts.receipt_date >= FY_START) & (d.receipts.receipt_date <= FY_END)].copy()
    r["month"] = pd.to_datetime(r.receipt_date).dt.strftime("%b-%y")
    collected = r.groupby("month").amount.sum()
    return pd.DataFrame({"month": billed.index, "billed": billed.values, "collected": [float(collected.get(m, 0.0)) for m in billed.index]})


def run_pipeline(data_dir: Path, as_of: date) -> dict:
    """Run every rule module once and return all schedules, findings and context."""
    d = load(Path(data_dir))
    # the society's identity comes from the data file when present (uploaded or mock-up societies)
    for attr, item in (("name", "Society name"), ("reg_no", "Registration no."), ("address", "Society address")):
        v = d.master(item)
        if isinstance(v, str) and v.strip():
            setattr(SOCIETY, attr, v.strip())
    ledger, interest_df, defaulters, f1 = ac.member_ledger(d)
    gst_sched, gst_summary, f2 = ac.gst_check(d)
    fund_sched, f3 = ac.fund_compliance(d)
    recon, recon_detail, f4 = ac.bank_reconciliation(d)
    anomalies, benford, f5 = ac.expense_anomalies(d)
    tds_sched, f6 = ac.tds_check(d)
    calendar, f7 = cp.compliance_calendar(d, as_of)
    meetings, resolutions, actions, f8 = cp.minutes_analysis(d, as_of)
    tax_comp, tax_summary, f9 = tx.compute_tax(d)
    findings = number_findings(f1 + f2 + f3 + f4 + f5 + f6 + f7 + f8 + f9)
    fdf = pd.DataFrame([f.as_dict() for f in findings])[["id", "severity", "module", "area", "observation", "reference", "recommendation", "amount", "evidence"]]
    sf_gap = d.fund("Sinking Fund - opening") + d.fund("Sinking Fund - collected") - d.earmarked_fd()
    sheets = {
        "Member_Ledger": ledger, "Defaulters": defaulters, "Interest_Recompute": interest_df,
        "GST_Check": gst_sched, "GST_Summary": gst_summary, "Fund_Compliance": fund_sched,
        "Bank_Reconciliation": recon, "Bank_Exceptions": recon_detail, "Expense_Anomalies": anomalies, "Benford": benford,
        "TDS_Check": tds_sched, "Compliance_Calendar": calendar, "Minutes_Meetings": meetings, "Minutes_Resolutions": resolutions,
        "Minutes_Actions": actions, "Tax_Computation": tax_comp,
    }
    return {"data": d, "findings": findings, "findings_df": fdf, "sheets": sheets, "tax_summary": tax_summary,
            "monthly": monthly_series(d), "sf_gap": sf_gap, "as_of": as_of, "defaulters": defaulters}


def main(argv=None):
    ap = argparse.ArgumentParser(description="AI-assisted statutory audit assistant for co-operative housing societies")
    ap.add_argument("--data", default="data/raw", type=Path)
    ap.add_argument("--out", default="output", type=Path)
    ap.add_argument("--as-of", default="2026-07-15", help="audit fieldwork date (YYYY-MM-DD)")
    ap.add_argument("--ai", action="store_true", help="draft narratives with Claude (needs Anthropic credentials)")
    args = ap.parse_args(argv)
    as_of = date.fromisoformat(args.as_of)
    args.out.mkdir(parents=True, exist_ok=True)

    r = run_pipeline(args.data, as_of)
    d, findings, fdf, sheets, tax_summary = r["data"], r["findings"], r["findings_df"], r["sheets"], r["tax_summary"]
    print(f"Loaded {len(d.members)} members, {len(d.bills)} bills, {len(d.receipts)} receipts, {len(d.expenses)} vouchers, {len(d.minutes)} minutes files")
    print(f"{len(findings)} observations: " + ", ".join(f"{k} {v}" for k, v in fdf.severity.value_counts().items()))

    ai = AIWriter(enabled=args.ai)
    print("AI drafting:", "Claude " + ai.model if ai.enabled else "offline templates")
    drafts = {
        "Draft_Audit_Observations": ai.audit_observations(findings),
        "Draft_Management_Letter": ai.management_letter(findings, as_of),
        "Draft_Governance_Summary": ai.minutes_summary(sheets["Minutes_Meetings"], sheets["Minutes_Actions"]),
        "Draft_Tax_Note": ai.tax_note(tax_summary),
    }
    letters = {row.flat_no: ai.reminder_letter(row, as_of) for row in r["defaulters"].itertuples()}
    drafts["Draft_Reminder_Letters"] = "\n\n".join(f"----- Flat {k} -----\n{v}" for k, v in letters.items())

    wb_path = args.out / "CHS_Audit_Workbook_FY2025-26.xlsx"
    write_workbook(wb_path, sheets, drafts, fdf)
    ctx = {"findings": fdf, "ledger": sheets["Member_Ledger"], "calendar": sheets["Compliance_Calendar"], "gst_summary": sheets["GST_Summary"],
           "benford": sheets["Benford"], "monthly": r["monthly"], "tax_summary": tax_summary, "as_of": as_of, "sf_gap": r["sf_gap"]}
    (args.out / "dashboard.html").write_text(build_dashboard(ctx), encoding="utf-8")
    for name, text in drafts.items():
        (args.out / f"{name}.txt").write_text(text, encoding="utf-8")
    ai.write_log(args.out / "ai_prompt_log.md")
    fdf.to_csv(args.out / "findings.csv", index=False)
    ledger = sheets["Member_Ledger"]
    (args.out / "summary.json").write_text(json.dumps({
        "as_of": as_of.isoformat(), "members": len(d.members), "bills": len(d.bills), "findings": len(findings),
        "by_severity": fdf.severity.value_counts().to_dict(), "quantified_exposure": float(fdf.amount.sum()),
        "member_dues": float(ledger.closing_balance.clip(lower=0).sum()), "defaulters_over_3m": int(len(r["defaulters"])),
        "gst_error_amount": float(sheets["GST_Summary"].amount.abs().sum()), "sinking_fund_gap": r["sf_gap"], "tax": tax_summary,
        "ai_enabled": ai.enabled,
    }, indent=2, default=str))
    print(f"Written: {wb_path.name}, dashboard.html, {len(drafts)} draft documents, ai_prompt_log.md, findings.csv, summary.json -> {args.out}")


if __name__ == "__main__":
    main()
