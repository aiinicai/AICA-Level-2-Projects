"""
AS2-INV-003 / INDAS2-INV-003 — Inventory Valuation Method.

Framework: AS 2 (Valuation of Inventories) / Ind AS 2 (Inventories).

What data is required to genuinely test this: the valuation method
actually applied to inventory (e.g. FIFO / Weighted Average / Standard
Cost) and, ideally, a cost-vs-net-realizable-value comparison per
inventory item or category.
What can actually be established from the approved schema: nothing.
There is no "INVENTORY" file type, and no canonical field anywhere in
`app/mapping/column_mapper.py::CANONICAL_FIELDS` captures a valuation
method, cost basis, or net realizable value — not on the ledger-style
fields (TB/GL/JE/SALES/PURCHASE/BANK/AR/AP) and not on FixedAsset/
GstLineItem/TdsLineItem either.
What cannot be established: everything this rule would need to test.

This rule therefore always reports Insufficient Data. Stage 8 Round 2
(correction #9) downgraded it to `is_active=False` — "Future /
Insufficient Data / Not currently executable" in the catalogue, rather
than an active rule that can only ever report Insufficient Data — per
the instruction not to activate rules merely to reach a rule count.
The catalogue entry is kept (not removed) so it is honest about what
AS 2/Ind AS 2 coverage does and does not exist today. If a future stage
adds an INVENTORY file type with a valuation-method field, this rule
should be redesigned and reactivated — not this text quietly
reinterpreted.
"""
from __future__ import annotations

from app.rules.base_rule import RuleOutcome

FRAMEWORK_RULE_IDS = {"AS": "AS2-INV-003", "IND_AS": "INDAS2-INV-003"}
TOPIC = "Inventory Valuation Method"


def evaluate(engagement, dataset: dict[str, list], framework: str) -> RuleOutcome:
    rule_id = FRAMEWORK_RULE_IDS.get(framework, FRAMEWORK_RULE_IDS["AS"])
    outcome = RuleOutcome(rule_id=rule_id)
    outcome.insufficient_data_reason = (
        "No file type or mapped field in the current FinSight schema captures the inventory valuation method, "
        "cost basis, or net realizable value comparison (no \"INVENTORY\" dataset type, and no canonical field for "
        "any of these exists). This rule cannot be evaluated against the uploaded data and is reported here as "
        "Insufficient Data rather than being silently omitted from the review."
    )
    return outcome
