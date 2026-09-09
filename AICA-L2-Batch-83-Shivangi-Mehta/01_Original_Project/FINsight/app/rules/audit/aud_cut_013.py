"""
AUD-CUT-013 — Revenue Cut-off.

Audit area: Revenue Cut-off. Relevant SA: SA 240, SA 315, SA 500.
Assertions: Cut-off, Occurrence.

SA Reference (authoritative — ICAI Standard on Auditing): SA 240,
SA 315, SA 500. This citation identifies revenue cut-off as a
recognized audit risk area under these standards; it does NOT mean any
of them prescribes the specific proximity window used below — that
window is entirely FinSight's own.
FinSight Analytical Test (created by FinSight, not prescribed by any
SA): flag a SALES transaction dated within a FinSight-configurable
window either side of financial year end (currently 7 days —
`PROXIMITY_WINDOW_DAYS`). No amount threshold is applied.

Reclassified from Accounting to Audit back in the v0.1/v0.2 blueprint
review (it tests timing/period-matching, not framework treatment — the
module-boundary test in Section 1.1) and now implemented here for the
first time.

What data is required: `SALES` rows with `transaction_date`.
What can actually be established: whether a revenue transaction is
recorded within a configurable proximity window of financial year end
(before or after, if the uploaded data extends that far).
What cannot be established: whether the transaction is actually
recorded in the wrong period — only dispatch/delivery or
service-completion evidence, inspected by a reviewer, can establish
that.
Insufficient data: no validated SALES data, or the engagement's
financial year cannot be parsed.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.rules import wording
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.rules.period_utils import financial_year_bounds
from app.utils.currency import paise_to_display

RULE_ID = "AUD-CUT-013"
AUDIT_AREA = "Revenue Cut-off"
RELATED_SA = "SA 240, SA 315, SA 500"
ASSERTIONS = ("CUT_OFF", "OCCURRENCE")
TOPIC = "Revenue Cut-off"

PROXIMITY_WINDOW_DAYS = 7  # FinSight-configurable, not an SA requirement.


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    sales_rows = dataset.get("SALES", [])
    if not sales_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Sales data is available for this engagement."
        )
        return outcome

    bounds = financial_year_bounds(engagement.financial_year)
    if bounds is None:
        outcome.insufficient_data_reason = (
            f"The engagement's financial year (\"{engagement.financial_year}\") could not be parsed into "
            f"calendar bounds."
        )
        return outcome
    _fy_start, fy_end = bounds
    window_start = fy_end - timedelta(days=PROXIMITY_WINDOW_DAYS - 1)
    window_end = fy_end + timedelta(days=PROXIMITY_WINDOW_DAYS)

    for row in sales_rows:
        v = row.values
        raw_date = v.get("transaction_date")
        if not raw_date:
            outcome.partial_insufficient_data_notes.append(
                f"Sales row (file {row.file_id}, row {row.row_index + 1}): no Transaction Date value — cut-off "
                f"proximity could not be assessed."
            )
            continue
        try:
            txn_date = date.fromisoformat(raw_date)
        except ValueError:
            outcome.partial_insufficient_data_notes.append(
                f"Sales row (file {row.file_id}, row {row.row_index + 1}): Transaction Date could not be parsed."
            )
            continue

        outcome.evaluated_count += 1
        if not (window_start <= txn_date <= window_end):
            continue

        amount = max(v.get("debit_amount") or 0, v.get("credit_amount") or 0)
        side = "before" if txn_date <= fy_end else "after"
        party = v.get("party_name") or f"row {row.row_index + 1}"
        outcome.exceptions.append(ExceptionDraft(
            label=wording.AUDIT_ATTENTION_REQUIRED,
            area=AUDIT_AREA,
            trigger_condition=(
                f'Revenue transaction with "{party}" dated {txn_date.isoformat()}, {side} financial year end '
                f"({fy_end.isoformat()}), within the {PROXIMITY_WINDOW_DAYS}-day proximity window."
            ),
            explanation=(
                f'A revenue transaction with "{party}" for {paise_to_display(amount)} is dated {txn_date.isoformat()}'
                f", within the FinSight-configurable {PROXIMITY_WINDOW_DAYS}-day window {side} financial year end. "
                f"This flags the transaction for cut-off review only — it does not itself establish that the "
                f"transaction is recorded in the wrong period."
            ),
            suggested_query=(
                f'Please provide dispatch/delivery or service-completion evidence for the transaction with '
                f'"{party}" dated {txn_date.isoformat()}, to confirm the period it belongs to.'
            ),
            risk_level="HIGH",
            data_sources=[str(row.file_id)],
            threshold_used={
                "proximity_window_days": PROXIMITY_WINDOW_DAYS,
                "fy_end": fy_end.isoformat(),
                "side": side,
            },
            amount_paise=amount or None,
            related_transaction_id=row.transaction_id,
        ))

    return outcome
