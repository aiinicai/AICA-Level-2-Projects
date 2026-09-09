"""
AS5-PPI-012 / INDAS8-PPE-012 — Prior Period Items / Prior Period Errors
(narration keyword heuristic).

Framework: AS 5 (Net Profit or Loss for the Period, Prior Period Items
and Changes in Accounting Policies) / Ind AS 8 (Accounting Policies,
Changes in Accounting Estimates and Errors).

SPLIT in Stage 8 Round 2 (correction #7). "Prior Period Items" is AS
5's own defined term (para 4.3: "income or expenses which arise in the
current period as a result of errors or omissions in the preparation
of the financial statements of one or more prior periods"). "Prior
Period Errors" is Ind AS 8's own, substantively different, defined
term (para 5: omissions/misstatements from a failure to use, or misuse
of, reliable information available when prior-period statements were
authorised for issue — framed explicitly around error-correction with
retrospective-restatement mechanics). These are not interchangeable
synonyms, so the standard reference, explanation, and suggested query
are now framework-specific; only the underlying narration-keyword
heuristic is shared (unchanged, still explicitly a text heuristic, not
a determination).

What data is required: ledger-style rows (GL/JE, where narration-style
free text is most likely to be present) with a `description` value.
What can actually be established: whether the free-text description/
narration contains a keyword commonly used for prior-period adjustments
("prior period", "previous year", "PY adjustment", etc.). This is a
plain keyword match — it does not parse accounting meaning, and it does
not distinguish a genuine prior-period item/error from, say, narration
merely referencing a prior-year invoice number in an otherwise ordinary
current-period entry.
What cannot be established: whether a flagged entry is in fact a prior
period item (AS 5) or prior period error (Ind AS 8), whether it was
material, or whether it was appropriately disclosed/restated.
Insufficient data: no GL/JE row has a non-blank `description` value at
all.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.base_rule import ExceptionDraft, RuleOutcome

FRAMEWORK_RULE_IDS = {"AS": "AS5-PPI-012", "IND_AS": "INDAS8-PPE-012"}
TOPIC = "Prior Period Items / Errors — Narration Keyword Check"
_PPI_KEYWORDS = (
    "prior period", "previous year", "py adjustment", "prior year adjustment",
    "earlier year", "last year adjustment", "rectification of prior",
)
_LEDGER_TYPES = ("GL", "JE")

# Framework-specific terminology — the whole point of this correction is
# that these are NOT interchangeable, so nothing here is hardcoded into
# a single wording string reused for both frameworks.
_FRAMEWORK_TERMS = {
    "AS": {
        "standard_name": "AS 5",
        "term_lower": "prior period item",
        "term_title": "Prior Period Item",
    },
    "IND_AS": {
        "standard_name": "Ind AS 8",
        "term_lower": "prior period error",
        "term_title": "Prior Period Error",
    },
}


def evaluate(engagement, dataset: dict[str, list], framework: str) -> RuleOutcome:
    terms = _FRAMEWORK_TERMS.get(framework, _FRAMEWORK_TERMS["AS"])
    rule_id = FRAMEWORK_RULE_IDS.get(framework, FRAMEWORK_RULE_IDS["AS"])
    outcome = RuleOutcome(rule_id=rule_id)

    rows_with_description = [
        row for t in _LEDGER_TYPES for row in dataset.get(t, [])
        if (row.values.get("description") or "").strip()
    ]
    if not rows_with_description:
        outcome.insufficient_data_reason = (
            "No validated General Ledger or Journal Entry row has a non-blank Description/Narration value for "
            "this engagement — a narration keyword check cannot be performed."
        )
        return outcome

    outcome.evaluated_count = len(rows_with_description)
    for row in rows_with_description:
        description = (row.values.get("description") or "").strip()
        matched = next((k for k in _PPI_KEYWORDS if k in description.lower()), None)
        if matched is None:
            continue

        amount = (row.values.get("debit_amount") or 0) + (row.values.get("credit_amount") or 0)
        outcome.exceptions.append(ExceptionDraft(
            label=wording.POTENTIAL_INCONSISTENCY,
            area=TOPIC,
            trigger_condition=f'Narration contains the keyword "{matched}": "{description}".',
            explanation=(
                f'An entry\'s narration ("{description}") contains language commonly associated with a '
                f"{terms['term_lower']} under {terms['standard_name']}. This is a plain keyword match on free "
                f"text — it does not confirm this is in fact a {terms['term_lower']}, nor its materiality or "
                f"disclosure/restatement treatment, if any."
            ),
            suggested_query=(
                f"Please confirm whether this entry represents a {terms['term_lower']} under {terms['standard_name']} "
                f"and, if so, how it was disclosed/treated in accordance with that standard."
            ),
            risk_level="LOW",
            data_sources=[str(row.file_id)],
            threshold_used={"matched_keyword": matched, "standard_name": terms["standard_name"]},
            amount_paise=amount or None,
            related_transaction_id=row.transaction_id,
        ))

    return outcome
