"""
AUD-JE-001 — Manual Journal Entries Near Year-End.

Audit area: Journal Entry Testing. Relevant SA: SA 240 (The Auditor's
Responsibilities Relating to Fraud in an Audit of Financial Statements),
SA 330 (The Auditor's Responses to Assessed Risks). Assertions:
Occurrence, Cut-off, Accuracy.

SA Reference (authoritative — ICAI Standard on Auditing): SA 240, SA 330.
This citation identifies the audit standard whose guidance motivates
this check (SA 240's discussion of manual journal entries as a
fraud-risk area). It does NOT mean SA 240 or SA 330 prescribes this
rule's specific proximity window or amount threshold — neither
standard specifies a day-count or a rupee figure.
FinSight Analytical Test (created by FinSight, not prescribed by any
SA): flag a manual JE dated within a FinSight-configurable window
before financial year end (currently 5 days — `PROXIMITY_WINDOW_DAYS`),
at or above the applicable materiality threshold (the engagement's own
Overall Materiality if set, else a FinSight default fallback of
₹1,00,000 — see `resolve_materiality_threshold_paise()`).

This is a RISK INDICATOR, never an accounting exception (Module
boundary, Section 1.1) — a manual entry near year-end above the
threshold is not itself wrong; it is a pattern that warrants audit
attention per SA 240's guidance on manual journal entries as a
fraud-risk area.

What data is required: `JE` rows with `is_manual_entry`, `transaction_date`,
and `debit_amount`/`credit_amount`.
What can actually be established: whether a manual entry was posted
within a configurable proximity window of financial year end, at or
above a materiality-derived amount.
What cannot be established: intent, approval status, or whether the
entry is actually improper — this is a candidate for further procedures,
never a finding of wrongdoing.
Insufficient data: no validated JE data at all, or the engagement's
`financial_year` cannot be parsed into FY bounds.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.rules import wording
from app.rules.accounting.shared_detectors import resolve_materiality_threshold_paise, is_flag_true
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.rules.period_utils import financial_year_bounds
from app.utils.currency import paise_to_display

RULE_ID = "AUD-JE-001"
AUDIT_AREA = "Journal Entry Testing"
RELATED_SA = "SA 240, SA 330"
ASSERTIONS = ("OCCURRENCE", "CUT_OFF", "ACCURACY")
TOPIC = "Manual Journal Entries Near Year-End"

# FinSight-configurable analytical thresholds, never SA requirements.
PROXIMITY_WINDOW_DAYS = 5


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    je_rows = dataset.get("JE", [])
    if not je_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Journal Entry data is available for this engagement."
        )
        return outcome

    bounds = financial_year_bounds(engagement.financial_year)
    if bounds is None:
        outcome.insufficient_data_reason = (
            f"The engagement's financial year (\"{engagement.financial_year}\") could not be parsed into "
            f"calendar bounds — proximity to year-end cannot be assessed."
        )
        return outcome
    _fy_start, fy_end = bounds
    window_start = fy_end - timedelta(days=PROXIMITY_WINDOW_DAYS - 1)

    threshold_paise, threshold_source = resolve_materiality_threshold_paise(engagement)

    for row in je_rows:
        v = row.values
        if not is_flag_true(v.get("is_manual_entry")):
            continue
        raw_date = v.get("transaction_date")
        if not raw_date:
            outcome.partial_insufficient_data_notes.append(
                f"Manual JE row (file {row.file_id}, row {row.row_index + 1}): no Transaction Date value — "
                f"proximity to year-end could not be assessed for this entry."
            )
            continue
        try:
            txn_date = date.fromisoformat(raw_date)
        except ValueError:
            outcome.partial_insufficient_data_notes.append(
                f"Manual JE row (file {row.file_id}, row {row.row_index + 1}): Transaction Date could not be parsed."
            )
            continue

        outcome.evaluated_count += 1
        if not (window_start <= txn_date <= fy_end):
            continue

        amount = max(v.get("debit_amount") or 0, v.get("credit_amount") or 0)
        if amount < threshold_paise:
            continue

        description = v.get("description") or v.get("account_name") or f"entry (row {row.row_index + 1})"
        outcome.exceptions.append(ExceptionDraft(
            label=wording.AUDIT_ATTENTION_REQUIRED,
            area=AUDIT_AREA,
            trigger_condition=(
                f"Manual journal entry of {paise_to_display(amount)} posted on {txn_date.isoformat()}, within "
                f"{PROXIMITY_WINDOW_DAYS} day(s) of financial year end ({fy_end.isoformat()}); amount is at or "
                f"above the applicable threshold ({paise_to_display(threshold_paise)}, from {threshold_source})."
            ),
            explanation=(
                f'Manual entry "{description}" was posted on {txn_date.isoformat()}, within the FinSight-'
                f"configurable {PROXIMITY_WINDOW_DAYS}-day proximity window before financial year end, for an "
                f"amount ({paise_to_display(amount)}) at or above the applicable threshold. Manual entries posted "
                f"close to period end are a recognized fraud-risk pattern under SA 240 and warrant further audit "
                f"attention — this does not itself mean anything is wrong with the entry; only that it is a "
                f"candidate for the procedures below."
            ),
            suggested_query=(
                "Please provide supporting documentation and approval evidence for this manual journal entry "
                "posted close to year-end."
            ),
            risk_level="HIGH",
            data_sources=[str(row.file_id)],
            threshold_used={
                "proximity_window_days": PROXIMITY_WINDOW_DAYS,
                "amount_threshold_paise": threshold_paise,
                "amount_threshold_source": threshold_source,
                "threshold_is_sa_requirement": False,
            },
            amount_paise=amount,
            related_transaction_id=row.transaction_id,
        ))

    return outcome
