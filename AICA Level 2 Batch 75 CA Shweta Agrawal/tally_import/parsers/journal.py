"""
Journal Entry parser.
Columns: Date | Debit Ledger | Credit Ledger | Amount | Narration
Exact Tally ledger names required -- no fuzzy-match, straight to Journal voucher XML.
"""
from __future__ import annotations

import pandas as pd

from .common import new_row

REQUIRED_COLS = ["Date", "Debit Ledger", "Credit Ledger", "Amount", "Narration"]


def parse(df: pd.DataFrame) -> list[dict]:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Journal Entry sheet missing columns: {missing}")

    rows = []
    for _, r in df.iterrows():
        if pd.isna(r["Amount"]) or pd.isna(r["Date"]):
            continue
        rows.append(new_row(
            source="Journal",
            date=pd.to_datetime(r["Date"], dayfirst=True).date(),
            voucher_type="Journal",
            narration=str(r["Narration"]) if not pd.isna(r["Narration"]) else "",
            primary_ledger=str(r["Debit Ledger"]).strip(),
            contra_ledger=str(r["Credit Ledger"]).strip(),   # no fuzzy-match, used as-is
            contra_raw=str(r["Credit Ledger"]).strip(),
            amount=float(r["Amount"]),
        ))
    return rows
