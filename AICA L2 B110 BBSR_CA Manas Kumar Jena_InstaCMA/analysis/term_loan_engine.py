"""
Term loan engine: monthly repayment schedule (Equal EMI and Equal Principal,
both computed side by side, the selected method feeding the CMA) and the
financial-year summary used by the P&L, Balance Sheet, FORM-III and DSCR.

Rules (identical to the formulas written into the Excel 'Term Loan' sheet):
  * First instalment month = 1st of the month after the date of preparation.
  * Moratorium months: interest is serviced, principal is nil.
  * Interest  = ROUND(opening x rate / 12, 0)
  * Equal Principal: principal = ROUND(loan / instalments, 0)
  * Equal EMI: EMI = ROUND(PMT(rate/12, instalments, loan), 0);
               principal = EMI - interest
  * Last month principal = opening balance, so the loan clears exactly.
"""
import datetime as dt

from analysis.rounding import xround

MAX_MONTHS = 120


def add_months(d, n):
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    return dt.date(y, m, 1)


def fy_end(d):
    return d.year + (1 if d.month >= 4 else 0)


def emi_amount(amount, annual_rate, instalments):
    if instalments <= 0 or amount <= 0:
        return 0
    i = annual_rate / 12.0
    if i == 0:
        return xround(amount / instalments)
    return xround(amount * i / (1 - (1 + i) ** (-instalments)))


def build_schedule(amount, annual_rate, tenure, moratorium, method, first_month):
    """Return list of month rows (up to MAX_MONTHS)."""
    tenure = int(min(max(tenure, 0), MAX_MONTHS))
    moratorium = int(min(max(moratorium, 0), max(tenure - 1, 0)))
    inst = tenure - moratorium
    emi = emi_amount(amount, annual_rate, inst)
    ep_fixed = xround(amount / inst) if inst > 0 else 0
    rows = []
    op_ep = op_emi = float(amount)
    for n in range(1, MAX_MONTHS + 1):
        d = add_months(first_month, n - 1)
        active = n <= tenure and amount > 0
        # Equal principal
        int_ep = xround(op_ep * annual_rate / 12) if active else 0
        if not active or n <= moratorium:
            pr_ep = 0
        elif n == tenure:
            pr_ep = op_ep
        else:
            pr_ep = min(op_ep, ep_fixed)
        # Equal EMI
        int_emi = xround(op_emi * annual_rate / 12) if active else 0
        if not active or n <= moratorium:
            pr_emi = 0
        elif n == tenure:
            pr_emi = op_emi
        else:
            pr_emi = min(op_emi, emi - int_emi)
        row = {
            "n": n, "date": d, "fy_end": fy_end(d),
            "ep_open": op_ep, "ep_interest": int_ep, "ep_principal": pr_ep,
            "ep_instalment": int_ep + pr_ep, "ep_close": op_ep - pr_ep,
            "emi_open": op_emi, "emi_interest": int_emi, "emi_principal": pr_emi,
            "emi_instalment": int_emi + pr_emi, "emi_close": op_emi - pr_emi,
        }
        sel = "emi" if method == "Equal EMI" else "ep"
        row["sel_open"] = row[sel + "_open"]
        row["sel_interest"] = row[sel + "_interest"]
        row["sel_principal"] = row[sel + "_principal"]
        row["sel_instalment"] = row[sel + "_instalment"]
        row["sel_close"] = row[sel + "_close"]
        rows.append(row)
        op_ep -= pr_ep
        op_emi -= pr_emi
    return {"rows": rows, "emi": emi, "instalments": inst, "ep_fixed": ep_fixed,
            "tenure": tenure, "moratorium": moratorium}


def fy_summary(schedule, fy_list, amount):
    """Per FY: instalments, interest, principal, closing balance, next-FY principal."""
    rows = schedule["rows"]
    out = {}
    for fy in fy_list:
        r_in = [r for r in rows if r["fy_end"] == fy]
        interest = sum(r["sel_interest"] for r in r_in)
        principal = sum(r["sel_principal"] for r in r_in)
        instal = sum(r["sel_instalment"] for r in r_in)
        paid_upto = sum(r["sel_principal"] for r in rows if r["fy_end"] <= fy)
        started = any(r["fy_end"] <= fy for r in rows)
        closing = (amount - paid_upto) if started else 0.0
        nxt = sum(r["sel_principal"] for r in rows if r["fy_end"] == fy + 1)
        out[fy] = {"instalments": instal, "interest": interest, "principal": principal,
                   "closing": closing, "next_principal": nxt,
                   "disbursed": amount if (rows and rows[0]["fy_end"] == fy) else 0.0}
    return out


def total_principal(schedule):
    return sum(r["sel_principal"] for r in schedule["rows"])
