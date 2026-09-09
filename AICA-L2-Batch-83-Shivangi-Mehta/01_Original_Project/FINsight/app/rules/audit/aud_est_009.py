"""
AUD-EST-009 — Significant Estimate-Linked Account Movement.

Audit area: Significant Estimates. Relevant SA: SA 540 (Auditing
Accounting Estimates — the original, non-"Revised" title; the 2023
"SA 540 (Revised)" exposure draft is not yet finalized by ICAI and is
not cited here). Assertions: Valuation, Accuracy.

SA Reference (authoritative — ICAI Standard on Auditing): SA 540. This
citation identifies accounting-estimate audit procedures as the
context this check informs; it does NOT mean SA 540 prescribes a 30%
movement threshold, or the estimate-related keyword list below — SA
540 describes the auditor's approach to estimates, not a numeric
trigger or a keyword taxonomy.
FinSight Analytical Test (created by FinSight, not prescribed by any
SA): flag an account whose name matches a FinSight estimate-related
keyword list (provision/reserve for/allowance/impairment/estimate —
`_ESTIMATE_KEYWORDS`) whose net balance moved, in either direction, by
at least a FinSight-configurable percentage versus a prior-year
engagement (currently 30% — `MOVEMENT_THRESHOLD_PCT`).

Reuses `shared_detectors.net_balance_by_account()` — the same
generalized detector AS29-PROV-010 (Accounting) uses — with a broader,
estimate-related keyword list, and `find_prior_year_dataset()`, per
Blueprint Section 1.1's "one detector, two interpretive layers"
principle. Unlike AS29-PROV-010 (which only measures a reduction/
utilization via `reversal_movement_amount_and_pct()`), this rule flags
movement in EITHER direction — an estimate-linked balance can warrant
audit attention whether it grew or shrank materially — so the
percentage is computed locally rather than reusing that helper.

What data is required: `GL`/`JE`/`TB` rows with `account_name`,
`debit_amount`/`credit_amount`, whose account name contains a
provision/reserve/allowance/impairment/estimate keyword, for the
current engagement AND a prior-year engagement for the same entity.
What can actually be established: the net balance per matching account
this year vs. the prior-year engagement, and whether the percentage
change (either direction) exceeds a configurable analytical threshold.
What cannot be established: whether management's estimation
methodology or assumptions are appropriate — only inspection of the
underlying working paper can establish that; this rule is a movement
signal only, never a judgment on the estimate's reasonableness.
Insufficient data: no prior-year engagement, no matching-keyword
accounts in this engagement, or no matching-keyword accounts in the
prior-year engagement.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.accounting.shared_detectors import find_prior_year_dataset, net_balance_by_account
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

RULE_ID = "AUD-EST-009"
AUDIT_AREA = "Significant Estimates"
RELATED_SA = "SA 540"
ASSERTIONS = ("VALUATION", "ACCURACY")
TOPIC = "Significant Estimate-Linked Account Movement"

# A broader keyword list than AS29-PROV-010's own — this rule looks at
# estimate-linked balances generally (provisions, reserves, allowances,
# impairments, and estimates by name), not only "provision" accounts.
_ESTIMATE_KEYWORDS = ("provision", "reserve for", "allowance", "impairment", "estimate")

# A FinSight-configurable analytical threshold, not an SA requirement.
MOVEMENT_THRESHOLD_PCT = 30.0


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    current_balances = net_balance_by_account(dataset, _ESTIMATE_KEYWORDS)
    if not current_balances:
        outcome.insufficient_data_reason = (
            "No account in this engagement's validated General Ledger/Journal Entry/Trial Balance data matches "
            "a provision, reserve, allowance, impairment, or estimate keyword."
        )
        return outcome

    prior_dataset = find_prior_year_dataset(engagement)
    if prior_dataset is None:
        outcome.insufficient_data_reason = (
            f"No prior-year engagement was found for \"{engagement.entity_name}\" — movement cannot be assessed "
            f"without a comparable prior period."
        )
        return outcome
    prior_balances = net_balance_by_account(prior_dataset, _ESTIMATE_KEYWORDS)
    if not prior_balances:
        outcome.insufficient_data_reason = (
            "A prior-year engagement for this entity exists, but no account in its validated data matches a "
            "provision, reserve, allowance, impairment, or estimate keyword to compare against."
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
        source_rows = [
            r for dt in ("GL", "JE", "TB") for r in dataset.get(dt, [])
            if (r.values.get("account_name") or "").strip() == account_name
        ]
        outcome.exceptions.append(ExceptionDraft(
            label=wording.AUDIT_ATTENTION_REQUIRED,
            area=AUDIT_AREA,
            trigger_condition=(
                f'Estimate-linked account "{account_name}" balance {direction} by {movement_pct}% compared to '
                f"the prior-year engagement (from {paise_to_display(prior)} to {paise_to_display(current)})."
            ),
            explanation=(
                f'Account "{account_name}" (matched as estimate-linked by name) moved from {paise_to_display(prior)} '
                f"to {paise_to_display(current)} ({movement_pct}%, {direction}) between the prior-year engagement "
                f"and this one — above the FinSight-configurable {MOVEMENT_THRESHOLD_PCT}% analytical threshold. "
                f"This flags the balance for review of management's estimation methodology and assumptions; it "
                f"does not itself evaluate whether that methodology or those assumptions are appropriate."
            ),
            suggested_query=(
                "Please provide the methodology and key assumptions supporting this estimate."
            ),
            risk_level="HIGH",
            data_sources=[str(r.file_id) for r in source_rows],
            threshold_used={
                "prior_balance_paise": prior,
                "current_balance_paise": current,
                "movement_pct": movement_pct,
                "finsight_analytical_threshold_pct": MOVEMENT_THRESHOLD_PCT,
                "threshold_is_sa_requirement": False,
                "direction": direction,
            },
            amount_paise=abs(current - prior),
        ))

    return outcome
