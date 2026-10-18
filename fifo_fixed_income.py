"""FIFO positions, realized/unrealized P&L and 30/360 interest for fixed income trades.

Input trades columns:
    trade_date  : date
    security_id : str
    side        : 'BUY' / 'SELL'
    quantity    : face value (positive)
    price       : clean price per 100 face
    coupon_rate : annual coupon in % (e.g. 5.25)

Assumptions:
    * Opening position is zero for every security.
    * A SELL with no inventory opens a short lot (matched FIFO by later BUYs).
    * Prices are clean; P&L is price P&L only, interest income is shown separately.
    * Interest per matched/closing slice = face * coupon% * days360(open settle, close settle) / 360,
      signed + for long, - for short. Interest runs on settlement dates (optional `settle_date`
      column; trade date if absent); FIFO matching and price P&L use trade dates.
"""
from collections import deque
from datetime import date

import pandas as pd


def days_360(d1: date, d2: date) -> int:
    """30/360 US (Bond Basis) day count."""
    y1, m1, dd1 = d1.year, d1.month, d1.day
    y2, m2, dd2 = d2.year, d2.month, d2.day
    if dd1 == 31:
        dd1 = 30
    if dd2 == 31 and dd1 == 30:
        dd2 = 30
    return 360 * (y2 - y1) + 30 * (m2 - m1) + (dd2 - dd1)


SIDE_MAP = {"B": "BUY", "BUY": "BUY", "BOUGHT": "BUY", "PURCHASE": "BUY", "PURCHASED": "BUY",
            "S": "SELL", "SELL": "SELL", "SOLD": "SELL", "SALE": "SELL"}   # [B] / [S] -> B / S


def days_360_eu(d1: date, d2: date) -> int:
    """30E/360 (European) day count: any 31st becomes the 30th."""
    return (360 * (d2.year - d1.year) + 30 * (d2.month - d1.month)
            + (min(d2.day, 30) - min(d1.day, 30)))


def run_fifo(trades: pd.DataFrame, valuation_date, market_prices: dict,
             opening_lots: pd.DataFrame = None, period_start=None,
             day_count: str = "30/360", interest_base: str = "face", coupon_dates: dict = None):
    """Return (closed_matches, closing_positions, summary) DataFrames.

    FIFO matching and price P&L use the trade date. Interest accrues from SETTLEMENT date to
    SETTLEMENT date (trades need a `settle_date` column; if missing, the trade date is used).
    A position that has not settled by the valuation date accrues no interest (never negative).

    opening_lots: previous month-end closing lots (security_id, quantity [signed], open_date,
        cost_price, coupon_rate, optional settle_date). They are queued ahead of the new trades,
        so FIFO continues across months. Without it, every security starts at zero.
    day_count: "30e/360" (European: a 31st is always the 30th), "30/360" (US bond basis) or
        "actual" (calendar days); the divisor is always 360.
    interest_base: "face" (face value) or "market" (face x price/100: closing price for open lots,
        sale price for sold slices), the way the desk workbook accrues interest.
    coupon_dates: {security_id: [dates a coupon was received]}. `interest_income` is always the
        interest since purchase; `interest_since_coupon` restarts at the latest coupon date that
        falls between the lot's settlement and the end date (accrued interest still outstanding).
    period_start: start of the reporting period. `interest_period` accrues only from
        max(open settlement, period_start); `interest_income` accrues from the original
        open settlement date.
    opening_lots may also carry `mark_price` (the previous month-end closing price). Then
        `unrealized_pl_period` = change in unrealized P&L over the period, measured from that
        price (from the cost price for lots bought in the period); `unrealized_pl` stays the
        cumulative figure against cost. Without `mark_price` the two are equal.
    """
    valuation_date = pd.Timestamp(valuation_date).date()
    ps = pd.Timestamp(period_start).date() if period_start is not None else None

    def days(start, end, floor=None):
        if floor:
            start = max(start, floor)
        if day_count == "actual":
            n = (end - start).days
        elif day_count == "30e/360":
            n = days_360_eu(start, end)
        else:
            n = days_360(start, end)
        return max(n, 0)

    cdates = {s: sorted(pd.Timestamp(x).date() for x in v)
              for s, v in (coupon_dates or {}).items()}

    def accrual_start(sec, settle, end):
        """Latest coupon date on which the lot was held (settle <= date <= end), else settle."""
        got = [c for c in cdates.get(sec, []) if settle <= c <= end]
        return got[-1] if got else settle

    t = trades.copy()
    t["trade_date"] = pd.to_datetime(t["trade_date"])
    t["settle_date"] = pd.to_datetime(t["settle_date"]) if "settle_date" in t else t["trade_date"]
    t["settle_date"] = t["settle_date"].fillna(t["trade_date"])
    raw_side = t["side"].astype(str)
    t["side"] = raw_side.str.upper().str.replace(r"[^A-Z]", "", regex=True).map(SIDE_MAP)
    if t["side"].isna().any():  # never guess: an unknown value must not become a sale
        raise ValueError("Unrecognised side value(s): "
                         + ", ".join(repr(x) for x in sorted(set(raw_side[t["side"].isna()]))))
    t = t.sort_values(["security_id", "trade_date"], kind="stable")
    by_sec = {s: g for s, g in t.groupby("security_id", sort=False)}

    opening = {}
    if opening_lots is not None and len(opening_lots):
        ol = opening_lots.copy()
        ol["open_date"] = pd.to_datetime(ol["open_date"])
        ol["settle_date"] = (pd.to_datetime(ol["settle_date"]) if "settle_date" in ol
                             else ol["open_date"])
        ol["settle_date"] = ol["settle_date"].fillna(ol["open_date"])
        if "mark_price" not in ol:      # older saved positions: no prior month-end price
            ol["mark_price"] = float("nan")
        for s, g in ol.sort_values("open_date", kind="stable").groupby("security_id", sort=False):
            opening[s] = [[r.quantity, r.cost_price, r.open_date.date(), r.coupon_rate,
                           r.settle_date.date(), None if pd.isna(r.mark_price) else float(r.mark_price)]
                          for r in g.itertuples(index=False)]

    closed, open_rows = [], []

    for sec in list(by_sec) + [s for s in opening if s not in by_sec]:
        lots = deque(opening.get(sec, []))  # lot: [signed_qty, price, trade_date, coupon, settle_date]
        g = by_sec.get(sec)
        for r in (g.itertuples(index=False) if g is not None else []):
            qty = r.quantity if r.side == "BUY" else -r.quantity
            d, px, cpn, sd = r.trade_date.date(), r.price, r.coupon_rate, r.settle_date.date()
            # Close against opposite-signed lots in FIFO order
            while qty != 0 and lots and (lots[0][0] > 0) != (qty > 0):
                lot = lots[0]
                m = min(abs(lot[0]), abs(qty))
                sign = 1 if lot[0] > 0 else -1          # +1 closing a long, -1 closing a short
                pl = sign * m * (px - lot[1]) / 100
                k = sign * m * (px / 100 if interest_base == "market" else 1) * lot[3] / 100 / 360
                closed.append(dict(
                    security_id=sec, direction="LONG" if sign > 0 else "SHORT",
                    quantity=m, open_date=lot[2], open_settle=lot[4], open_price=lot[1],
                    close_date=d, close_settle=sd, close_price=px, coupon_rate=lot[3],
                    days=days(lot[4], sd),
                    realized_pl=pl, interest_income=k * days(lot[4], sd),
                    interest_period=k * days(lot[4], sd, ps),
                    interest_since_coupon=k * days(accrual_start(sec, lot[4], sd), sd)))
                lot[0] -= sign * m
                qty += sign * m
                if lot[0] == 0:
                    lots.popleft()
            if qty != 0:
                lots.append([qty, px, d, cpn, sd, None])

        mkt = market_prices.get(sec)
        for q, px, d, cpn, sd, mark in lots:
            sign = 1 if q > 0 else -1
            eff_mkt = mkt if mkt is not None else px
            unreal = sign * abs(q) * (eff_mkt - px) / 100
            # change in unrealized P&L over the period: measured from last month-end's price for
            # lots carried in, from the cost price for lots bought in the period
            unreal_p = sign * abs(q) * (eff_mkt - (px if mark is None else mark)) / 100
            base = eff_mkt / 100 if interest_base == "market" else 1
            k = sign * abs(q) * base * cpn / 100 / 360
            open_rows.append(dict(
                security_id=sec, direction="LONG" if sign > 0 else "SHORT",
                quantity=q, open_date=d, settle_date=sd, cost_price=px, market_price=eff_mkt,
                market_value=q * eff_mkt / 100,   # signed: a short is a negative value
                coupon_rate=cpn, days=days(sd, valuation_date),
                unrealized_pl=unreal, unrealized_pl_period=unreal_p,
                interest_income=k * days(sd, valuation_date),
                interest_period=k * days(sd, valuation_date, ps),
                interest_since_coupon=k * days(accrual_start(sec, sd, valuation_date),
                                               valuation_date)))

    closed_df = pd.DataFrame(closed)
    open_df = pd.DataFrame(open_rows)

    parts = []
    if not closed_df.empty:
        parts.append(closed_df.groupby("security_id")[
            ["realized_pl", "interest_income", "interest_period",
             "interest_since_coupon"]].sum().add_suffix("_sold"))
    if not open_df.empty:
        parts.append(open_df.groupby("security_id").agg(
            closing_quantity=("quantity", "sum"),
            market_value=("market_value", "sum"),
            unrealized_pl=("unrealized_pl", "sum"),
            unrealized_pl_period=("unrealized_pl_period", "sum"),
            interest_income_closing=("interest_income", "sum"),
            interest_period_closing=("interest_period", "sum"),
            interest_since_coupon_closing=("interest_since_coupon", "sum")))
    summary = pd.concat(parts, axis=1).fillna(0).reset_index() if parts else pd.DataFrame()
    return closed_df, open_df, summary


if __name__ == "__main__":
    trades = pd.DataFrame([
        ("2024-01-15", "BOND_A", "BUY", 100000, 99.50, 5.0),
        ("2024-03-31", "BOND_A", "BUY", 50000, 100.25, 5.0),
        ("2024-06-30", "BOND_A", "SELL", 120000, 101.00, 5.0),
        ("2024-02-10", "BOND_B", "SELL", 30000, 98.00, 4.0),   # no opening position -> short
        ("2024-05-31", "BOND_B", "BUY", 10000, 97.00, 4.0),
    ], columns=["trade_date", "security_id", "side", "quantity", "price", "coupon_rate"])

    closed, closing, summary = run_fifo(
        trades, valuation_date="2024-12-31",
        market_prices={"BOND_A": 100.80, "BOND_B": 99.00})

    pd.set_option("display.width", 200, "display.max_columns", 30)
    print("Closed matches (realized P&L + interest):\n", closed, "\n")
    print("Closing positions (unrealized P&L + interest):\n", closing, "\n")
    print("Summary:\n", summary)

    # To use your own file:
    # trades = pd.read_csv("trades.csv"); run_fifo(trades, "2024-12-31", {...})




