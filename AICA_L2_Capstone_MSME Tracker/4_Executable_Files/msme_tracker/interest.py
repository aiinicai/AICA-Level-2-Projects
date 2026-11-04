"""Interest on delayed payments to Micro and Small enterprises – Section 16, MSMED Act, 2006.

Rule implemented
  * rate  = multiplier (default 3) x RBI Bank Rate in force on each day (rate table is editable)
  * start = the day after the due date (due date = acceptance + agreed days up to 45, else 15)
  * compounded with monthly rests: interest accrued in a calendar month is added to the
    interest-bearing base at month end
  * payments reduce the principal only (interest stays payable separately); interest stops when the
    principal is fully paid. A payment on day D still bears interest for D.
  * interest runs to the as-of date for open bills, and to the payment date for bills paid late
Interest under s.16 is not deductible for income tax (s.23 MSMED Act).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# RBI Bank Rate (= MSF rate). Effective dates / values to be verified against RBI notifications – the
# app lets the user edit this table.
DEFAULT_BANK_RATES = pd.DataFrame({
    "Effective From": pd.to_datetime(["2022-05-04", "2022-06-08", "2022-08-05", "2022-09-30", "2022-12-07", "2023-02-08",
                                      "2025-02-07", "2025-04-09", "2025-06-06", "2025-12-05", "2026-10-07"]),
    "Bank Rate %": [4.65, 5.15, 5.65, 6.15, 6.50, 6.75, 6.50, 6.25, 5.75, 5.50, 5.75],
})


def clean_rates(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    ef = d["Effective From"]
    if pd.api.types.is_datetime64_any_dtype(ef):
        d["Effective From"] = pd.to_datetime(ef, errors="coerce")
    else:
        s = ef.astype(str).str.strip()
        iso = s.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")      # saved/ISO dates must not be read day-first
        d["Effective From"] = pd.to_datetime(s.where(iso), errors="coerce", format="mixed", dayfirst=False)
        d["Effective From"] = d["Effective From"].fillna(pd.to_datetime(s.where(~iso), errors="coerce", format="mixed", dayfirst=True))
    d["Bank Rate %"] = pd.to_numeric(d["Bank Rate %"], errors="coerce")
    d = d.dropna().sort_values("Effective From").drop_duplicates("Effective From", keep="last")
    if d.empty:
        raise ValueError("The bank-rate table needs at least one row.")
    return d.reset_index(drop=True)


def bill_interest(principal: float, start, end, pay_events: list[tuple[pd.Timestamp, float]],
                  rates: pd.DataFrame, multiplier: float = 3.0) -> tuple[float, pd.Timestamp | None]:
    """Compound (monthly rests) interest on one bill from `start` to `end` inclusive.

    pay_events: (date, amount) payments that fall inside [start, end]; they reduce principal after that day.
    Returns (interest, last date interest ran to).
    """
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if principal <= 0.005 or start > end:
        return 0.0, None
    eff = list(rates["Effective From"])
    val = list(rates["Bank Rate %"])
    events = sorted(pay_events)
    p, cap, accr, total = float(principal), 0.0, 0.0, 0.0
    cur, last = start, start
    while cur <= end:
        k = max(i for i in range(len(eff)) if eff[i] <= cur) if eff[0] <= cur else 0
        rate = multiplier * val[k] / 100.0
        me = cur + pd.offsets.MonthEnd(0)
        cands = [end, me]
        nxt = [e - pd.Timedelta(days=1) for e in eff if e > cur]
        if nxt:
            cands.append(nxt[0])
        pay_dates = [d for d, _ in events if d >= cur]
        if pay_dates:
            cands.append(pay_dates[0])
        seg_end = min(cands)
        days = (seg_end - cur).days + 1
        i = (p + cap) * rate / 365.0 * days
        accr += i
        total += i
        last = seg_end
        if seg_end == me:
            cap += accr
            accr = 0.0
        for d, a in events:
            if d == seg_end:
                p -= a
        cur = seg_end + pd.Timedelta(days=1)
        if p <= 0.005:
            break
    return round(total, 2), last


def compute_interest(res, as_of, rates: pd.DataFrame, multiplier: float = 3.0) -> pd.DataFrame:
    """Per-bill interest for covered (Micro/Small) bills as at `as_of`. Only bills with interest > 0 are returned."""
    as_of = pd.Timestamp(as_of).normalize()
    L = res.ledger
    A = res.allocations if res.allocations is not None else pd.DataFrame(columns=["idx", "Payment Date", "Amount"])
    by_bill = {i: g for i, g in A.groupby("idx")} if len(A) else {}
    rows = []
    for i, r in L[L["Covered"]].iterrows():
        g = by_bill.get(i)
        paid_before = float(g.loc[g["Payment Date"] <= r["Due Date"], "Amount"].sum()) if g is not None else 0.0
        events = []
        if g is not None:
            events = [(d, float(a)) for d, a in zip(g["Payment Date"], g["Amount"]) if d > r["Due Date"]]
        p0 = float(r["Bill Amount"]) - paid_before
        start = r["Due Date"] + pd.Timedelta(days=1)
        interest, last = bill_interest(p0, start, as_of, events, rates, multiplier)
        if interest > 0:
            rows.append({"Vendor Name": r["Vendor Name"], "Bill No": r["Bill No"], "Branch": r["Branch"],
                         "Accepted On": r["Accepted On"], "Due Date": r["Due Date"], "Bill Amount": r["Bill Amount"],
                         "Principal Delayed": round(p0, 2), "Interest From": start, "Interest To": last,
                         "Days": int((last - start).days + 1), "Still Outstanding": r["Outstanding"],
                         "Status": "Open" if r["Outstanding"] > 0.005 else "Paid late",
                         "Interest Payable": interest})
    cols = ["Vendor Name", "Bill No", "Branch", "Accepted On", "Due Date", "Bill Amount", "Principal Delayed", "Interest From",
            "Interest To", "Days", "Still Outstanding", "Status", "Interest Payable"]
    return pd.DataFrame(rows, columns=cols)


def vendor_summary(detail: pd.DataFrame) -> pd.DataFrame:
    if detail.empty:
        return pd.DataFrame(columns=["Vendor Name", "Bills", "Principal Delayed", "Interest Payable"])
    g = (detail.groupby("Vendor Name", as_index=False)
         .agg(Bills=("Bill No", "count"), **{"Principal Delayed": ("Principal Delayed", "sum"), "Interest Payable": ("Interest Payable", "sum")})
         .sort_values("Interest Payable", ascending=False))
    return g.reset_index(drop=True)


# ---- Optional: look up the current Bank Rate on the RBI website (never automatic; the user confirms) ----
RBI_HOME_URL = "https://www.rbi.org.in/"   # the "Current Rates" box on the home page lists the Bank Rate


def parse_bank_rate(html: str) -> float | None:
    """Pull the 'Bank Rate' % out of the RBI home page text. Returns None if it cannot be found."""
    import html as _html
    import re
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = _html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"\s+", " ", text)
    m = re.search(r"\bBank Rate\s*[:\-]?\s*(\d{1,2}(?:\.\d{1,3})?)\s*%", text, flags=re.I)
    if not m:
        return None
    v = float(m.group(1))
    return v if 0 < v < 25 else None


def fetch_rbi_bank_rate(timeout: float = 10.0) -> float:
    """Fetch the RBI home page and return the published Bank Rate. Raises RuntimeError with a plain message on failure."""
    import urllib.request
    req = urllib.request.Request(RBI_HOME_URL, headers={"User-Agent": "Mozilla/5.0 (MSME Tracker rate check)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Could not reach the RBI website ({type(e).__name__}). Use the link to check it manually.") from e
    v = parse_bank_rate(html)
    if v is None:
        raise RuntimeError("Reached the RBI website but could not find the Bank Rate on the page. Use the link to check it manually.")
    return v
