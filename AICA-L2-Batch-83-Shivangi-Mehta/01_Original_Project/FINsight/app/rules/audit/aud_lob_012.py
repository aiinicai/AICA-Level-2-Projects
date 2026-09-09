"""
AUD-LOB-012 — Long Outstanding Balances.

Audit area: Long Outstanding Balances. Relevant SA: SA 500, SA 505
(External Confirmations). Assertions: Existence, Valuation, Rights &
Obligations.

SA Reference (authoritative — ICAI Standard on Auditing): SA 500,
SA 505. This citation identifies audit evidence and external
confirmations as the procedures this check informs (SA 505 governs how
a confirmation, if performed, should be designed and evaluated); it
does NOT mean either standard prescribes a 180-day ageing threshold or
a minimum-outstanding floor — both are FinSight's own.
FinSight Analytical Test (created by FinSight, not prescribed by any
SA): flag an AR/AP party balance, net as of financial year end, whose
last recorded movement was at least a FinSight-configurable number of
days before year end (currently 180 — `AGEING_THRESHOLD_DAYS`), where
the balance is also at or above a small FinSight noise floor (currently
₹1,000 — `MINIMUM_OUTSTANDING_PAISE`).

What data is required: `AR`/`AP` rows with `party_name`,
`transaction_date`, `debit_amount`/`credit_amount`.
What can actually be established: a net outstanding balance per party
as of financial year end (AR: debit − credit; AP: credit − debit — the
polarity is inferred from the dataset_type the row came from, an
assumption disclosed here rather than silently assumed), and an ageing
approximation measured as days since that party's last recorded
transaction_date on or before financial year end.
What cannot be established: true invoice-level ageing. No due-date or
invoice-date field exists anywhere in the approved schema, so ageing
here is approximated as "days since the party's last recorded
movement," not per-invoice ageing against payment terms — this
limitation is stated in every finding, not silently assumed away.
Insufficient data: no validated AR or AP data at all for this
engagement, or the engagement's financial year cannot be parsed.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.rules import wording
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.rules.period_utils import financial_year_bounds
from app.utils.currency import paise_to_display

RULE_ID = "AUD-LOB-012"
AUDIT_AREA = "Long Outstanding Balances"
RELATED_SA = "SA 500, SA 505"
ASSERTIONS = ("EXISTENCE", "VALUATION", "RIGHTS_OBLIGATIONS")
TOPIC = "Long Outstanding Balances"

# FinSight-configurable, not SA requirements.
AGEING_THRESHOLD_DAYS = 180
MINIMUM_OUTSTANDING_PAISE = 100_000  # ~₹1,000 — a noise floor, not a materiality judgment

_LEDGER_POLARITY = {"AR": 1, "AP": -1}  # multiplier applied to (debit - credit)


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    ar_rows = dataset.get("AR", [])
    ap_rows = dataset.get("AP", [])
    if not ar_rows and not ap_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Accounts Receivable or Accounts Payable data is available for this "
            "engagement."
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

    # party_name -> [dataset_type, net_balance_paise, last_txn_date, file_ids]
    parties: dict[str, dict] = {}
    for dataset_type, rows in (("AR", ar_rows), ("AP", ap_rows)):
        polarity = _LEDGER_POLARITY[dataset_type]
        for row in rows:
            v = row.values
            party_name = (v.get("party_name") or "").strip()
            raw_date = v.get("transaction_date")
            if not party_name or not raw_date:
                outcome.partial_insufficient_data_notes.append(
                    f"{dataset_type} row (file {row.file_id}, row {row.row_index + 1}): no Party Name or no "
                    f"Transaction Date — could not be included in the outstanding-balance computation."
                )
                continue
            try:
                txn_date = date.fromisoformat(raw_date)
            except ValueError:
                outcome.partial_insufficient_data_notes.append(
                    f"{dataset_type} row (file {row.file_id}, row {row.row_index + 1}): Transaction Date could "
                    f"not be parsed."
                )
                continue
            if txn_date > fy_end:
                continue  # only balances/movements as of FY end are relevant here

            debit = v.get("debit_amount") or 0
            credit = v.get("credit_amount") or 0
            entry = parties.setdefault(party_name, {
                "dataset_type": dataset_type, "balance": 0, "last_date": None, "file_ids": set(),
            })
            entry["balance"] += polarity * (debit - credit)
            entry["file_ids"].add(str(row.file_id))
            if entry["last_date"] is None or txn_date > entry["last_date"]:
                entry["last_date"] = txn_date

    outcome.evaluated_count = len(parties)

    for party_name, entry in parties.items():
        balance = entry["balance"]
        last_date = entry["last_date"]
        if balance <= 0 or last_date is None:
            continue
        if balance < MINIMUM_OUTSTANDING_PAISE:
            continue

        ageing_days = (fy_end - last_date).days
        if ageing_days < AGEING_THRESHOLD_DAYS:
            continue

        dataset_type = entry["dataset_type"]
        ledger_label = "receivable from" if dataset_type == "AR" else "payable to"
        outcome.exceptions.append(ExceptionDraft(
            label=wording.POTENTIAL_AUDIT_RISK,
            area=AUDIT_AREA,
            trigger_condition=(
                f'Net {ledger_label} "{party_name}" of {paise_to_display(balance)} has no recorded movement for '
                f"{ageing_days} day(s) as of financial year end ({fy_end.isoformat()})."
            ),
            explanation=(
                f'The net {ledger_label} "{party_name}" is {paise_to_display(balance)}, with its last recorded '
                f"movement on {last_date.isoformat()} — {ageing_days} day(s) before financial year end, above the "
                f"FinSight-configurable {AGEING_THRESHOLD_DAYS}-day ageing threshold. No due-date or invoice-date "
                f"field exists in the uploaded data, so this ageing is approximated as days since the party's "
                f"last recorded movement, not true per-invoice ageing against payment terms. The {ledger_label.split()[0]} "
                f"polarity (debit-credit for AR, credit-debit for AP) is a FinSight assumption based on the "
                f"dataset type the rows came from."
            ),
            suggested_query=(
                f'Please provide the status of the outstanding balance with "{party_name}" — a confirmation, or '
                f"evidence of subsequent realization/settlement."
            ),
            risk_level="MEDIUM",
            data_sources=sorted(entry["file_ids"]),
            threshold_used={
                "ageing_threshold_days": AGEING_THRESHOLD_DAYS,
                "minimum_outstanding_paise": MINIMUM_OUTSTANDING_PAISE,
                "ageing_days": ageing_days,
                "ageing_is_approximated_not_per_invoice": True,
                "polarity_source_dataset_type": dataset_type,
                "threshold_is_sa_requirement": False,
            },
            amount_paise=balance,
        ))

    return outcome
