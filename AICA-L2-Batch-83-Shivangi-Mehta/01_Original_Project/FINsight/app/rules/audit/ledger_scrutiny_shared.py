"""
Shared helpers for the AUD-LS-0xx "Ledger Scrutiny" rule pack.

Origin (disclosed): these 13 checks were adapted from a separate,
user-provided "CA Ledger Scrutiny Assistant" prototype (a standalone
pandas/Flask tool with its own 15-check catalogue) at the user's
explicit request, after review together identified 2 of its 15 checks
as functional duplicates of existing FinSight rules and excluded them:
"Weekend Transaction" (already covered by AUD-JE-002's own
weekend/manual-entry screen) and "High-Value Transaction" (already
covered by every existing materiality-threshold rule in this codebase,
e.g. AUD-WO-011/AUD-CASH-010). The remaining 13 are reimplemented here
from scratch against FinSight's own `MappedRow`/`ExceptionDraft` shapes
— none of the prototype's own code is imported or reused verbatim.

Scope (a disclosed, deliberate decision, not a silent limitation):
these checks read GL, JE, and BANK data only — the three dataset types
that carry a genuine row-level narration/description alongside a
transaction_date and an account_name, which every one of these 13
checks needs to be meaningful. TB rows are period-end balances with no
per-row narration or date, and SALES/PURCHASE/AR/AP have their own
dedicated rule coverage elsewhere — so this pack does not read them, to
avoid a check like "Missing Narration" or "Weekend Transaction"
producing noise against data it was never designed to look at.

Statutory basis: none of these 13 checks is prescribed, in this exact
form or threshold, by any specific SA paragraph — "ledger scrutiny" as
a general test-of-details technique is squarely within the scope of
SA 500 (Audit Evidence) and, for the three pattern/trend-based checks,
SA 520 (Analytical Procedures); each rule module's own docstring says
so explicitly and every finding is worded as a candidate for review,
never a confirmed irregularity — the same "FinSight Analytical Test,
not an SA-prescribed figure" framing already used throughout this
codebase's other rule modules.

Every check in this pack is a single-row finding — even the three that
compute a group/pattern first (Possible Split Transactions, Unusual
Ledger Activity, Unusual Ledger Usage) raise one ExceptionDraft per
individual row that is part of the flagged group, each carrying that
row's own `related_transaction_id`, never one finding "about" the group
as a whole — consistent with how every other single-row-eligible rule
in this codebase behaves (see dataset_service.attach_transaction_ids()
and TRANSACTION_DATASET_TYPES).
"""
from __future__ import annotations

from typing import Any

LEDGER_SCRUTINY_DATASET_TYPES = ("GL", "JE", "BANK")

# Check 2 — Generic/Insufficient Narration.
GENERIC_NARRATION_TERMS = (
    "payment", "expense", "being expense", "general", "miscellaneous",
    "misc", "as per bill", "other", "transfer",
)

# Check 12 — Risk Indicator keywords. FinSight's own disclosed word
# list, not derived from any SA or statute — a hit means "may warrant a
# closer look," never that the transaction is itself improper.
RISK_KEYWORDS = (
    "personal", "penalty", "donation", "cash", "loan", "advance",
    "director", "relative", "gift", "fine", "adjustment", "reversal",
)

# Check 5 — Round-Number Transaction. ₹5,000, in paise — FinSight's own
# default, matching the source prototype's own default exactly.
ROUND_DIVISOR_PAISE = 500_000

# Check 13 — Repeated Party Transactions: flag if a party appears MORE
# than this many times within a single calendar month.
REPEATED_PARTY_MONTHLY_THRESHOLD = 2

# Check 7 — minimum rows in one ledger (account_name) needed before a
# mean/std-dev "normal pattern" is even meaningful.
LEDGER_PATTERN_MIN_ROWS = 3

# Check 14 — minimum months of history needed before a month-over-month
# baseline is meaningful.
UNUSUAL_LEDGER_MIN_MONTHS = 2

# Check 14, "too low" side (Stage 21 addition — see aud_ls_012.py's own
# docstring for the full rationale): with only 2 "other" months to
# compare against, a single unusually-high month drags the average up
# enough that every *other* month then looks artificially "too low" by
# comparison — a false-positive flood, not a real finding. Requiring at
# least 3 "other" months, and comparing against their MEDIAN rather than
# their mean, means one extreme month can no longer single-handedly
# distort the baseline every other month is judged against.
UNUSUAL_LEDGER_DIP_MIN_OTHER_MONTHS = 3
UNUSUAL_LEDGER_DIP_DIVISOR = 2

# Check 15 — a party must have at least this many total transactions,
# across at least this many distinct ledgers, before "used only once
# against one of this party's ledgers" is treated as unusual rather
# than simply this party's normal (small) footprint.
UNUSUAL_USAGE_MIN_PARTY_TXNS = 5
UNUSUAL_USAGE_MIN_LEDGERS = 2


def collect_ledger_rows(dataset: dict[str, list]) -> list:
    """Every row from GL/JE/BANK — see this module's docstring for why
    those three and not TB/SALES/PURCHASE/AR/AP."""
    return [row for dt in LEDGER_SCRUTINY_DATASET_TYPES for row in dataset.get(dt, [])]


def row_amount(values: dict[str, Any]) -> int:
    """A single magnitude for one row's Debit/Credit — the larger/only
    populated side, or their sum in the rare both-populated case (Check
    4 flags that case separately; every other check still needs *some*
    amount figure to reason about for that row)."""
    debit = values.get("debit_amount") or 0
    credit = values.get("credit_amount") or 0
    if debit and credit:
        return debit + credit
    return debit or credit


def row_label(values: dict[str, Any], row) -> str:
    return (
        values.get("account_name") or values.get("party_name")
        or values.get("description") or f"row {row.row_index + 1}"
    )
