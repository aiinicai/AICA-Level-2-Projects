"""
Tax rule pack (Stage 10 — approved catalogue + implementation plan:
documentation/stage10_tax_rule_catalogue_proposal.md and
documentation/stage10_implementation_plan.md).

GATING REQUIREMENT (Blueprint Section 1.2 / Section 5, unchanged):
verification_status must be VERIFIED, backed by a primary-source
citation, before a rule executes — enforced in
`app/services/rule_runner_service.py`, not here. This registry alone
does not decide whether a rule is allowed to run; a rule_id missing
from `RULES` below can never run regardless of its DB row's status.

Every module here is 2-arg (`evaluate(engagement, dataset) ->
RuleOutcome`), NOT framework-gated — Income-tax law does not depend on
AS/Ind AS, the same reasoning Audit already established for SA-based
procedures (see app/rules/audit/__init__.py's docstring).

ACT-TRANSITION SCOPE (Decision 1, approved): every rule below is
verified and executable against the Income-tax Act, 1961 ONLY.
`app/services/tax_review_service.py` refuses to run any of these rules
at all for an engagement whose financial year falls under the (largely
unverified) Income-tax Act, 2025 — see `act_transition.py`. No module
here contains any Income-tax Act, 2025 logic.

The 9 rules below are exactly the set approved for Stage 10 coding
(Decision 2, plus TAX-MSME-013 per your follow-up approval) — no rule
beyond these 9 may be added without a further approval. Six additional
rules from the approved catalogue proposal remain gated
(SOURCE_VERIFICATION_REQUIRED or, for TAX-ACM-010, VERIFIED-but-
data-blocked) and are seeded as metadata only, with NO coded module —
see database/seed/seed_tax_rules.py.
"""
from __future__ import annotations

from app.rules.tax import (
    tax_aud_014, tax_cash_001, tax_cash_002, tax_dep_005, tax_dis_006,
    tax_gst_009, tax_loan_003, tax_msme_013, tax_rpt_004,
)

_RULE_MODULES = (
    tax_cash_001,
    tax_cash_002,
    tax_loan_003,
    tax_dis_006,
    tax_aud_014,
    tax_dep_005,
    tax_rpt_004,
    tax_gst_009,
    tax_msme_013,
)

RULES: dict[str, object] = {_module.RULE_ID: _module for _module in _RULE_MODULES}
