"""Aggregate mapped ledgers into Schedule III line totals and prove they balance.

Presentation sign: liabilities, equity and income are positive when credit; assets and expenses
are positive when debit.
"""
from __future__ import annotations

import pandas as pd

from .mapping import Rulebook

TOTAL_COLS = ["statement", "line", "line_label", "sub", "opening", "closing"]


def line_totals(mapped: pd.DataFrame, rulebook: Rulebook | None = None) -> pd.DataFrame:
    """One row per (line, sub). Adds the two computed items a trial balance does not hold:
    the stock movement inside cost of materials / changes in inventories, and the year's profit
    (shown as surplus in the statement of profit and loss)."""
    rb = rulebook or Rulebook.load()
    side = lambda k: rb.lines.get(k, {}).get("side", "A")  # noqa: E731
    rows = []
    for r in mapped.itertuples(index=False):
        if r.line == "UNMAPPED" or (abs(r.opening) < 0.005 and abs(r.closing) < 0.005):
            continue
        k = -1.0 if side(r.line) == "L" else 1.0
        rows.append((r.statement, r.line, r.sub, k * r.opening, k * r.closing))
        if isinstance(r.inventory_pl_line, str):  # a fall in stock is an expense
            rows.append(("PL", r.inventory_pl_line, f"Opening less closing stock: {r.sub}", 0.0, r.opening - r.closing))
    df = pd.DataFrame(rows, columns=["statement", "line", "sub", "opening", "closing"])

    pl = df[df["statement"] == "PL"]
    income = pl[pl["line"].map(side) == "L"]["closing"].sum()
    expense = pl[pl["line"].map(side) == "A"]["closing"].sum()
    profit = income - expense
    df = pd.concat([df, pd.DataFrame([("BS", "EQ.RS", "Surplus: profit for the year", 0.0, profit)], columns=df.columns)])

    df["line_label"] = df["line"].map(lambda k: rb.lines[k]["label"])
    df["_o"] = df["line"].map(lambda k: rb.lines[k]["order"])
    df = df.groupby(["_o", "statement", "line", "line_label", "sub"], as_index=False)[["opening", "closing"]].sum()
    df.attrs["profit"] = profit
    return df.sort_values(["_o", "sub"]).drop(columns="_o")[TOTAL_COLS].reset_index(drop=True)


def balance_check(totals: pd.DataFrame, rulebook: Rulebook | None = None) -> dict:
    """Total assets vs total equity and liabilities (closing and opening)."""
    rb = rulebook or Rulebook.load()
    bs = totals[totals["statement"] == "BS"].copy()
    bs["side"] = bs["line"].map(lambda k: rb.lines[k]["side"])
    out = {}
    for col in ("closing", "opening"):
        a = bs.loc[bs["side"] == "A", col].sum()
        l = bs.loc[bs["side"] == "L", col].sum()
        out[col] = {"assets": a, "equity_and_liabilities": l, "difference": a - l}
    return out
