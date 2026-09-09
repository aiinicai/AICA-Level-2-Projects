"""
Audit rule pack registry (Blueprint Section 1.1: Audit == risk
indicators/assertions/procedures only — never a framework-treatment
conclusion; kept conceptually and structurally separate from
Accounting throughout Stage 9).

Every module listed in `_RULE_MODULES` exposes exactly three names:
`RULE_ID` (str — one module, one catalogue identity; unlike Accounting,
Audit is NOT framework-gated, so there is no per-framework dict here —
SA-based procedures apply regardless of whether the engagement is on
AS or Ind AS), `TOPIC` (str), and `evaluate(engagement, dataset) ->
RuleOutcome` (2-arg — no `framework` parameter, deliberately, for the
same reason).

This module builds `RULES`, a `rule_id -> module` map, by importing
each module explicitly (not a directory-scan auto-import), so adding a
rule is a visible, one-line change here rather than an implicit side
effect of dropping a file into this folder — mirrors
`app/rules/accounting/__init__.py`'s own registry pattern.

`app/services/rule_runner_service.py` is the only place a rule_id from
this map actually executes, and it independently re-checks the
`AuditRule` DB row's own `is_active`/`verification_status` gate before
calling in, and enforces that every `ExceptionDraft.label` an audit
module returns is one of `wording.AUDIT_LABELS` — this registry alone
does not decide whether a rule is allowed to run, only which module a
rule_id's logic lives in.

The original 13 rules approved in the Stage 9 catalogue review were
active here under a standing cap ("no rule beyond these 13 without a
further approval"). That further approval was given explicitly (the
user's own instruction accompanying this pack: "add these above
mentioned ledger scrutiny checks"), adding a second "Ledger Scrutiny"
pack (originally AUD-LS-001 through AUD-LS-013), adapted from a
user-provided ledger-scrutiny prototype with 2 of its original 15
checks excluded as duplicates of existing rules (see
`ledger_scrutiny_shared.py`'s module docstring for the full disclosure).

Stage 21 revision (explicitly approved): AUD-LS-008 ("Month-End
Transaction") was retired at the user's request — the user judged
month-end flagging too noisy/low-value next to the equivalent, higher-
stakes year-end check (AUD-LS-009), which is unchanged and remains
active. **The rule_id AUD-LS-008 is retired, not reused** — a future
rule is never given this number, so an old exported working paper or
audit-log entry that cites "AUD-LS-008" is never misread as referring
to a different, later check. 25 rules are active here in total (the
original 13 plus 12 remaining Ledger Scrutiny rules). Any rule beyond
these 25 still requires a further explicit approval before being
added.
"""
from __future__ import annotations

from app.rules.audit import (
    aud_acc_004, aud_cash_010, aud_cut_013, aud_est_009, aud_je_001,
    aud_je_002, aud_je_003, aud_lob_012, aud_ls_001, aud_ls_002,
    aud_ls_003, aud_ls_004, aud_ls_005, aud_ls_006, aud_ls_007,
    aud_ls_009, aud_ls_010, aud_ls_011, aud_ls_012,
    aud_ls_013, aud_mov_005, aud_rev_008, aud_rpt_006, aud_sub_007,
    aud_wo_011,
)

_RULE_MODULES = (
    aud_je_001,
    aud_je_002,
    aud_je_003,
    aud_acc_004,
    aud_mov_005,
    aud_rpt_006,
    aud_sub_007,
    aud_rev_008,
    aud_est_009,
    aud_cash_010,
    aud_wo_011,
    aud_lob_012,
    aud_cut_013,
    aud_ls_001,
    aud_ls_002,
    aud_ls_003,
    aud_ls_004,
    aud_ls_005,
    aud_ls_006,
    aud_ls_007,
    # aud_ls_008 (Month-End Transaction) retired — see docstring above.
    aud_ls_009,
    aud_ls_010,
    aud_ls_011,
    aud_ls_012,
    aud_ls_013,
)

RULES: dict[str, object] = {_module.RULE_ID: _module for _module in _RULE_MODULES}
