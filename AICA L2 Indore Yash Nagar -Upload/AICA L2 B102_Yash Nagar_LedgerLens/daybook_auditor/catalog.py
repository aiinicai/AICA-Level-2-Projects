"""Every test the Day Book audit runs, in plain words, with how many findings each raised. A test that found nothing is
listed too, so the reviewer can see it ran."""
from __future__ import annotations

import pandas as pd

from . import narration as N
from . import rules as R

_THRESH = "; ".join(f"Rs {limit:,.0f}" for limit, _ in N.THRESHOLDS)

# (family, name, rule name, what it does)
BASE = [
    ("999 and amount tests", "999 verification", N.R_NEAR,
     "Flags payments, receipts, journals and purchases whose amount ends in 999 (Rs 9,999 or more), or sits within the set "
     f"percentage just below a statutory or approval limit ({_THRESH}). Such amounts can be set to stay under a limit or split from a larger payment."),
    ("999 and amount tests", "Repeated identical amounts", N.R_REPEAT, "The same amount to the same party three or more times within a few days."),
    ("999 and amount tests", "Benford first-digit test", N.R_BENFORD, "Compares the first digits of amounts with the pattern that natural data follows."),
    ("999 and amount tests", "Round-sum entries", R.R_ROUND, "Large entries in round thousands."),
    ("Accounting rules", "Cash payment above the limit", R.R_CASH_PAY, "Cash paid to one person in a day above Rs 10,000 (Sec 40A(3))."),
    ("Accounting rules", "Cash payment just below the limit", R.R_CASH_NEAR, "Cash payments kept just under the limit."),
    ("Accounting rules", "Cash receipt above the limit", R.R_CASH_RCPT, "Cash received above Rs 2,00,000 (Sec 269ST)."),
    ("Accounting rules", "Negative cash balance", R.R_NEG_CASH, "The cash book going below zero on any day."),
    ("Accounting rules", "Possible duplicate vouchers", R.R_DUP, "Two vouchers with the same party, amount and date."),
    ("Accounting rules", "Debit equal to credit", R.R_IMBAL, "Every voucher must balance."),
    ("Accounting rules", "Voucher number gaps", R.R_GAP, "Missing numbers in a voucher series, allowing for restarts of the series."),
    ("Accounting rules", "Date outside the financial year", R.R_PERIOD, "Vouchers dated before or after the year."),
    ("Accounting rules", "Dates hidden in the export", R.R_UNDATED, "Tally's Educational mode replaces most dates; date-based tests step back."),
    ("Accounting rules", "Large entry on a Sunday", R.R_SUNDAY, "Large entries on a day the business is normally closed."),
    ("Accounting rules", "Missing narration", R.R_NARR, "Material entries with no narration."),
    ("Accounting rules", "Suspense or miscellaneous ledger", R.R_SUSP, "Postings to suspense, miscellaneous or similar ledgers."),
    ("Accounting rules", "Possible TDS non-deduction", R.R_TDS, "Payments to service or contract ledgers with no TDS in the voucher."),
    ("Accounting rules", "GST ledger inconsistency", R.R_GST, "GST ledgers that do not agree with the taxable value."),
]


def catalog_frame(findings: pd.DataFrame) -> pd.DataFrame:
    """One row per test: family, test, what it checks, findings raised, vouchers touched."""
    rows = list(BASE) + [("Narration themes", t.label, N.R_NARR_PREFIX + t.label, "Narration wording. " + t.reference[:150]) for t in N.THEMES]
    f = findings if len(findings) else pd.DataFrame({"rule": [], "voucher_id": []})
    out = []
    for fam, name, rule, what in rows:
        hit = f[f["rule"] == rule]
        out.append({"Family": fam, "Test": name, "What it checks": what, "Findings": int(len(hit)),
                    "Vouchers": int(hit["voucher_id"].nunique()), "Result": "Raised findings" if len(hit) else "Ran: nothing found"})
    return pd.DataFrame(out)
