"""
AS26-INT-011 / INDAS38-INT-011 — Intangible Assets: Roll-Forward
Consistency Review.

Framework: AS 26 (Intangible Assets) / Ind AS 38 (Intangible Assets).
Framework-aware, same pattern as AS10-FA-001/INDAS16-FA-001.

REDESIGNED in Stage 8 Round 2 (correction #4 — "apply the same
principle" as AS10-FA-001's correction #3). Same reasoning: no
amortization-method field exists, so amortization/depreciation method
is never assumed. Replaced with the same method-agnostic roll-forward
arithmetic identity check used for tangible assets, applied to Fixed
Asset Register rows tagged `asset_class` containing "Intangible" (the
schema has no separate amortization column — `book_depreciation_amount_
paise` and the WDV fields are reused for intangibles regardless of
asset class, per the model's own design, matching AS10-FA-001's
established precedent for this field reuse).

What data is required: `fixed_assets` rows with `asset_class`
containing "Intangible", plus the same five roll-forward fields
AS10-FA-001 needs.
What cannot be established: the entity's actual amortization method or
useful-life basis — same as AS10-FA-001, no method is ever assumed.
Insufficient data: no rows tagged Intangible present at all, or a
tagged row missing one of the five roll-forward fields.
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

FRAMEWORK_RULE_IDS = {"AS": "AS26-INT-011", "IND_AS": "INDAS38-INT-011"}
TOPIC = "Intangible Assets — Roll-Forward Consistency Review"


def evaluate(engagement, dataset: dict[str, list], framework: str) -> RuleOutcome:
    rule_id = FRAMEWORK_RULE_IDS.get(framework, FRAMEWORK_RULE_IDS["AS"])
    outcome = RuleOutcome(rule_id=rule_id)

    all_assets = dataset.get("FIXED_ASSETS", [])
    intangibles = [r for r in all_assets if "intangible" in (r.values.get("asset_class") or "").strip().lower()]

    if not intangibles:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Fixed Asset Register rows are tagged asset_class = \"Intangible\" "
            "for this engagement."
        )
        return outcome

    for row in intangibles:
        v = row.values
        description = v.get("asset_description") or f"intangible asset (row {row.row_index + 1})"

        if not roll_forward_fields_present(v):
            outcome.partial_insufficient_data_notes.append(
                f"{description}: opening WDV, additions, deletions, recorded amortization, and closing WDV are "
                f"not all present — and no amortization method or residual value field is captured in the "
                f"uploaded data either, so a roll-forward consistency check could not be attempted for this asset."
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
                f"amortization) does not reconcile with the reported closing WDV — a difference of approximately "
                f"{paise_to_display(abs(diff))}."
            ),
            explanation=(
                f"For {description}, opening WDV of {paise_to_display(v['opening_wdv_paise'])} plus additions of "
                f"{paise_to_display(v['additions_paise'])} less deletions of {paise_to_display(v['deletions_paise'])} "
                f"less recorded amortization of {paise_to_display(v['book_depreciation_amount_paise'])} implies a "
                f"closing WDV that differs from the reported closing WDV of "
                f"{paise_to_display(v['closing_wdv_paise'])} by approximately {paise_to_display(abs(diff))}. This "
                f"is a roll-forward arithmetic check only — it does not assume straight-line or any other "
                f"specific amortization method, and it does not indicate which of the reported figures, if any, "
                f"is incorrect."
            ),
            suggested_query=(
                f"Please reconcile the reported roll-forward for {description} — the opening WDV, additions, "
                f"deletions, and recorded amortization do not arithmetically produce the reported closing WDV."
            ),
            risk_level="LOW",
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
