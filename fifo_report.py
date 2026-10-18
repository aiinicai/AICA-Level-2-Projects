"""Stored monthly data and period reports for the FIFO tool.

Every time a month is run with "Save ... after Run" ticked, its trades and closing prices are
kept under  <folder of the positions folder>/data/<entity>/ :
    trades/<YYYY-MM>.csv   the trades of that month's file
    runs/<YYYY-MM>.json    valuation date, closing prices and settings used
(<YYYY-MM> is the month of the latest trade in the file; re-running a month replaces it.)

A period report (for example Jan to Mar) is then rebuilt from these stored months, with no
upload: FIFO is run on all stored trades from the start, the position at the end of the month
before the period becomes the opening position (with its closing prices as the starting marks),
and the period itself is calculated exactly as a single month would be. Everything before the
first stored month is assumed to be zero.
"""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from fifo_fixed_income import run_fifo

TRADE_COLS = ["trade_date", "security_id", "side", "quantity", "price", "coupon_rate",
              "settle_date"]


def _root(pos_dir, entity):
    return Path(pos_dir).parent / "data" / entity


def month_label(trades):
    return pd.to_datetime(trades["trade_date"]).max().strftime("%Y-%m")


def save_run(pos_dir, entity, trades, source_name, valuation_date, prices, settings):
    """Store this month's trades, closing prices and settings. Returns the month label."""
    label = month_label(trades)
    root = _root(pos_dir, entity)
    (root / "trades").mkdir(parents=True, exist_ok=True)
    (root / "runs").mkdir(parents=True, exist_ok=True)
    out = trades[TRADE_COLS].copy()
    for c in ("trade_date", "settle_date"):
        out[c] = pd.to_datetime(out[c]).dt.strftime("%Y-%m-%d")
    out.to_csv(root / "trades" / f"{label}.csv", index=False)
    td = pd.to_datetime(trades["trade_date"])
    rec = {"label": label, "valuation_date": pd.Timestamp(valuation_date).strftime("%Y-%m-%d"),
           "source_file": source_name, "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "first_trade": td.min().strftime("%Y-%m-%d"), "last_trade": td.max().strftime("%Y-%m-%d"),
           "n_trades": int(len(trades)), "prices": {k: float(v) for k, v in prices.items()},
           "settings": settings}
    (root / "runs" / f"{label}.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return label


def list_runs(pos_dir, entity):
    """Stored months, oldest first."""
    folder = _root(pos_dir, entity) / "runs"
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in folder.glob("*.json")]
    return sorted(runs, key=lambda r: r["label"])


def overlaps(pos_dir, entity, trades):
    """Labels of OTHER stored months whose trade dates overlap these trades (double-count risk)."""
    label = month_label(trades)
    td = pd.to_datetime(trades["trade_date"])
    lo, hi = td.min().strftime("%Y-%m-%d"), td.max().strftime("%Y-%m-%d")
    return [r["label"] for r in list_runs(pos_dir, entity)
            if r["label"] != label and not (r["last_trade"] < lo or r["first_trade"] > hi)]


def _load_trades(pos_dir, entity, labels):
    root = _root(pos_dir, entity) / "trades"
    frames = [pd.read_csv(root / f"{lb}.csv", parse_dates=["trade_date", "settle_date"])
              for lb in labels]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=TRADE_COLS)


def missing_months(labels, to_label):
    """Calendar months with no stored data between the first stored month and to_label."""
    months = pd.period_range(labels[0], to_label, freq="M").strftime("%Y-%m")
    return [m for m in months if m not in set(labels)]


def save_opening(pos_dir, entity, lots, as_of):
    """Keep an uploaded opening position so period reports start from it."""
    folder = _root(pos_dir, entity) / "openings"
    folder.mkdir(parents=True, exist_ok=True)
    lots.to_csv(folder / f"opening_{pd.Timestamp(as_of):%Y-%m-%d}.csv", index=False)


def load_opening(pos_dir, entity):
    """(lots, as-of date) of the latest uploaded opening position, or (None, None)."""
    files = sorted((_root(pos_dir, entity) / "openings").glob("opening_*.csv"))
    if not files:
        return None, None
    return pd.read_csv(files[-1]), pd.Timestamp(files[-1].stem.split("_")[-1])


def build_report(pos_dir, entity, from_label, to_label, day_count="30e/360",
                 interest_base="face", coupon_dates=None):
    """Return (closed, closing, summary, info) for the period from_label .. to_label."""
    runs = list_runs(pos_dir, entity)
    labels = [r["label"] for r in runs]
    if from_label not in labels or to_label not in labels:
        raise ValueError("Choose two months that have stored data.")
    if from_label > to_label:
        raise ValueError("'From' must not be after 'To'.")
    by = {r["label"]: r for r in runs}
    end = by[to_label]
    pe = pd.Timestamp(end["valuation_date"])
    earlier = [r for r in runs if r["label"] < from_label]
    base, base_date = load_opening(pos_dir, entity)   # uploaded opening position, if any
    if earlier:   # the run just before the period supplies the opening date and starting prices
        ps = pd.Timestamp(earlier[-1]["valuation_date"])
        start_prices = earlier[-1]["prices"]
    elif base is not None:
        ps, start_prices = base_date, {}
    else:
        ps = pd.Timestamp(from_label + "-01") - pd.Timedelta(days=1)
        start_prices = {}
    if base is not None and ps < base_date:
        raise ValueError(f"The report would start before the opening positions date "
                         f"({base_date.date()}). Choose a later From month.")

    trades = _load_trades(pos_dir, entity, [lb for lb in labels if lb <= to_label])
    td = pd.to_datetime(trades["trade_date"])
    if base is not None:     # trades up to the opening date are already inside the opening position
        trades = trades[td > base_date]
        td = pd.to_datetime(trades["trade_date"])
    before, within = trades[td <= ps], trades[(td > ps) & (td <= pe)]
    cols = ["security_id", "quantity", "open_date", "settle_date", "cost_price", "coupon_rate"]
    opening = None
    if base is not None and not earlier:
        opening = base[cols + ["mark_price"]]   # starting marks = the uploaded market prices
    elif base is not None or len(before):
        _, lots, _ = run_fifo(before, ps, start_prices, opening_lots=base, day_count=day_count,
                              interest_base=interest_base)
        if len(lots):
            opening = lots[cols].assign(mark_price=lots["market_price"])
    extra = {"coupon_dates": coupon_dates} if coupon_dates else {}
    closed, closing, summary = run_fifo(within, pe, end["prices"], opening_lots=opening,
                                        period_start=ps, day_count=day_count,
                                        interest_base=interest_base, **extra)
    info = {"period_start": ps, "period_end": pe, "from": from_label, "to": to_label,
            "months": [lb for lb in labels if from_label <= lb <= to_label],
            "gaps": missing_months(labels, to_label), "trades_in_period": int(len(within)),
            "opening_lots": 0 if opening is None else int(len(opening))}
    return closed, closing, summary, info
