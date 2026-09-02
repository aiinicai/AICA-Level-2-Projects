"""
Accounting rule pack registry (Blueprint Section 1.1: Accounting ==
framework-treatment questions only).

Every module listed in `_RULE_MODULES` exposes exactly three names:
`FRAMEWORK_RULE_IDS` (dict, `{"AS": "<rule_id>", "IND_AS": "<rule_id>"}`
— one module, two catalogue identities, since Stage 8 Round 2's
framework-aware redesign requires "a rule must never produce an Ind AS
reference for an AS engagement," which means one `AccountingRule` row
per framework, not one row serving both), `TOPIC` (str), and
`evaluate(engagement, dataset, framework) -> RuleOutcome`.

This module builds `RULES`, a `rule_id -> module` map, by importing
each module explicitly (not a directory-scan auto-import) and
registering BOTH of its framework-specific rule_ids against it, so
adding a rule is a visible, one-line change here rather than an
implicit side effect of dropping a file into this folder.

`app/services/rule_runner_service.py` is the only place a rule_id from
this map actually executes, and it independently re-checks that the
`AccountingRule` DB row's own `framework` matches the engagement's
framework before calling in — this registry alone does not decide
which rule runs for which engagement, it only says which module a
rule_id's logic lives in.

7 rule families (14 catalogue rows: one AS + one Ind AS row each) are
active. `AS2-INV-003`/`INDAS2-INV-003`, `AS13-INV-005`/
`INDAS109-INV-005`, and `AS15-EB-008`/`INDAS19-EB-008` remain coded
here (so a future stage can reactivate them without a rewrite) but are
seeded `is_active=False` — "Future / Insufficient Data / Not currently
executable" — per Stage 8 Round 2 correction #9 ("only strong rules
should be active... do not activate rules merely to reach a rule
count"). `AS6-DEP-002` (correction #2 — AS 6 was withdrawn by ICAI and
folded into AS 10) has no module at all; it exists only as a withdrawn/
superseded marker row in the seed data and must never execute. An 8th
candidate family, Foreign Exchange Restatement (AS11-FX-007), remains
excluded entirely pending a schema-change decision — see the Stage 8
report.
"""
from __future__ import annotations

from app.rules.accounting import (
    as2_inv_003, as10_dep_002, as10_fa_001, as13_inv_005, as15_eb_008,
    as16_bc_006, as18_rpt_009, as26_int_011, as29_prov_010, gen_ppi_012,
)

_RULE_MODULES = (
    as10_fa_001,
    as26_int_011,
    as10_dep_002,
    as29_prov_010,
    as16_bc_006,
    as18_rpt_009,
    gen_ppi_012,
    as2_inv_003,
    as13_inv_005,
    as15_eb_008,
)

RULES: dict[str, object] = {}
for _module in _RULE_MODULES:
    for _rule_id in _module.FRAMEWORK_RULE_IDS.values():
        RULES[_rule_id] = _module
