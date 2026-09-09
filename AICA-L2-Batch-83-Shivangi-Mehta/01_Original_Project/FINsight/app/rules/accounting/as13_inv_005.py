"""
AS13-INV-005 / INDAS109-INV-005 — Investment Valuation & Classification.

Framework: AS 13 (Accounting for Investments) / Ind AS 109 (Financial
Instruments). Flagged explicitly (verification research, Stage 8 Round
2): this is NOT a clean 1:1 mapping. AS 13 covers only investments
(current/long-term classification, cost-vs-lower-of-cost-or-fair-value,
"diminution other than temporary" impairment). Ind AS 109 is far
broader — all financial instruments, using a business-model/contractual-
cash-flow classification test (amortized cost / FVTPL / FVOCI) and an
expected-credit-loss impairment model — and a slice of what AS 13
covered (investment property specifically) is carved out under Ind AS
into a separate standard, Ind AS 40. This rule targets the general
investment-valuation question common to both; it does not claim AS 13
and Ind AS 109 are scope-equivalent.

What data is required to genuinely test this: an investment-
classification field (current/long-term under AS 13, or the Ind AS 109
categories — amortized cost/FVTPL/FVOCI) and a fair-value/market-value
figure to compare against carrying value.
What can actually be established from the approved schema: nothing. No
"INVESTMENTS" file type exists, and no canonical field anywhere in
`app/mapping/column_mapper.py::CANONICAL_FIELDS` captures an investment
classification or a fair-value figure.
What cannot be established: everything this rule would need to test.

Like AS2-INV-003, this rule always reports Insufficient Data. Stage 8
Round 2 (correction #9) downgraded it to `is_active=False` — "Future /
Insufficient Data / Not currently executable" — rather than an active
rule that can only ever report Insufficient Data. If a future stage
adds an INVESTMENTS file type with classification and fair-value
fields, this rule should be redesigned and reactivated against that
real data.
"""
from __future__ import annotations

from app.rules.base_rule import RuleOutcome

FRAMEWORK_RULE_IDS = {"AS": "AS13-INV-005", "IND_AS": "INDAS109-INV-005"}
TOPIC = "Investment Valuation & Classification"


def evaluate(engagement, dataset: dict[str, list], framework: str) -> RuleOutcome:
    rule_id = FRAMEWORK_RULE_IDS.get(framework, FRAMEWORK_RULE_IDS["AS"])
    outcome = RuleOutcome(rule_id=rule_id)
    outcome.insufficient_data_reason = (
        "No file type or mapped field in the current FinSight schema captures investment classification "
        "(current/long-term, or amortized cost/FVTPL/FVOCI) or a fair-value figure to compare against carrying "
        "value (no \"INVESTMENTS\" dataset type, and no canonical field for either exists). This rule cannot be "
        "evaluated against the uploaded data and is reported here as Insufficient Data rather than being silently "
        "omitted from the review."
    )
    return outcome
