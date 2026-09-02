"""
AUD-MOV-005 — Significant Account Balance Movement vs Prior Year.

Audit area: Analytical Review. Relevant SA: SA 520 (Analytical
Procedures). Assertions: Completeness, Accuracy, Existence. Risk level:
MEDIUM (Stage 9 catalogue review downgraded this from the original
proposal's High — "a 25% movement is an analytical review indicator,
not automatically high risk").

SA Reference (authoritative — ICAI Standard on Auditing): SA 520. This
citation identifies analytical procedures as the general audit
technique this check applies; it does NOT mean SA 520 prescribes a 25%
movement threshold — SA 520 describes the analytical-procedures
methodology, not a specific numeric trigger.
FinSight Analytical Test (created by FinSight, not prescribed by any
SA): flag a Trial Balance account whose net balance moved, in either
direction, by at least a FinSight-configurable percentage versus a
prior-year engagement for the same entity (currently 25% —
`MOVEMENT_THRESHOLD_PCT`).

What data is required: `TB` rows with `account_name`, `debit_amount`/
`credit_amount`, for the current engagement AND a prior-year engagement
for the same entity.
What can actually be established: the net balance (credit - debit) per
account this year vs. the prior-year engagement, and whether the
percentage change exceeds a configurable threshold.
What cannot be established: no `account_type` field exists anywhere in
the approved schema to distinguish balance-sheet from P&L accounts, so
this is a raw balance-movement signal, not a ratio benchmarked to
account nature — disclosed explicitly in every finding.
Insufficient data: no prior-year engagement, or the prior-year
engagement has no validated Trial Balance data.
"""
from __future__ import annotations

from collections import defaultdict

from app.rules import wording
from app.rules.accounting.shared_detectors import find_prior_year_dataset
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-MOV-005"
AUDIT_AREA = "Analytical Review"
RELATED_SA = "SA 520"
ASSERTIONS = ("COMPLETENESS", "ACCURACY", "EXISTENCE")
TOPIC = "Significant Account Balance Movement vs Prior Year"

# A FinSight-configurable analytical threshold, not an SA requirement.
MOVEMENT_THRESHOLD_PCT = 25.0


def _tb_balances(dataset: dict[str, list]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for row in dataset.get("TB", []):
        account_name = (row.values.get("account_name") or "").strip()
        if not account_name:
            continue
        debit = row.values.get("debit_amount") or 0
        credit = row.values.get("credit_amount") or 0
        totals[account_name] += credit - debit
    return totals


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    current_balances = _tb_balances(dataset)
    if not current_balances:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Trial Balance data is available for this engagement."
        )
        return outcome

    prior_dataset = find_prior_year_dataset(engagement)
    if prior_dataset is None:
        outcome.insufficient_data_reason = (
            f"No prior-year engagement was found for \"{engagement.entity_name}\" — movement cannot be assessed "
            f"without a comparable prior period."
        )
        return outcome
    prior_balances = _tb_balances(prior_dataset)
    if not prior_balances:
        outcome.insufficient_data_reason = (
            "A prior-year engagement for this entity exists, but it has no validated Trial Balance data to "
            "compare against."
        )
        return outcome

    for account_name, current in current_balances.items():
        prior = prior_balances.get(account_name)
        if prior is None:
            outcome.partial_insufficient_data_notes.append(
                f'Account "{account_name}" has no comparable prior-year balance to compare against.'
            )
            continue
        outcome.evaluated_count += 1
        if prior == 0:
            continue  # no meaningful percentage base

        movement_pct = round(abs(current - prior) / abs(prior) * 100, 1)
        if movement_pct < MOVEMENT_THRESHOLD_PCT:
            continue

        direction = "increased" if current > prior else "decreased"
        outcome.exceptions.append(ExceptionDraft(
            label=wording.POTENTIAL_AUDIT_RISK,
            area=AUDIT_AREA,
            trigger_condition=(
                f'Account "{account_name}" balance {direction} by {movement_pct}% compared to the prior-year '
                f"engagement (from {paise_to_display(prior)} to {paise_to_display(current)})."
            ),
            explanation=(
                f'Account "{account_name}" moved from {paise_to_display(prior)} to {paise_to_display(current)} '
                f"({movement_pct}%) between the prior-year engagement and this one — above the FinSight-"
                f"configurable {MOVEMENT_THRESHOLD_PCT}% analytical threshold. No account-type/classification "
                f"field exists in the uploaded data, so this is a raw balance-movement signal, not a ratio "
                f"benchmarked to whether the account is a balance-sheet or P&L item; it is an indicator for "
                f"analytical review, not a confirmed finding."
            ),
            suggested_query=(
                f'Please explain the {movement_pct}% movement in "{account_name}" compared to the prior year and '
                f"provide any supporting schedule."
            ),
            risk_level="MEDIUM",
            data_sources=[str(r.file_id) for r in dataset.get("TB", []) if (r.values.get("account_name") or "").strip() == account_name],
            threshold_used={
                "prior_balance_paise": prior,
                "current_balance_paise": current,
                "movement_pct": movement_pct,
                "finsight_analytical_threshold_pct": MOVEMENT_THRESHOLD_PCT,
                "threshold_is_sa_requirement": False,
            },
            amount_paise=abs(current - prior),
        ))

    return outcome
