"""
AS29-PROV-010 / INDAS37-PROV-010 — Provisions: Significant Movement
Review.

Framework: AS 29 (Provisions, Contingent Liabilities and Contingent
Assets) / Ind AS 37 (Provisions, Contingent Liabilities and Contingent
Assets).

REFRAMED in Stage 8 Round 2 (correction #5). The 50% reversal threshold
is a **configurable FinSight analytical threshold**, not an accounting-
standard requirement — the standards themselves impose no such
percentage. A movement crossing this threshold is a trigger for
professional review of the current best estimate and its supporting
basis; it is never itself described as an accounting inconsistency, and
this rule now uses the "Review Required" label rather than any wording
implying the standard was breached or the movement is wrong.

What data is required: ledger-style transaction data (GL/JE/TB) for
both the current engagement and a prior-year engagement for the SAME
entity, with `account_name` values that look like a provision account.
What can actually be established: the prior year's closing provision
balance for a matching account name (net credit balance), and how much
of it moved (net debit) in the current period — a proxy for how much of
the provision was reversed or utilized. Whether a movement above the
threshold below actually warrants further review is a FinSight
analytical judgment call, tunable, and disclosed as such in every
finding this rule raises.
What cannot be established: whether a movement is supported by a
documented change in the current best estimate — no policy-note field
exists.
Insufficient data: no prior-year engagement, no provision-like accounts
in either period, or no matching account name between the two periods.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.accounting.shared_detectors import (
    find_prior_year_dataset,
    net_balance_by_account,
    reversal_movement_amount_and_pct,
)
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

FRAMEWORK_RULE_IDS = {"AS": "AS29-PROV-010", "IND_AS": "INDAS37-PROV-010"}
TOPIC = "Provisions — Significant Movement Review"
_PROVISION_KEYWORDS = ("provision", "reserve for")
# A FinSight-configured analytical trigger, not an accounting-standard
# threshold — see the module docstring and every finding's explanation
# text, which states this explicitly rather than implying a standard
# requirement.
_SIGNIFICANT_MOVEMENT_THRESHOLD_PCT = 50.0

# Stage 9: _net_balance_by_account() and the inline movement calculation
# that used to live here were extracted, unchanged in behavior, into
# app.rules.accounting.shared_detectors.net_balance_by_account() /
# reversal_movement_amount_and_pct() so AUD-EST-009 (Audit) can reuse
# the exact same mechanism against its own keyword list — see that
# module's docstring for the "one detector, two interpretive layers"
# reasoning (Section 1.1). This rule's own behavior is unchanged; only
# where the code lives changed.


def evaluate(engagement, dataset: dict[str, list], framework: str) -> RuleOutcome:
    rule_id = FRAMEWORK_RULE_IDS.get(framework, FRAMEWORK_RULE_IDS["AS"])
    outcome = RuleOutcome(rule_id=rule_id)

    current_balances = net_balance_by_account(dataset, _PROVISION_KEYWORDS)
    if not current_balances:
        outcome.insufficient_data_reason = (
            "No ledger accounts resembling a provision (matching common keywords) were found in this "
            "engagement's validated data."
        )
        return outcome

    prior_dataset = find_prior_year_dataset(engagement)
    if prior_dataset is None:
        outcome.insufficient_data_reason = (
            f"No prior-year engagement was found for \"{engagement.entity_name}\" — provision movement "
            f"cannot be assessed without a comparable prior period."
        )
        return outcome
    prior_balances = net_balance_by_account(prior_dataset, _PROVISION_KEYWORDS)
    if not prior_balances:
        outcome.insufficient_data_reason = (
            "A prior-year engagement for this entity exists, but no provision-like accounts were found in its "
            "validated data to compare against."
        )
        return outcome

    for account_name, prior_closing in prior_balances.items():
        if prior_closing <= 0:
            continue  # no provision was actually carried forward — nothing to reverse
        current_movement = current_balances.get(account_name)
        outcome.evaluated_count += 1
        if current_movement is None:
            outcome.partial_insufficient_data_notes.append(
                f'Provision account "{account_name}" had a balance carried forward from the prior year, but no '
                f"matching account was found in this year's data — movement could not be assessed."
            )
            continue

        movement_amount, movement_pct = reversal_movement_amount_and_pct(prior_closing, current_movement)

        if movement_pct >= _SIGNIFICANT_MOVEMENT_THRESHOLD_PCT:
            outcome.exceptions.append(ExceptionDraft(
                label=wording.REVIEW_REQUIRED,
                area=TOPIC,
                trigger_condition=(
                    f'Provision account "{account_name}" moved by approximately {paise_to_display(movement_amount)} '
                    f"this period ({movement_pct}% of its {paise_to_display(prior_closing)} opening balance) — "
                    f"exceeds the {_SIGNIFICANT_MOVEMENT_THRESHOLD_PCT}% FinSight analytical threshold used to "
                    f"flag movements for review."
                ),
                explanation=(
                    f'The provision account "{account_name}" carried an opening balance of approximately '
                    f"{paise_to_display(prior_closing)} from the prior-year engagement, and moved by approximately "
                    f"{paise_to_display(movement_amount)} ({movement_pct}%) in the current period. This exceeds a "
                    f"configurable FinSight analytical threshold ({_SIGNIFICANT_MOVEMENT_THRESHOLD_PCT}% of the "
                    f"opening balance) used only to flag movements that may warrant review of the current best "
                    f"estimate and its supporting basis — it is not an accounting-standard requirement, and this "
                    f"movement is not, on its own, described as inconsistent with AS 29/Ind AS 37. Whether the "
                    f"movement reflects a documented change in the current best estimate could not be established "
                    f"from the uploaded data — no policy-note field or linked document was available to check."
                ),
                suggested_query=(
                    f'Please explain the basis for the movement in the provision for "{account_name}", including '
                    f"whether it reflects a change in the current best estimate."
                ),
                risk_level="MEDIUM",
                data_sources=[str(r.file_id) for rows in dataset.values() for r in rows
                              if (r.values.get("account_name") or "").strip() == account_name],
                threshold_used={
                    "prior_closing_paise": prior_closing,
                    "current_movement_paise": current_movement,
                    "movement_pct": movement_pct,
                    "finsight_analytical_threshold_pct": _SIGNIFICANT_MOVEMENT_THRESHOLD_PCT,
                    "threshold_is_accounting_standard_requirement": False,
                },
                amount_paise=movement_amount,
            ))

    return outcome
