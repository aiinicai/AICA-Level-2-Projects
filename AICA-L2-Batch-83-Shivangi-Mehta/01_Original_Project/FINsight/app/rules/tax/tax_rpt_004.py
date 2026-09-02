"""
TAX-RPT-004 — Related-Party Payment Reasonableness Screen.

Legal provision: Section 40A(2), Income-tax Act, 1961. Expenditure to a
"specified person" (broadly: relatives, and persons/entities with a
substantial interest — 20%+ voting power or profit share) that the
Assessing Officer considers excessive or unreasonable, having regard to
fair market value or legitimate business need, may be disallowed to the
extent considered excessive/unreasonable. A pure reasonableness/fact
test — the Act specifies no fixed percentage or rupee threshold.

Verification: VERIFIED (old Act, 1961) — primary source: Section 40A,
incometaxindia.gov.in, full text fetched directly (see documentation/
stage10_tax_rule_catalogue_proposal.md, TAX-RPT-004). New Act 2025
forward reference (UNVERIFIED, non-gating): unresolved — three
independent secondary sources gave three different section numbers;
never used to decide executability, and not asserted here at all given
the conflict.

FinSight Analytical Test — a FinSight-designed heuristic screen for
Section 40A(2), not itself a figure the Act specifies (the Act's own
test is reasonableness against market value, which FinSight cannot
compute — it has no external market-rate data): reuses Audit's existing
`detect_related_party_candidates()` detector UNCHANGED (the same
keyword/name-similarity heuristic AUD-RPT-006 already uses — Blueprint
Section 1.1's "one detector, two interpretive layers" principle),
filtered to EXPENSE-side rows (a payment BY the entity, debit_amount >
0) since Section 40A(2) only concerns deductible expenditure, not
revenue-side related-party transactions.

Limitation: this produces a candidate list for professional
reasonableness review — it is NOT a disallowance computation and does
not establish related-party status under any legal definition (the
same limitation AUD-RPT-006 already discloses for the identical
detector). It deliberately overlaps with AUD-RPT-006 by design — the
same candidates, filtered to the expense side and re-interpreted
through Section 40A(2) rather than SA 550 — and should be reviewed
alongside AUD-RPT-006's findings rather than as an independent signal.

Insufficient data: no mapped row in this engagement's validated data
has a Party Name value at all.
"""
from __future__ import annotations

from collections import defaultdict

from app.rules import wording
from app.rules.accounting.shared_detectors import detect_related_party_candidates
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.rules.tax.act_transition import describe_act_era
from app.utils.currency import paise_to_display

RULE_ID = "TAX-RPT-004"
TOPIC = "Related-Party Payment Reasonableness Screen"
PROVISION_REFERENCE = "Section 40A(2), Income-tax Act, 1961"


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    any_party_name = any(row.values.get("party_name") for rows in dataset.values() for row in rows)
    if not any_party_name:
        outcome.insufficient_data_reason = (
            "No mapped row in this engagement's validated data has a Party Name value — related-party candidates "
            "cannot be identified without at least one party-bearing transaction file."
        )
        return outcome

    candidates = detect_related_party_candidates(dataset, engagement.entity_name)
    # Section 40A(2) concerns expenditure BY the entity — filter to the expense side.
    expense_candidates = [row for row in candidates if (row.values.get("debit_amount") or 0) > 0]
    outcome.evaluated_count = len(expense_candidates)
    if not expense_candidates:
        return outcome

    by_party: dict[str, list] = defaultdict(list)
    for row in expense_candidates:
        by_party[(row.values.get("party_name") or "").strip()].append(row)

    era = describe_act_era(engagement.financial_year)
    for party_name, rows in by_party.items():
        reason = getattr(rows[0], "_related_party_reason", "matched the related-party keyword/name-similarity heuristic")
        total_amount = sum(r.values.get("debit_amount") or 0 for r in rows)
        outcome.exceptions.append(ExceptionDraft(
            label=wording.POTENTIAL_TAX_ISSUE,
            area=TOPIC,
            trigger_condition=(
                f'Expense payment(s) to related-party candidate "{party_name}" total {paise_to_display(total_amount)} '
                f"across {len(rows)} transaction(s)."
            ),
            explanation=(
                f'{era}. Section 40A(2) permits disallowance of expenditure to a "specified person" that is '
                f'excessive or unreasonable relative to fair market value or legitimate business need — a '
                f'reasonableness test the Act itself does not reduce to a fixed threshold, and FinSight has no '
                f'external market-rate data to apply it. FinSight identified "{party_name}" as a related-party '
                f'CANDIDATE ONLY (it {reason} — the same text heuristic Audit\'s AUD-RPT-006 uses), with expense '
                f"payments totaling {paise_to_display(total_amount)}. This does NOT establish related-party status "
                f"under any legal definition, nor that any amount is excessive or unreasonable — only a "
                f"professional review of the actual relationship and market terms can do that. This is a "
                f"potential issue for review, not a confirmed disallowance."
            ),
            suggested_query=(
                f'Please confirm the actual relationship, if any, between the entity and "{party_name}", and '
                f"whether the payment terms reflect fair market value for the goods/services provided."
            ),
            risk_level="MEDIUM",
            data_sources=[str(r.file_id) for r in rows],
            threshold_used={
                "threshold_is_statutory": False,
                "statutory_source": PROVISION_REFERENCE,
                "identification_method": "reuses shared_detectors.detect_related_party_candidates() unchanged, expense-side only",
                "candidate_only_not_confirmed": True,
                "transaction_count": len(rows),
            },
            amount_paise=total_amount or None,
        ))

    return outcome
