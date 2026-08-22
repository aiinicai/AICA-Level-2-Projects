"""
Bank Statement parser.

Two entry points:
  parse(df)                          -- the original fixed template:
                                         Date | Narration | Ledger (Bank) | Contra Ledger | Debit/Credit | Amount
  parse_mapped(df, mapping, bank_ledger) -- column-mapped import: the user picks
                                         which of their real bank export's columns
                                         hold date/narration/amount(s), and a single
                                         bank ledger applies to the whole file
                                         (instead of requiring a "Ledger (Bank)"
                                         column on every row). Falls back on
                                         saved narration rules to prefill the
                                         contra ledger before the usual fuzzy-match
                                         step runs.
"""
from __future__ import annotations

import pandas as pd

from .common import new_row
from .. import bank_rules

REQUIRED_COLS = ["Date", "Narration", "Ledger (Bank)", "Contra Ledger", "Debit/Credit", "Amount"]


def parse(df: pd.DataFrame) -> list[dict]:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Bank statement sheet missing columns: {missing}")

    rows = []
    for _, r in df.iterrows():
        if pd.isna(r["Amount"]) or pd.isna(r["Date"]):
            continue
        dr_cr = str(r["Debit/Credit"]).strip().lower()
        amount = float(r["Amount"])
        bank_ledger = str(r["Ledger (Bank)"]).strip()
        contra_raw = str(r["Contra Ledger"]).strip()

        # Debit/Credit is from the bank statement's perspective:
        # Credit = money IN to bank => Receipt; Debit = money OUT of bank => Payment
        voucher_type = "Receipt" if dr_cr.startswith("cr") else "Payment"

        rows.append(new_row(
            source="Bank",
            date=pd.to_datetime(r["Date"], dayfirst=True).date(),
            voucher_type=voucher_type,
            narration=str(r["Narration"]),
            primary_ledger=bank_ledger,
            contra_raw=contra_raw,
            amount=abs(amount),
        ))
    return rows


def parse_mapped(df: pd.DataFrame, mapping: dict, bank_ledger: str) -> list[dict]:
    """mapping keys: date_col, narration_col (required), plus either
    {debit_col, credit_col} (separate amount columns) or {amount_col} with
    optional dr_cr_col (single amount column, optionally with a separate
    Dr/Cr indicator; if no indicator, negative=Payment/positive=Receipt)."""
    date_col = mapping.get("date_col")
    narration_col = mapping.get("narration_col")
    debit_col = mapping.get("debit_col")
    credit_col = mapping.get("credit_col")
    amount_col = mapping.get("amount_col")
    dr_cr_col = mapping.get("dr_cr_col")
    contra_col = mapping.get("contra_col")

    if not date_col or not narration_col:
        raise ValueError("Column mapping needs at least a Date column and a Narration column.")
    if not (debit_col and credit_col) and not amount_col:
        raise ValueError("Column mapping needs either Debit+Credit columns, or a single Amount column.")
    for col in [date_col, narration_col, debit_col, credit_col, amount_col, dr_cr_col, contra_col]:
        if col and col not in df.columns:
            raise ValueError(f"Mapped column '{col}' not found in the uploaded file.")

    bank_ledger = (bank_ledger or "").strip()
    if not bank_ledger:
        raise ValueError("Pick which bank ledger this statement is for before parsing.")

    def to_float(val) -> float | None:
        """Blank-safe, comma-safe float parsing. PDF-extracted table cells are
        empty strings ('') rather than proper NaN for blank cells, and PDF
        amounts often carry thousands-separator commas (e.g. '1,234.56')."""
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        s = str(val).strip().replace(",", "")
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None

    rows = []
    skipped_bad_dates = 0
    for _, r in df.iterrows():
        if pd.isna(r[date_col]) or not str(r[date_col]).strip():
            continue
        try:
            row_date = pd.to_datetime(r[date_col], dayfirst=True).date()
        except (ValueError, TypeError):
            # PDF table extraction occasionally misaligns a stray cell (e.g. a
            # serial number) into the date column on a header/footer row --
            # skip that one row rather than failing the whole import.
            skipped_bad_dates += 1
            continue
        narration = str(r[narration_col]) if not pd.isna(r.get(narration_col)) else ""

        if debit_col and credit_col:
            debit = to_float(r.get(debit_col)) or 0.0
            credit = to_float(r.get(credit_col)) or 0.0
            if debit and credit:
                continue  # ambiguous row, both populated -- skip rather than guess
            if debit:
                voucher_type, amount = "Payment", debit
            elif credit:
                voucher_type, amount = "Receipt", credit
            else:
                continue
        else:
            raw_amount = to_float(r.get(amount_col))
            if raw_amount is None:
                continue
            if dr_cr_col and not pd.isna(r.get(dr_cr_col)):
                dr_cr = str(r[dr_cr_col]).strip().lower()
                voucher_type = "Receipt" if dr_cr.startswith("cr") else "Payment"
            else:
                # No indicator column: fall back to sign (negative = money out = Payment).
                voucher_type = "Payment" if raw_amount < 0 else "Receipt"
            amount = abs(raw_amount)
            if amount == 0:
                continue

        # A contra/vendor column already in the file wins outright; the
        # narration-rule table only fills in when the file doesn't have one
        # or a specific row's value is blank.
        contra_raw = ""
        if contra_col and not pd.isna(r.get(contra_col)):
            contra_raw = str(r[contra_col]).strip()
        if not contra_raw:
            contra_raw = bank_rules.match(narration) or ""

        rows.append(new_row(
            source="Bank",
            date=row_date,
            voucher_type=voucher_type,
            narration=narration,
            primary_ledger=bank_ledger,
            contra_raw=contra_raw,
            amount=amount,
        ))
    return rows, skipped_bad_dates
