"""
AS10-FA-001 / INDAS16-FA-001 — Fixed Assets: Roll-Forward Consistency
Review.

Framework: AS 10 (Property, Plant and Equipment) / Ind AS 16 (Property,
Plant and Equipment) — same standard number under both frameworks by
coincidence; NOT the same standard as Ind AS 10 ("Events after the
Reporting Period"), which is unrelated. Framework-aware: one shared
`evaluate()` produces the correct `rule_id` for whichever framework the
runner asks for (`app/services/rule_runner_service.py` additionally
enforces this at the gate — a rule's own `AccountingRule.framework`
row must match the engagement's framework before this even runs).

REDESIGNED in Stage 8 Round 2 (correction #3). The original version
compared recorded depreciation to a straight-line, time-apportioned
reference expectation — this produced false positives for any entity
genuinely using WDV, units-of-production, or another valid method,
since nothing in the uploaded data says which method applies (no
`depreciation_method` or `residual_value` field exists anywhere in the
approved schema). Recording a "Potential Accounting Exception" purely
because a figure differs from an *assumed* method the entity was never
shown to use was exactly the false-positive risk flagged in review.

What data is required: `fixed_assets` rows with `opening_wdv_paise`,
`additions_paise`, `deletions_paise`, `book_depreciation_amount_paise`,
and `closing_wdv_paise` all present.
What can actually be established: whether the entity's OWN reported
roll-forward figures reconcile arithmetically — opening WDV + additions
- deletions - recorded depreciation should equal closing WDV. This is
method-agnostic: it holds true whatever depreciation method (SLM, WDV,
units-of-production, or anything else) actually produced the recorded
depreciation figure, so no method is ever assumed.
What cannot be established: which specific depreciation method was
used (no field captures it), whether that method is appropriate, what
the "correct" depreciation figure should be, or which of the five
reported figures is wrong if the roll-forward doesn't tie — only that
it doesn't tie.
Insufficient data: any asset missing one of the five required
roll-forward fields is excluded from the check and reported separately,
per-asset, never silently treated as reconciling or not.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.accounting.shared_detectors import (
    ROLL_FORWARD_TOLERANCE_PAISE,
    reconcile_asset_roll_forward,
    roll_forward_fields_present,
)
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.utils.currency import paise_to_display

FRAMEWORK_RULE_IDS = {"AS": "AS10-FA-001", "IND_AS": "INDAS16-FA-001"}
TOPIC = "Fixed Assets — Roll-Forward Consistency Review"


def evaluate(engagement, dataset: dict[str, list], framework: str) -> RuleOutcome:
    rule_id = FRAMEWORK_RULE_IDS.get(framework, FRAMEWORK_RULE_IDS["AS"])
    outcome = RuleOutcome(rule_id=rule_id)

    assets = dataset.get("FIXED_ASSETS", [])
    if not assets:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Fixed Asset Register data is available for this engagement."
        )
        return outcome

    for row in assets:
        v = row.values
        description = v.get("asset_description") or f"asset (row {row.row_index + 1})"

        if not roll_forward_fields_present(v):
            outcome.partial_insufficient_data_notes.append(
                f"{description}: opening WDV, additions, deletions, recorded depreciation, and closing WDV are not "
                f"all present — and no depreciation method or residual value field is captured in the uploaded "
                f"data either, so a roll-forward consistency check could not be attempted for this asset."
            )
            continue

        outcome.evaluated_count += 1
        diff = reconcile_asset_roll_forward(
            v["opening_wdv_paise"], v["additions_paise"], v["deletions_paise"],
            v["book_depreciation_amount_paise"], v["closing_wdv_paise"],
        )
        if abs(diff) <= ROLL_FORWARD_TOLERANCE_PAISE:
            continue

        outcome.exceptions.append(ExceptionDraft(
            label=wording.REVIEW_REQUIRED,
            area=TOPIC,
            trigger_condition=(
                f"{description}: the reported roll-forward (opening WDV + additions - deletions - recorded "
                f"depreciation) does not reconcile with the reported closing WDV — a difference of approximately "
                f"{paise_to_display(abs(diff))}."
            ),
            explanation=(
                f"For {description}, opening WDV of {paise_to_display(v['opening_wdv_paise'])} plus additions of "
                f"{paise_to_display(v['additions_paise'])} less deletions of {paise_to_display(v['deletions_paise'])} "
                f"less recorded depreciation of {paise_to_display(v['book_depreciation_amount_paise'])} implies a "
                f"closing WDV that differs from the reported closing WDV of "
                f"{paise_to_display(v['closing_wdv_paise'])} by approximately {paise_to_display(abs(diff))}. This "
                f"is a roll-forward arithmetic check only — it does not assume straight-line, WDV, units-of-"
                f"production, or any other specific depreciation method, and it does not indicate which of the "
                f"reported figures, if any, is incorrect."
            ),
            suggested_query=(
                f"Please reconcile the reported roll-forward for {description} — the opening WDV, additions, "
                f"deletions, and recorded depreciation do not arithmetically produce the reported closing WDV."
            ),
            risk_level="MEDIUM",
            data_sources=[str(row.file_id)],
            threshold_used={
                "tolerance_paise": ROLL_FORWARD_TOLERANCE_PAISE,
                "opening_wdv_paise": v["opening_wdv_paise"],
                "additions_paise": v["additions_paise"],
                "deletions_paise": v["deletions_paise"],
                "book_depreciation_amount_paise": v["book_depreciation_amount_paise"],
                "closing_wdv_paise": v["closing_wdv_paise"],
                "difference_paise": diff,
            },
            amount_paise=abs(diff),
        ))

    return outcome
