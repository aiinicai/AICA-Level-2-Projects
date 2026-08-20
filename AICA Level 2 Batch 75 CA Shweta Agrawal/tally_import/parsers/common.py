"""
Common staging-row schema produced by every parser. The Streamlit app renders
one big table combining rows from all sources using these columns.
"""
from __future__ import annotations

import uuid

STAGING_COLUMNS = [
    "row_id",       # internal uuid
    "source",       # Bank | Journal | GSTR2B | GSTR1
    "select",       # bool, user toggles for posting
    "status",       # Ready | UnMatched | Duplicate | Error | Posted | Failed
    "date",         # datetime.date
    "voucher_type",  # Payment | Receipt | Contra | Journal | Purchase | Sales
    "narration",
    "reference",
    "primary_ledger",   # bank ledger / debit ledger / purchase-customer party
    "contra_ledger",    # resolved Tally ledger name (editable)
    "contra_raw",        # original unmapped text, for reference
    "expense_ledger",    # GSTR2B only: Purchase/Direct Expense/Indirect Expense/Capital Asset ledger for this row
    "expense_category",  # GSTR2B only: category of expense_ledger -- decides which Tally Voucher Type to post under
    "itc_eligible",      # GSTR2B only: True (default) unless the user marks the row ITC-ineligible in the grid
    "amount",            # signed per source convention before voucher building
    "taxable_value",
    "tax_json",          # json string: [["CGST Ledger", 100.0], ...]
    "gstin",
    "rc_flag",
    "duplicate_hint",    # text describing why flagged duplicate
    "error",             # populated after posting attempt if failed
    "posted_voucher_no",
]


def new_row(**kwargs) -> dict:
    row = {c: None for c in STAGING_COLUMNS}
    row["row_id"] = str(uuid.uuid4())
    row["select"] = True
    row["status"] = "Ready"
    row.update(kwargs)
    return row
