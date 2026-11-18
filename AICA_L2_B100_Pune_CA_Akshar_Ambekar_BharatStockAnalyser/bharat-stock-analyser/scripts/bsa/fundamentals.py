"""Annual and quarterly financial tables, ratios and historical valuation multiples.

Per-share figures are computed on the CURRENT share count (PAT / shares outstanding today).
Yahoo price history is split- and bonus-adjusted, so this keeps historical P/E and P/B
consistent across bonus issues and splits. The cost is a small error where shares were
issued for cash. This is stated in the report methodology.

Definitions used throughout:
    EBITDA      Operating EBITDA, excluding other income and unusual items (Indian broker
                convention). Yahoo's own EBITDA equals PBT + interest + depreciation and so
                includes other income; it is kept as `ebitda_reported`.
    PAT         Profit attributable to owners (after minority interest).
    PAT_norm    PAT less one-off items after tax. One-offs are the source's unusual items plus
                any spike in other income (see `normalise`). This is an estimate and is
                labelled as such in the report.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from .fmt import cagr, clamp, fy_label, median, num, q_label, safe_div

ROWS = {
    "revenue": ["Total Revenue", "Operating Revenue"],
    "cost_of_revenue": ["Cost Of Revenue", "Reconciled Cost Of Revenue"],
    "ebitda_reported": ["EBITDA", "Normalized EBITDA"],
    "ebit": ["EBIT", "Operating Income"],
    "depreciation": ["Reconciled Depreciation", "Depreciation And Amortization In Income Statement"],
    "interest": ["Interest Expense", "Interest Expense Non Operating"],
    "other_income": ["Other Non Operating Income Expenses"],
    "unusual": ["Total Unusual Items", "Total Unusual Items Excluding Goodwill"],
    "pbt": ["Pretax Income"],
    "tax": ["Tax Provision"],
    "pat": ["Net Income Common Stockholders", "Net Income",
            "Net Income From Continuing Operation Net Minority Interest"],
    "pat_total": ["Net Income Including Noncontrolling Interests"],
    "minority": ["Minority Interests"],
    "nii": ["Net Interest Income"],
    "equity": ["Stockholders Equity", "Common Stock Equity"],
    "total_debt": ["Total Debt"],
    "cash": ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "Cash Financial"],
    "total_assets": ["Total Assets"],
    "current_liabilities": ["Current Liabilities"],
    "inventory": ["Inventory"],
    "receivables": ["Accounts Receivable", "Receivables"],
    "payables": ["Accounts Payable", "Payables"],
    "cfo": ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"],
    "capex": ["Capital Expenditure"],
    "fcf": ["Free Cash Flow"],
    "dividends": ["Cash Dividends Paid", "Common Stock Dividend Paid"],
    "cfi": ["Investing Cash Flow", "Cash Flow From Continuing Investing Activities"],
    "cff": ["Financing Cash Flow", "Cash Flow From Continuing Financing Activities"],
}

INCOME_KEYS = ("revenue", "cost_of_revenue", "ebitda_reported", "ebit", "depreciation", "interest", "other_income",
               "unusual", "pbt", "tax", "pat", "pat_total", "minority", "nii")
QUARTER_KEYS = tuple(k for k in INCOME_KEYS if k != "cost_of_revenue")

# Other income counts as a spike (one-off) when it exceeds this multiple of the median of the
# other periods in the table AND the excess is at least this share of profit before tax.
SPIKE_MULTIPLE = 3.0
SPIKE_SHARE_OF_PBT = 0.10

def _value(df: pd.DataFrame, key: str, col, fx: float) -> float | None:
    if df is None or df.empty or col is None:
        return None
    for name in ROWS[key]:
        if name in df.index:
            v = num(df.at[name, col])
            if v is not None:
                return v * fx
    return None


def _match_col(df: pd.DataFrame, when: pd.Timestamp):
    """Column of df whose date is within 45 days of `when`."""
    if df is None or df.empty:
        return None
    for c in df.columns:
        try:
            if abs((pd.Timestamp(c) - when).days) <= 45:
                return c
        except Exception:
            continue
    return None


def _periods(income: pd.DataFrame, keep: int) -> list[pd.Timestamp]:
    if income is None or income.empty:
        return []
    cols = []
    for c in income.columns:
        if _value(income, "revenue", c, 1.0) is not None or _value(income, "pat", c, 1.0) is not None:
            cols.append(pd.Timestamp(c))
    return sorted(cols)[-keep:]


def is_financial(info: dict, income: pd.DataFrame) -> bool:
    if (info.get("sector") or "") == "Financial Services":
        return True
    if income is None or income.empty:
        return False
    has_ebitda = any(n in income.index for n in ROWS["ebitda_reported"])
    return not has_ebitda and "Net Interest Income" in income.index


def annual_table(raw, shares: float | None, price_close: pd.Series) -> list[dict]:
    fx = raw.fx_to_inr
    rows: list[dict] = []
    for when in _periods(raw.income, keep=5):
        ci = _match_col(raw.income, when)
        cb = _match_col(raw.balance, when)
        cc = _match_col(raw.cashflow, when)
        r = {"label": fy_label(when), "date": when.strftime("%Y-%m-%d")}
        for k in INCOME_KEYS:
            r[k] = _value(raw.income, k, ci, fx)
        for k in ("equity", "total_debt", "cash", "total_assets", "current_liabilities", "inventory",
                  "receivables", "payables"):
            r[k] = _value(raw.balance, k, cb, fx)
        for k in ("cfo", "capex", "fcf", "dividends", "cfi", "cff"):
            r[k] = _value(raw.cashflow, k, cc, fx)
        if r["fcf"] is None and r["cfo"] is not None and r["capex"] is not None:
            r["fcf"] = r["cfo"] + r["capex"]
        # FY-end price (split-adjusted close, not dividend-adjusted).
        r["price_fy_end"] = num(price_close.asof(when)) if not price_close.empty and when >= price_close.index[0] \
            else None
        rows.append(r)
    normalise(rows)

    prev = None
    for r in rows:
        r["revenue_growth"] = (safe_div(r["revenue"], prev["revenue"]) - 1) * 100 \
            if prev and safe_div(r["revenue"], prev["revenue"]) is not None and prev["revenue"] > 0 else None
        # Growth is not meaningful when either year is a loss.
        r["pat_growth"] = (r["pat"] / prev["pat"] - 1) * 100 \
            if prev and r["pat"] is not None and r["pat"] > 0 and prev["pat"] and prev["pat"] > 0 else None
        r["ebitda_margin"] = _pct(r["ebitda"], r["revenue"])
        r["pat_margin"] = _pct(r["pat"], r["revenue"])
        avg_eq = _avg(r["equity"], prev["equity"] if prev else None)
        r["roe"] = _pct(r["pat"], avg_eq) if avg_eq and avg_eq > 0 else None
        cap_emp = (r["total_assets"] - r["current_liabilities"]) \
            if r["total_assets"] is not None and r["current_liabilities"] is not None else None
        r["capital_employed"] = cap_emp
        r["roce"] = _pct(r["ebit"], cap_emp) if cap_emp and cap_emp > 0 else None
        avg_assets = _avg(r["total_assets"], prev["total_assets"] if prev else None)
        r["roa"] = _pct(r["pat"], avg_assets) if avg_assets else None
        r["net_debt"] = (r["total_debt"] or 0) - (r["cash"] or 0) if r["total_debt"] is not None else None
        r["net_debt_equity"] = safe_div(r["net_debt"], r["equity"]) if r["equity"] and r["equity"] > 0 else None
        r["interest_cover"] = safe_div(r["ebit"], abs(r["interest"])) if r["interest"] else None
        r["cfo_to_pat"] = safe_div(r["cfo"], r["pat"]) if r["pat"] and r["pat"] > 0 else None
        r["payout"] = _pct(-(r["dividends"] or 0), r["pat"]) if r["dividends"] is not None and r["pat"] and \
            r["pat"] > 0 else None
        r["eps_adj"] = safe_div(r["pat"], shares)
        r["eps_norm"] = safe_div(r["pat_norm"], shares)
        r["bvps_adj"] = safe_div(r["equity"], shares)
        r["dps_adj"] = safe_div(-(r["dividends"] or 0), shares) if r["dividends"] is not None else None
        # Historical P/E on earnings excluding one-offs, so a one-off year does not distort the median.
        r["pe"] = safe_div(r["price_fy_end"], r["eps_norm"]) if r["eps_norm"] and r["eps_norm"] > 0 else None
        r["pb"] = safe_div(r["price_fy_end"], r["bvps_adj"]) if r["bvps_adj"] and r["bvps_adj"] > 0 else None
        cost_base = r["cost_of_revenue"] or r["revenue"]
        r["inventory_days"] = _days(r["inventory"], cost_base)
        r["receivable_days"] = _days(r["receivables"], r["revenue"])
        r["payable_days"] = _days(r["payables"], cost_base)
        r["asset_turnover"] = safe_div(r["revenue"], avg_assets)
        r["leverage"] = safe_div(avg_assets, avg_eq)
        prev = r
    return rows


def normalise(rows: list[dict]) -> None:
    """Add operating EBITDA, one-off items and PAT excluding one-offs to each period, in place.

    One-off (pre-tax) = the source's unusual items plus any spike in other income. A spike is
    other income above SPIKE_MULTIPLE x the median of the other periods, where the excess is at
    least SPIKE_SHARE_OF_PBT of profit before tax; the excess over the median is the one-off.
    If both are flagged in one period the larger is used, to avoid counting one item twice.
    The after-tax effect uses the period's effective tax rate, bounded to 0% to 35%.
    """
    for i, r in enumerate(rows):
        oi, unusual, pbt, tax = (num(r.get(k)) for k in ("other_income", "unusual", "pbt", "tax"))
        rep = num(r.get("ebitda_reported"))
        r["ebitda"] = rep - (oi or 0.0) - (unusual or 0.0) if rep is not None else None

        excess = 0.0
        others = [num(x.get("other_income")) for j, x in enumerate(rows)
                  if j != i and num(x.get("other_income")) is not None]
        if oi is not None and oi > 0 and len(others) >= 2 and pbt and pbt > 0:
            base = max(median(others), 0.0)
            if oi > SPIKE_MULTIPLE * base and (oi - base) >= SPIKE_SHARE_OF_PBT * pbt:
                excess = oi - base
        u = unusual or 0.0
        one_off = max(u, excess) if u > 0 and excess > 0 else u + excess
        notes = []
        if excess:
            notes.append("other income spike")
        if u:
            notes.append("unusual items")
        rate = clamp(tax / pbt, 0.0, 0.35) if pbt and pbt > 0 and tax is not None else 0.25
        r["one_off"] = one_off
        r["one_off_after_tax"] = one_off * (1 - rate)
        r["one_off_source"] = " and ".join(notes) or None
        pat = num(r.get("pat"))
        r["pat_norm"] = pat - r["one_off_after_tax"] if pat is not None else None
        if r.get("pat_total") is None and pbt is not None and tax is not None:
            r["pat_total"] = pbt - tax


def quarterly_table(raw, shares: float | None) -> list[dict]:
    fx = raw.fx_to_inr
    sources = getattr(raw, "q_sources", None) or {}
    out = []
    for when in _periods(raw.q_income, keep=5):
        c = _match_col(raw.q_income, when)
        r = {"label": q_label(when), "date": when.strftime("%Y-%m-%d"),
             "source": sources.get(when.strftime("%Y-%m-%d"), "Yahoo Finance")}
        for k in QUARTER_KEYS:
            r[k] = _value(raw.q_income, k, c, fx)
        out.append(r)
    normalise(out)
    for r in out:
        r["ebitda_margin"] = _pct(r["ebitda"], r["revenue"])
        r["pat_margin"] = _pct(r["pat"], r["revenue"])
        r["eps_adj"] = safe_div(r["pat"], shares)
        r["eps_norm"] = safe_div(r["pat_norm"], shares)
    return out


def _find_quarter(quarters: list[dict], when: pd.Timestamp, tol_days: int = 20) -> dict | None:
    for q in quarters:
        if abs((pd.Timestamp(q["date"]) - when).days) <= tol_days:
            return q
    return None


def quarter_changes(quarters: list[dict]) -> dict:
    """QoQ and YoY changes, matched by period end date, not by position.

    The source sometimes skips a quarter. Matching by date means a missing quarter gives
    'not available' instead of a comparison with the wrong period.
    """
    keys = ("revenue", "ebitda", "pat", "pat_norm", "nii", "eps_adj")
    res = {"qoq": {}, "yoy": {}, "latest": None, "prev": None, "year_ago": None, "missing": []}
    if not quarters:
        return res
    last = quarters[-1]
    res["latest"] = last["label"]
    end = pd.Timestamp(last["date"])

    def chg(a, b):
        a, b = num(a), num(b)
        if a is None or b is None or b <= 0:
            return None
        return (a / b - 1) * 100

    p = _find_quarter(quarters, end - pd.DateOffset(months=3))
    y = _find_quarter(quarters, end - pd.DateOffset(months=12))
    if p:
        res["prev"] = p["label"]
        res["qoq"] = {k: chg(last.get(k), p.get(k)) for k in keys}
    if y:
        res["year_ago"] = y["label"]
        res["yoy"] = {k: chg(last.get(k), y.get(k)) for k in keys}
    first = pd.Timestamp(quarters[0]["date"])
    k = 1
    while end - pd.DateOffset(months=3 * k) > first + pd.Timedelta(days=20):
        when = end - pd.DateOffset(months=3 * k)
        if not _find_quarter(quarters, when):
            res["missing"].append(q_label(when))
        k += 1
    return res


def _consecutive(quarters: list[dict]) -> bool:
    ds = [pd.Timestamp(q["date"]) for q in quarters]
    return all(80 <= (b - a).days <= 100 for a, b in zip(ds, ds[1:]))


def trailing_eps(annual: list[dict], quarters: list[dict], shares: float | None) -> dict:
    """Trailing EPS excluding one-offs: last four consecutive quarters, else the latest full year."""
    q4 = quarters[-4:]
    if len(q4) == 4 and _consecutive(q4) and all(q.get("pat_norm") is not None for q in q4):
        pat = sum(q["pat"] for q in q4 if q.get("pat") is not None)
        norm = sum(q["pat_norm"] for q in q4)
        return {"ttm_pat": pat, "ttm_pat_norm": norm, "eps": safe_div(norm, shares),
                "basis": f"four quarters to {q4[-1]['label']}, excluding one-offs"}
    last = annual[-1] if annual else {}
    note = "quarterly data has a gap" if len(quarters) >= 4 else "fewer than four quarters available"
    if last.get("eps_norm") is not None:
        return {"ttm_pat": None, "ttm_pat_norm": None, "eps": last["eps_norm"],
                "basis": f"{last['label']} full year, excluding one-offs ({note})"}
    return {"ttm_pat": None, "ttm_pat_norm": None, "eps": None, "basis": None}


def _quarter_ends_after(d: date, today: date) -> list[date]:
    """Quarter-end dates strictly after d and on or before today."""
    out = []
    y, m = d.year, d.month
    while True:
        m += 3
        if m > 12:
            m -= 12
            y += 1
        last_day = 31 if m in (3, 12) else 30
        e = date(y, m, last_day)
        if e > today:
            return out
        out.append(e)


def freshness(quarters: list[dict], today: date, annual: list[dict] | None = None) -> dict:
    """Which quarterly results should exist by `today` but are not in the data.

    The latest period covered is the later of the last quarter and the last fiscal year end,
    because annual accounts include the quarters within that year.
    SEBI LODR Regulation 33: quarterly results within 45 days of quarter end; results for the
    March quarter (with the annual accounts) within 60 days.
    """
    periods = [(pd.Timestamp(q["date"]).date(), q["label"]) for q in quarters[-1:]] + \
              [(pd.Timestamp(r["date"]).date(), f"{r['label']} (annual)") for r in (annual or [])[-1:]]
    if not periods:
        return {"latest_quarter": None, "missing": [], "check_required": False, "overdue": False}
    latest, latest_label = max(periods)
    missing = []
    for e in _quarter_ends_after(latest, today):
        due = e + pd.Timedelta(days=60 if e.month == 3 else 45)
        missing.append({"quarter": q_label(pd.Timestamp(e)), "period_end": e.strftime("%d-%b-%Y"),
                        "due_by": due.strftime("%d-%b-%Y"), "overdue": today > due})
    return {"latest_quarter": latest_label, "missing": missing, "check_required": bool(missing),
            "overdue": any(x["overdue"] for x in missing)}


def growth_summary(annual: list[dict]) -> dict:
    """Up to 3-year CAGR for revenue, EBITDA, PAT and EPS (profit and EPS exclude one-offs)."""
    if len(annual) < 2:
        return {"years": 0}
    n = min(3, len(annual) - 1)
    first, last = annual[-1 - n], annual[-1]
    return {
        "years": n,
        "from": first["label"],
        "to": last["label"],
        "revenue": cagr(first["revenue"], last["revenue"], n),
        "ebitda": cagr(first["ebitda"], last["ebitda"], n),
        "pat": cagr(first["pat_norm"], last["pat_norm"], n),
        "eps": cagr(first["eps_norm"], last["eps_norm"], n),
        "book_value": cagr(first["equity"], last["equity"], n),
    }


def build(raw, financial: bool) -> dict:
    info = raw.info
    shares = num(info.get("sharesOutstanding")) or num(info.get("impliedSharesOutstanding"))
    if not shares and not raw.balance.empty and "Ordinary Shares Number" in raw.balance.index:
        shares = num(raw.balance.loc["Ordinary Shares Number"].dropna().iloc[0])
    close = raw.ohlc["Close"].dropna()

    annual = annual_table(raw, shares, close)
    quarters = quarterly_table(raw, shares)
    te = trailing_eps(annual, quarters, shares)
    pes = [r["pe"] for r in annual if r["pe"] and 0 < r["pe"] < 150]
    pbs = [r["pb"] for r in annual if r["pb"] and 0 < r["pb"] < 40]
    return {
        "is_financial": financial,
        "shares": shares,
        "annual": annual,
        "quarters": quarters,
        "quarter_changes": quarter_changes(quarters),
        "growth": growth_summary(annual),
        "ttm_pat": te["ttm_pat"],
        "ttm_pat_norm": te["ttm_pat_norm"],
        "trailing_eps": te["eps"],
        "trailing_basis": te["basis"],
        "pe_history_median": median(pes),
        "pb_history_median": median(pbs),
        "pe_history_points": len(pes),
        "pb_history_points": len(pbs),
    }


def _pct(a, b) -> float | None:
    v = safe_div(a, b)
    return None if v is None else v * 100


def _avg(a, b) -> float | None:
    a, b = num(a), num(b)
    if a is None:
        return None
    return a if b is None else (a + b) / 2


def _days(bal, flow) -> float | None:
    v = safe_div(bal, flow)
    return None if v is None or v < 0 else v * 365
