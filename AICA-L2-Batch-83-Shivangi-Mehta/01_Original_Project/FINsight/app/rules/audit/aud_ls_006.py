"""
AUD-LS-006 — Ledger Scrutiny: Unusual Amount vs Ledger Pattern.

Audit area: Ledger Scrutiny. Relevant SA: SA 520.

SA Reference: SA 520 (Analytical Procedures) — comparing a transaction
against the normal pattern already observed on the same ledger account
is a textbook analytical procedure. SA 520 does not prescribe the exact
statistical method or the 2-standard-deviation threshold used below.
FinSight Analytical Test (adapted from a user-provided ledger-scrutiny
prototype — see `ledger_scrutiny_shared.py`): within each account_name
with at least 3 rows, computes the mean and standard deviation of row
amounts, and flags a row whose amount deviates from that account's own
mean by more than 2 standard deviations.

Limitation: a small sample (as low as 3 rows) makes a mean/std-dev
estimate unstable — a single outlier can itself skew the "normal"
baseline it is being compared against; treat a flag as a prompt to
check the underlying transaction, not as statistically robust proof of
an anomaly.
Insufficient data: no validated GL, JE, or BANK data at all for this
engagement, or no account has 3 or more rows to establish a pattern
against.
"""
from __future__ import annotations

import statistics

from app.rules import wording
from app.rules.audit.ledger_scrutiny_shared import LEDGER_PATTERN_MIN_ROWS, collect_ledger_rows, row_amount
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-LS-006"
AUDIT_AREA = "Ledger Scrutiny"
RELATED_SA = "SA 520"
ASSERTIONS = ("ACCURACY", "VALUATION")
TOPIC = "Ledger Scrutiny — Unusual Amount vs Ledger Pattern"

_DEVIATION_MULTIPLE = 2


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    ledger_rows = collect_ledger_rows(dataset)
    if not ledger_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped General Ledger, Journal Entry, or Bank Statement data is "
            "available for this engagement."
        )
        return outcome

    outcome.evaluated_count = len(ledger_rows)

    accounts: dict[str, list] = {}
    for row in ledger_rows:
        account_name = (row.values.get("account_name") or "").strip()
        if not account_name:
            continue
        accounts.setdefault(account_name, []).append(row)

    eligible_accounts = {name: rows for name, rows in accounts.items() if len(rows) >= LEDGER_PATTERN_MIN_ROWS}
    if not eligible_accounts:
        outcome.insufficient_data_reason = (
            f"No ledger account has {LEDGER_PATTERN_MIN_ROWS} or more rows, which FinSight requires before a "
            f"mean/standard-deviation pattern is meaningful."
        )
        return outcome

    for account_name, rows in eligible_accounts.items():
        amounts = [row_amount(row.values) for row in rows]
        mean = statistics.mean(amounts)
        stdev = statistics.stdev(amounts)
        if stdev == 0:
            continue  # every row identical — nothing to deviate from
        for row, amount in zip(rows, amounts):
            deviation = abs(amount - mean)
            if deviation <= _DEVIATION_MULTIPLE * stdev:
                continue
            outcome.exceptions.append(ExceptionDraft(
                label=wording.REVIEW_REQUIRED,
                area=AUDIT_AREA,
                trigger_condition=(
                    f'Entry on "{account_name}" for {paise_to_display(amount)} deviates from that account\'s '
                    f"own average of {paise_to_display(round(mean))} by more than {_DEVIATION_MULTIPLE} standard "
                    f"deviations."
                ),
                explanation=(
                    f'An entry on "{account_name}" for {paise_to_display(amount)} sits well outside the range '
                    f"normally seen on this account across the {len(rows)} rows evaluated (average "
                    f"{paise_to_display(round(mean))}). This is a statistical comparison against this "
                    f"engagement's own data, not against any external or statutory benchmark, and does not "
                    f"itself establish the entry is wrong."
                ),
                suggested_query="Please explain the reason for this entry's unusual amount relative to this ledger's normal pattern.",
                risk_level="MEDIUM",
                data_sources=[str(row.file_id)],
                threshold_used={
                    "identification_method": "FinSight mean/standard-deviation pattern check",
                    "threshold_is_statutory": False,
                    "account_mean_paise": round(mean),
                    "account_stdev_paise": round(stdev),
                    "deviation_multiple": _DEVIATION_MULTIPLE,
                    "rows_in_account": len(rows),
                },
                amount_paise=amount or None,
                related_transaction_id=row.transaction_id,
            ))

    return outcome
