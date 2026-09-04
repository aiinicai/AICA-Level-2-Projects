"""
AS16-BC-006 / INDAS23-BC-006 — Borrowing Costs: Capitalization Review
Signal.

Framework: AS 16 (Borrowing Costs) / Ind AS 23 (Borrowing Costs).

POLISHED in Stage 8 Round 2 (correction #6) — the label was already
"Review Required" (never an accounting-exception label), but the
finding text is now explicit about the four specific things this
co-occurrence signal cannot establish, so a reviewer never mistakes a
flagged co-occurrence for a finding that borrowing costs were (or
should have been) capitalized.

What data is required: `fixed_assets` rows tagged as capital work in
progress (CWIP), and ledger-style rows (TB/GL/JE) whose `account_name`
looks like a loan/borrowing account with a nonzero balance/movement.
What can actually be established: whether a CWIP-tagged asset and a
loan-like account are BOTH present for this engagement — a coarse
co-occurrence signal only. It deliberately does not attempt to read the
CWIP asset's own narration/description to guess a link (the Stage 3
redesign explicitly ruled out narration-guessing as unreliable) — same
class of coarse heuristic as GEN-PPI-012/AS18-RPT-009.
What cannot be established, and is stated explicitly in every finding
this rule raises: (1) whether the CWIP asset meets the "qualifying
asset" test under AS 16/Ind AS 23; (2) whether any specific borrowing
can be directly attributed to that asset; (3) whether the conditions
for commencing capitalization (expenditure being incurred, borrowing
costs being incurred, and activities necessary to prepare the asset
being in progress) are met; (4) whether any actual borrowing cost was,
in fact, capitalized. None of these four are derivable from the
uploaded transactional data alone.
Insufficient data: no CWIP-tagged fixed asset exists for this
engagement at all (nothing to potentially capitalize borrowing costs
into).
"""
from __future__ import annotations

from app.rules import wording
from app.rules.base_rule import ExceptionDraft, RuleOutcome

FRAMEWORK_RULE_IDS = {"AS": "AS16-BC-006", "IND_AS": "INDAS23-BC-006"}
TOPIC = "Borrowing Costs — Capitalization Review Signal"
_CWIP_KEYWORDS = ("cwip", "capital work in progress", "work in progress", "wip")
_LOAN_KEYWORDS = ("loan", "borrowing", "term loan", "cash credit", "overdraft", "debenture", "bank od")
_LEDGER_TYPES = ("TB", "GL", "JE")


def _find_cwip_assets(dataset: dict[str, list]) -> list:
    matches = []
    for row in dataset.get("FIXED_ASSETS", []):
        asset_class = (row.values.get("asset_class") or "").strip().lower()
        description = (row.values.get("asset_description") or "").strip().lower()
        if any(k in asset_class for k in _CWIP_KEYWORDS) or any(k in description for k in _CWIP_KEYWORDS):
            matches.append(row)
    return matches


def _find_loan_rows(dataset: dict[str, list]) -> list:
    matches = []
    for dataset_type in _LEDGER_TYPES:
        for row in dataset.get(dataset_type, []):
            account_name = (row.values.get("account_name") or "").strip().lower()
            if not account_name or not any(k in account_name for k in _LOAN_KEYWORDS):
                continue
            debit = row.values.get("debit_amount") or 0
            credit = row.values.get("credit_amount") or 0
            if debit or credit:
                matches.append(row)
    return matches


def evaluate(engagement, dataset: dict[str, list], framework: str) -> RuleOutcome:
    rule_id = FRAMEWORK_RULE_IDS.get(framework, FRAMEWORK_RULE_IDS["AS"])
    outcome = RuleOutcome(rule_id=rule_id)

    cwip_assets = _find_cwip_assets(dataset)
    if not cwip_assets:
        outcome.insufficient_data_reason = (
            "No validated Fixed Asset Register row is tagged as capital work in progress (CWIP) for this "
            "engagement — there is no qualifying asset under construction for borrowing costs to potentially "
            "relate to."
        )
        return outcome

    loan_rows = _find_loan_rows(dataset)
    outcome.evaluated_count = len(cwip_assets)

    if not loan_rows:
        outcome.partial_insufficient_data_notes.append(
            f"{len(cwip_assets)} CWIP-tagged asset(s) were found, but no ledger account matching common "
            f"loan/borrowing keywords with a nonzero balance was found in this engagement's validated data — "
            f"borrowing-cost capitalization relevance could not be assessed further."
        )
        return outcome

    cwip_total_paise = sum(r.values.get("original_cost_paise") or 0 for r in cwip_assets)
    loan_total_paise = sum((r.values.get("debit_amount") or 0) + (r.values.get("credit_amount") or 0) for r in loan_rows)

    outcome.exceptions.append(ExceptionDraft(
        label=wording.REVIEW_REQUIRED,
        area=TOPIC,
        trigger_condition=(
            f"{len(cwip_assets)} capital-work-in-progress asset(s) and {len(loan_rows)} loan/borrowing-like "
            f"ledger entries were both found in this engagement's validated data."
        ),
        explanation=(
            "Both a capital-work-in-progress asset and one or more loan/borrowing-like ledger accounts are "
            "present in this engagement — a co-occurrence signal only. The uploaded data cannot establish: "
            "(1) whether the asset meets the \"qualifying asset\" test; (2) whether any specific borrowing is "
            "directly attributable to it; (3) whether the conditions for commencing capitalization (expenditure "
            "incurred, borrowing costs incurred, and preparation activities in progress) are met; or "
            "(4) whether any actual borrowing cost was, in fact, capitalized. No attempt was made to infer a "
            "link from asset descriptions or narration."
        ),
        suggested_query=(
            "Please confirm whether the capital-work-in-progress asset(s) meet the qualifying-asset test, "
            "whether any borrowing is directly attributable to them, and whether any borrowing costs were "
            "capitalized during this period."
        ),
        risk_level="LOW",
        data_sources=[str(r.file_id) for r in cwip_assets] + [str(r.file_id) for r in loan_rows],
        threshold_used={
            "cwip_asset_count": len(cwip_assets),
            "loan_row_count": len(loan_rows),
            "cwip_total_paise": cwip_total_paise,
            "loan_total_paise": loan_total_paise,
        },
    ))

    return outcome
