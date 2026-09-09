"""
AUD-WO-011 — Large Write-offs.

Audit area: Large Write-offs. Relevant SA: SA 240, SA 500. Assertions:
Valuation, Existence, Rights & Obligations.

SA Reference (authoritative — ICAI Standard on Auditing): SA 240,
SA 500. This citation identifies write-offs as a recognized fraud-risk/
evidence area under these standards; it does NOT mean either standard
prescribes the write-off keyword list or the materiality threshold
applied below — both are FinSight's own (or the engagement's own
configured Overall Materiality).
FinSight Analytical Test (created by FinSight, not prescribed by any
SA): flag a General Ledger/Journal Entry/Trial Balance row whose
account name or description matches a FinSight write-off keyword list
(written off/write off/write-off/bad debt/waiver/waived off), at or
above the applicable materiality threshold (the engagement's own
Overall Materiality if set, else a FinSight default fallback of
₹1,00,000).

What data is required: `GL`/`JE`/`TB` rows with `account_name` and/or
`description`, and an amount (`debit_amount`/`credit_amount`).
What can actually be established: whether a row's account name or
description contains a write-off/bad-debt/waiver keyword, and its
amount is at or above the applicable materiality threshold.
What cannot be established: whether the write-off was properly
approved or whether adequate recovery efforts preceded it — only
inspection of approval records and correspondence can establish that;
this rule is a keyword-and-amount screen, not a conclusion.
Insufficient data: no validated GL/JE/TB data at all for this
engagement.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.accounting.shared_detectors import resolve_materiality_threshold_paise
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-WO-011"
AUDIT_AREA = "Large Write-offs"
RELATED_SA = "SA 240, SA 500"
ASSERTIONS = ("VALUATION", "EXISTENCE", "RIGHTS_OBLIGATIONS")
TOPIC = "Large Write-offs"

_WRITE_OFF_KEYWORDS = ("written off", "write off", "write-off", "bad debt", "waiver", "waived off")
_LEDGER_TYPES = ("GL", "JE", "TB")


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    ledger_rows = [row for dt in _LEDGER_TYPES for row in dataset.get(dt, [])]
    if not ledger_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped General Ledger, Journal Entry, or Trial Balance data is available "
            "for this engagement."
        )
        return outcome

    threshold_paise, threshold_source = resolve_materiality_threshold_paise(engagement)

    for row in ledger_rows:
        v = row.values
        account_name = (v.get("account_name") or "").strip()
        description = (v.get("description") or "").strip()
        haystack = f"{account_name} {description}".strip().lower()
        if not haystack or not any(k in haystack for k in _WRITE_OFF_KEYWORDS):
            continue

        outcome.evaluated_count += 1
        amount = max(v.get("debit_amount") or 0, v.get("credit_amount") or 0)
        if amount < threshold_paise:
            continue

        label_text = account_name or description or f"row {row.row_index + 1}"
        outcome.exceptions.append(ExceptionDraft(
            label=wording.AUDIT_ATTENTION_REQUIRED,
            area=AUDIT_AREA,
            trigger_condition=(
                f'Entry on "{label_text}" for {paise_to_display(amount)} matches a write-off/bad-debt/waiver '
                f"keyword and is at or above the applicable materiality threshold."
            ),
            explanation=(
                f'An entry on "{label_text}" for {paise_to_display(amount)} matches a write-off/bad-debt/waiver '
                f"keyword in its account name or description, and meets or exceeds {threshold_source}, used here "
                f"as a FinSight analytical threshold. This flags the entry for review of its approval and "
                f"rationale — it does not itself establish that the write-off was improper or inadequately "
                f"supported."
            ),
            suggested_query=(
                "Please provide the approval record and details of recovery efforts undertaken prior to this "
                "write-off."
            ),
            risk_level="HIGH",
            data_sources=[str(row.file_id)],
            threshold_used={
                "materiality_threshold_paise": threshold_paise,
                "materiality_threshold_source": threshold_source,
                "threshold_is_sa_requirement": False,
                "matched_keywords": _WRITE_OFF_KEYWORDS,
            },
            amount_paise=amount,
            related_transaction_id=row.transaction_id,
        ))

    return outcome
