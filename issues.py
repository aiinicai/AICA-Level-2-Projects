"""
Filing issues & risk analysis engine.

Turns the figures the app has already fetched (GSTR-1, GSTR-3B, GSTR-2B, GSTR-9,
filing status, aggregate turnover, and - when available - e-way-bill totals) into
a single ranked list of issues a reviewer should act on, each with a severity,
the amount involved, the section it relates to and a recommended action.

Pure pandas, no network - fully testable offline.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

TOL = 1.0            # rupee tolerance for "equal"
PCT = 0.05           # 5% relative tolerance for soft flags
SEV_ORDER = {"High": 0, "Medium": 1, "Low": 2, "Info": 3}


def _n(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


class _Collector:
    def __init__(self):
        self.rows = []

    def add(self, severity, area, period, issue, detail, amount=0.0, ref="", action=""):
        self.rows.append({"Severity": severity, "Area": area, "Period": period, "Issue": issue,
                          "Detail": detail, "Amount (Rs)": round(_n(amount), 2), "Reference": ref,
                          "Action": action})

    def frame(self):
        df = pd.DataFrame(self.rows, columns=["Severity", "Area", "Period", "Issue", "Detail",
                                              "Amount (Rs)", "Reference", "Action"])
        if not df.empty:
            df["_o"] = df["Severity"].map(SEV_ORDER).fillna(9)
            df = df.sort_values(["_o", "Area", "Period"]).drop(columns="_o").reset_index(drop=True)
        return df


def _months_in(df, col="Period"):
    return [] if df is None or df.empty else list(df[col])


def analyse_filing(fy, status_df=None, g3_sum=None, g1_tot=None, g2_tot=None, recon=None,
            g9_json=None, aato=None, ewb_month=None, today=None):
    """Returns (issues_df, summary_dict)."""
    today = today or date.today()
    c = _Collector()

    # ---------------------------------------------------------------- 1. filing discipline
    if status_df is not None and not status_df.empty:
        for _, r in status_df.iterrows():
            st = r.get("Status", "")
            per = r.get("Period", "")
            rtn = r.get("Return", "")
            if st == "Not filed - overdue":
                c.add("High", "Filing", per, f"{rtn} not filed", f"Overdue by {int(r.get('Days late', 0))} days.",
                      r.get("Est. late fee", 0), "Sec 47 / 46",
                      f"File {rtn} for {per} immediately; late fee and interest accrue daily.")
            elif st == "Filed late":
                c.add("Medium", "Filing", per, f"{rtn} filed late",
                      f"Filed {int(r.get('Days late', 0))} day(s) after the due date.",
                      r.get("Est. late fee", 0), "Sec 47",
                      "Ensure late fee was discharged; review cause of delay.")

    # ---------------------------------------------------------------- 2. GSTR-1 vs GSTR-3B (outward)
    if recon is not None and not recon.empty:
        for _, r in recon.iterrows():
            per = r.get("Period", "")
            dtax = _n(r.get("Diff tax (GSTR-1 - 3B)"))
            dval = _n(r.get("Diff taxable (GSTR-1 - 3B)"))
            if abs(dtax) > TOL:
                sev = "High" if abs(dtax) > max(1000, 0.01 * _n(r.get("GSTR-1 tax"))) else "Medium"
                if dtax > 0:
                    c.add(sev, "Outward (1 vs 3B)", per, "GSTR-1 tax higher than 3B",
                          f"GSTR-1 shows Rs {_n(r.get('GSTR-1 tax')):,.0f} output tax vs 3B Rs "
                          f"{_n(r.get('Output tax 3.1(a)')):,.0f}. Under-paid in 3B.", abs(dtax),
                          "Sec 37 / 39", "Pay the short tax with interest in the next 3B; amend if needed.")
                else:
                    c.add(sev, "Outward (1 vs 3B)", per, "3B tax higher than GSTR-1",
                          f"3B output tax exceeds GSTR-1 by Rs {abs(dtax):,.0f}. GSTR-1 may be under-reported.",
                          abs(dtax), "Sec 37", "Reconcile; amend GSTR-1 to match the liability discharged.")
            elif abs(dval) > max(100, PCT * _n(r.get("GSTR-1 taxable value"))):
                c.add("Low", "Outward (1 vs 3B)", per, "Taxable value mismatch (tax equal)",
                      f"Taxable value differs by Rs {abs(dval):,.0f} though tax matches (rate/class mix).",
                      abs(dval), "Sec 37", "Check zero-rated / exempt classification between 1 and 3B.")
        # cumulative
        if {"GSTR-1 tax", "Output tax 3.1(a)"} <= set(recon):
            cum = _n(recon["GSTR-1 tax"].sum()) - _n(recon["Output tax 3.1(a)"].sum())
            if abs(cum) > TOL:
                c.add("Medium" if abs(cum) > 1000 else "Low", "Outward (1 vs 3B)", f"FY{fy}",
                      "Cumulative GSTR-1 vs 3B output-tax gap",
                      f"Net difference for the year: Rs {cum:,.0f}.", abs(cum), "Annual recon",
                      "Resolve before GSTR-9; this is a common Table 9 difference.")

    # ---------------------------------------------------------------- 3. GSTR-2B vs GSTR-3B (ITC)
    if recon is not None and not recon.empty and {"ITC available 4A", "2B ITC (excl. othersup)"} <= set(recon):
        for _, r in recon.iterrows():
            per = r.get("Period", "")
            excess = _n(r.get("Excess ITC in 3B over 2B"))
            if excess > TOL:
                sev = "High" if excess > max(1000, 0.05 * _n(r.get("2B ITC (excl. othersup)"))) else "Medium"
                c.add(sev, "ITC (2B vs 3B)", per, "ITC claimed in 3B exceeds 2B",
                      f"3B ITC Rs {_n(r.get('ITC available 4A')):,.0f} vs 2B Rs "
                      f"{_n(r.get('2B ITC (excl. othersup)')):,.0f} (excess Rs {excess:,.0f}).",
                      excess, "Sec 16(2)(aa) / Rule 36(4)",
                      "Reverse / justify the excess ITC; ineligible unless the invoice appears in 2B.")
            elif excess < -TOL:
                c.add("Info", "ITC (2B vs 3B)", per, "ITC available in 2B not fully claimed",
                      f"2B ITC exceeds 3B by Rs {abs(excess):,.0f} - possible unclaimed credit.",
                      abs(excess), "Sec 16(4)",
                      "Claim eligible ITC before the September-following deadline.")
        cum = _n(recon["ITC available 4A"].sum()) - _n(recon["2B ITC (excl. othersup)"].sum())
        if cum > TOL:
            c.add("Medium" if cum > 1000 else "Low", "ITC (2B vs 3B)", f"FY{fy}",
                  "Cumulative excess ITC over 2B", f"Net excess ITC claimed for the year: Rs {cum:,.0f}.",
                  cum, "Sec 16(2)(aa)", "Reconcile before GSTR-9 Table 8; keep supplier-wise working.")

    # ---------------------------------------------------------------- 4. interest exposure (late 3B)
    if status_df is not None and not status_df.empty and g3_sum is not None and not g3_sum.empty:
        cash = {r["Period"]: _n(r.get("Tax paid in cash")) for _, r in g3_sum.iterrows()}
        for _, r in status_df[status_df["Return"] == "GSTR-3B"].iterrows():
            per, days = r.get("Period"), int(r.get("Days late", 0))
            if r.get("Status") == "Filed late" and days > 0 and cash.get(per, 0) > 0:
                interest = cash[per] * 0.18 * days / 365.0
                if interest >= 1:
                    c.add("Medium" if interest > 1000 else "Low", "Interest", per,
                          "Interest u/s 50 on late 3B",
                          f"~Rs {interest:,.0f} interest @18% on cash tax Rs {cash[per]:,.0f} for {days} days (estimate).",
                          interest, "Sec 50(1)",
                          "Confirm interest was paid in that 3B; shortfall attracts recovery.")

    # ---------------------------------------------------------------- 5. nil / anomaly checks
    if g3_sum is not None and not g3_sum.empty:
        for _, r in g3_sum.iterrows():
            per = r["Period"]
            out_tax = _n(r.get("Output tax 3.1(a)"))
            itc = _n(r.get("ITC available 4A"))
            if r.get("Nil return") == "Yes" and itc > TOL:
                c.add("Low", "Anomaly", per, "Nil 3B but ITC available",
                      f"3B marked nil yet Rs {itc:,.0f} ITC was available in 2B.", itc, "Sec 16",
                      "Confirm no outward supplies; claim eligible ITC if genuine.")
            rcm_tax = _n(r.get("RCM tax 3.1(d)"))
            if rcm_tax > TOL:
                c.add("Info", "RCM", per, "RCM liability declared",
                      f"Reverse-charge tax Rs {rcm_tax:,.0f} in 3.1(d).", rcm_tax, "Sec 9(3)/9(4)",
                      "Ensure matching RCM ITC in 4A(3) and that it was paid in cash.")

    # ---------------------------------------------------------------- 6. turnover sanity
    if aato and g1_tot is not None and not g1_tot.empty:
        g1_turn = _n(g1_tot["Taxable value"].sum()) if "Taxable value" in g1_tot else 0
        if g1_turn and abs(g1_turn - aato) > max(100000, 0.1 * aato):
            c.add("Low", "Turnover", f"FY{fy}", "GSTR-1 turnover differs from AATO",
                  f"GSTR-1 taxable value Rs {g1_turn:,.0f} vs portal aggregate turnover Rs {aato:,.0f}.",
                  abs(g1_turn - aato), "AATO", "Expected where exports/exempt/other GSTINs exist; verify.")

    # ---------------------------------------------------------------- 7. GSTR-9 reconciliation
    if g9_json:
        d = g9_json.get("data", g9_json) if isinstance(g9_json, dict) else {}
        t9 = d.get("table9", {})
        for head, lbl in (("iamt", "IGST"), ("camt", "CGST"), ("samt", "SGST")):
            cell = t9.get(head, {})
            diff = _n(cell.get("diff_tax_paid"))
            if abs(diff) > TOL:
                c.add("Medium", "Annual (GSTR-9)", f"FY{fy}", f"GSTR-9 Table 9 {lbl} difference",
                      f"Payable vs paid differs by Rs {diff:,.0f} ({lbl}).", abs(diff), "GSTR-9 Table 9",
                      "Pay any balance via DRC-03 before/with the annual return.")

    # ---------------------------------------------------------------- 8. e-way bill vs GSTR-1
    if ewb_month is not None and not ewb_month.empty:
        g1m = {}
        if g1_tot is not None and not g1_tot.empty:
            g1m = {r["Period"]: _n(r.get("Taxable value")) for _, r in g1_tot.iterrows()}
        for _, r in ewb_month.iterrows():
            per = r.get("Period", "")
            ewb_val = _n(r.get("EWB taxable value", r.get("EWB value")))
            g1v = g1m.get(per, 0.0)
            diff = ewb_val - g1v
            if ewb_val > 0 and g1v > 0 and abs(diff) > max(10000, PCT * ewb_val):
                if diff > 0:
                    c.add("High", "E-way bill vs GSTR-1", per, "E-way bills exceed GSTR-1 supplies",
                          f"EWB value Rs {ewb_val:,.0f} vs GSTR-1 Rs {g1v:,.0f} (Rs {diff:,.0f} more EWB).",
                          diff, "Rule 138 / Sec 37",
                          "Possible outward supplies not reported in GSTR-1 - verify and report.")
                else:
                    c.add("Medium", "E-way bill vs GSTR-1", per, "GSTR-1 supplies exceed e-way bills",
                          f"GSTR-1 Rs {g1v:,.0f} vs EWB Rs {ewb_val:,.0f}.", abs(diff), "Rule 138",
                          "Expected for services / sub-threshold / exempt; confirm EWB was raised where required.")
            elif ewb_val > 0 and g1v == 0:
                c.add("High", "E-way bill vs GSTR-1", per, "E-way bills but no GSTR-1 supplies",
                      f"EWB value Rs {ewb_val:,.0f} with nil GSTR-1 for the month.", ewb_val, "Sec 37",
                      "Outward supplies likely unreported - investigate immediately.")

    df = c.frame()
    summ = {"total": int(len(df)),
            "high": int((df["Severity"] == "High").sum()) if not df.empty else 0,
            "medium": int((df["Severity"] == "Medium").sum()) if not df.empty else 0,
            "low": int((df["Severity"] == "Low").sum()) if not df.empty else 0,
            "exposure": float(df.loc[df["Severity"].isin(["High", "Medium"]), "Amount (Rs)"].sum()) if not df.empty else 0.0}
    return df, summ
