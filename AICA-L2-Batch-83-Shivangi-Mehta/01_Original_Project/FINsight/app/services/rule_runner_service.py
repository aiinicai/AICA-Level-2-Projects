"""
Rule execution gating (Blueprint Section 1.2: "verification gating as a
structural control" — a rule pack's `rule_runner_service` must refuse to
execute or display any rule whose `verification_status != VERIFIED`,
uniformly, regardless of module).

This is the ONLY place that decides whether a rule actually runs.
`app/rules/accounting/__init__.py::RULES` is pure code (every rule
module the codebase ships with); the `accounting_rules` DB table is
metadata + the gate (`is_active`, `verification_status`, `framework`) a
reviewer or the seed script controls. A rule must be present in BOTH —
coded AND marked active+verified in the DB — before it ever runs. A
rule_id that exists in one but not the other is silently excluded from
execution, never an error, since the two are allowed to be seeded/
deployed on independent schedules.

Stage 8 Round 2 correction #1 (framework-aware execution — "AS
engagement -> AS rules, IND_AS engagement -> Ind AS rules; a rule must
never produce an Ind AS reference for an AS engagement") is enforced
HERE, in the runner/metadata layer, not inside individual rule modules:
`get_runnable_accounting_rules()` takes the engagement's framework and
filters `AccountingRule.framework` against it, and `run_accounting_rule()`
independently re-checks the same match before calling in, and then
FORCIBLY overwrites whatever `rule_id` the module itself returned with
the DB row's own `rule_id` — so even a bug inside a rule module can
never cause a mismatched framework's rule_id (and, downstream, a
mismatched Standard reference — see `accounting_review_service.py`,
which always looks up the Standard via the DB row's own `standard_id`,
never via anything the module says) to leak into a finding.
"""
from __future__ import annotations

from sqlalchemy import select

from app import extensions
from app.models.rules import AccountingRule, AuditRule, Standard, TaxRule
from app.rules import wording
from app.rules.accounting import RULES
from app.rules.audit import RULES as AUDIT_RULES
from app.rules.base_rule import RuleOutcome
from app.rules.tax import RULES as TAX_RULES


def _session():
    """See engagement_service._session()'s docstring — same reasoning."""
    return extensions.SessionLocal


def get_standards_by_id() -> dict[int, Standard]:
    """standard_id -> Standard, for joining the catalogue display to
    each rule's Source/Framework/Standard columns without a relationship
    traversal (the sandbox ORM shim doesn't support one — see
    orm_shim.py's docstring — and the real app deliberately mirrors that
    same explicit-select style throughout, per engagement_service.py's
    own precedent)."""
    stmt = select(Standard)
    return {s.standard_id: s for s in _session().scalars(stmt).all()}


def list_all_accounting_rules() -> list[AccountingRule]:
    """Every AccountingRule row regardless of gating state or framework
    — used only for the read-only catalogue display (Rule ID/Framework/
    Standard/Topic/Active/Verification/etc.), never for execution.
    Execution always goes through `get_runnable_accounting_rules()`
    below, which additionally requires a specific `framework`."""
    stmt = select(AccountingRule).order_by(AccountingRule.rule_id)
    return list(_session().scalars(stmt).all())


def get_runnable_accounting_rules(framework: str) -> list[AccountingRule]:
    """Every AccountingRule row that is (a) marked runnable in the DB
    (is_active=True, verification_status="VERIFIED"), (b) has a
    matching coded module in RULES, AND (c) belongs to the requested
    `framework` ("AS" or "IND_AS") — the framework-aware gate from
    Stage 8 Round 2 correction #1. A rule seeded under the wrong
    framework, or an engagement whose framework doesn't match, simply
    never appears here; there is no cross-framework fallback. Ordered
    by rule_id for stable, reproducible report ordering."""
    stmt = (
        select(AccountingRule)
        .where(AccountingRule.is_active == True, AccountingRule.framework == framework)  # noqa: E712 — sandbox ORM shim doesn't support .is_(True)
        .order_by(AccountingRule.rule_id)
    )
    rows = list(_session().scalars(stmt).all())
    return [row for row in rows if row.verification_status == "VERIFIED" and row.rule_id in RULES]


def run_accounting_rule(rule_row: AccountingRule, engagement, dataset: dict[str, list], framework: str) -> RuleOutcome:
    """Runs exactly one gated rule. Callers should only ever pass a row
    that already came from `get_runnable_accounting_rules(framework)` —
    this function re-checks every part of the gate defensively anyway,
    since "never execute an unverified rule" and "never run an AS rule
    for an Ind AS engagement (or vice versa)" are structural controls,
    not courtesies. The module's own returned `outcome.rule_id` is
    always overwritten with `rule_row.rule_id` afterward — the DB row,
    not the module, is the single source of truth for which identity a
    finding is reported under."""
    if rule_row.verification_status != "VERIFIED":
        raise ValueError(
            f"Refusing to run rule {rule_row.rule_id!r}: verification_status is "
            f"{rule_row.verification_status!r}, not VERIFIED."
        )
    if not rule_row.is_active:
        raise ValueError(f"Refusing to run rule {rule_row.rule_id!r}: is_active is False.")
    if rule_row.framework != framework:
        raise ValueError(
            f"Refusing to run rule {rule_row.rule_id!r} (framework={rule_row.framework!r}) against an "
            f"engagement on framework {framework!r} — a rule must never run outside its own framework."
        )
    module = RULES.get(rule_row.rule_id)
    if module is None:
        raise ValueError(f"No coded rule module found for rule_id {rule_row.rule_id!r}.")
    outcome = module.evaluate(engagement, dataset, framework)
    outcome.rule_id = rule_row.rule_id  # authoritative override — never trust the module's self-reported id
    return outcome


def run_all_accounting_rules(engagement, dataset: dict[str, list], framework: str) -> dict[str, RuleOutcome]:
    """rule_id -> RuleOutcome, for every gated-runnable accounting rule
    on the given `framework`. A rule whose own evaluate() raises is not
    swallowed — the Stage 8 scope has no requirement to keep the review
    running past a genuine bug in one rule, and silently dropping a
    failed rule's outcome would misrepresent the review as complete
    when it wasn't."""
    return {
        rule_row.rule_id: run_accounting_rule(rule_row, engagement, dataset, framework)
        for rule_row in get_runnable_accounting_rules(framework)
    }


# --- Stage 9: Audit rule gating. Deliberately NOT framework-gated (SA-
# based procedures apply regardless of AS/Ind AS) — the mirror-image
# functions above take a `framework` parameter throughout; these do not,
# by design (see app/rules/audit/__init__.py's docstring). ---


def list_all_audit_rules() -> list[AuditRule]:
    """Every AuditRule row regardless of gating state — used only for
    the read-only catalogue display, never for execution. Execution
    always goes through `get_runnable_audit_rules()` below."""
    stmt = select(AuditRule).order_by(AuditRule.rule_id)
    return list(_session().scalars(stmt).all())


def get_runnable_audit_rules() -> list[AuditRule]:
    """Every AuditRule row that is (a) marked runnable in the DB
    (is_active=True, verification_status="VERIFIED") AND (b) has a
    matching coded module in AUDIT_RULES. No framework dimension —
    Audit rules run for every engagement regardless of AS/Ind AS.
    Ordered by rule_id for stable, reproducible report ordering."""
    stmt = (
        select(AuditRule)
        .where(AuditRule.is_active == True)  # noqa: E712 — sandbox ORM shim doesn't support .is_(True)
        .order_by(AuditRule.rule_id)
    )
    rows = list(_session().scalars(stmt).all())
    return [row for row in rows if row.verification_status == "VERIFIED" and row.rule_id in AUDIT_RULES]


def run_audit_rule(rule_row: AuditRule, engagement, dataset: dict[str, list]) -> RuleOutcome:
    """Runs exactly one gated audit rule. Callers should only ever pass
    a row that already came from `get_runnable_audit_rules()` — this
    function re-checks the gate defensively anyway, the same
    "structural control, not a courtesy" approach `run_accounting_rule()`
    uses above. Two additional checks beyond the Accounting mirror,
    both structural per Stage 9's own requirements:
    (1) every `ExceptionDraft.label` the module returns must be a
    member of `wording.AUDIT_LABELS` — an audit module must never use
    an Accounting-only label (`Potential Accounting Exception` /
    `Potential Inconsistency`) even by accident, so this is enforced
    here rather than left to each module's own discipline;
    (2) the module's own returned `outcome.rule_id` is always
    overwritten with `rule_row.rule_id` afterward, same authoritative-
    override pattern as `run_accounting_rule()`."""
    if rule_row.verification_status != "VERIFIED":
        raise ValueError(
            f"Refusing to run rule {rule_row.rule_id!r}: verification_status is "
            f"{rule_row.verification_status!r}, not VERIFIED."
        )
    if not rule_row.is_active:
        raise ValueError(f"Refusing to run rule {rule_row.rule_id!r}: is_active is False.")
    module = AUDIT_RULES.get(rule_row.rule_id)
    if module is None:
        raise ValueError(f"No coded audit rule module found for rule_id {rule_row.rule_id!r}.")
    outcome = module.evaluate(engagement, dataset)
    for draft in outcome.exceptions:
        if draft.label not in wording.AUDIT_LABELS:
            raise ValueError(
                f"Audit rule {rule_row.rule_id!r} produced a finding with label {draft.label!r}, which is not "
                f"one of the permitted audit labels {wording.AUDIT_LABELS!r}."
            )
    outcome.rule_id = rule_row.rule_id  # authoritative override — never trust the module's self-reported id
    return outcome


def run_all_audit_rules(engagement, dataset: dict[str, list]) -> dict[str, RuleOutcome]:
    """rule_id -> RuleOutcome, for every gated-runnable audit rule. A
    rule whose own evaluate() raises is not swallowed — same reasoning
    as `run_all_accounting_rules()` above."""
    return {
        rule_row.rule_id: run_audit_rule(rule_row, engagement, dataset)
        for rule_row in get_runnable_audit_rules()
    }


# --- Stage 10: Tax rule gating. Same shape as Audit's gating above
# (not framework-gated; Income-tax law doesn't depend on AS/Ind AS) —
# with ONE addition specific to Tax: `run_tax_rule()` enforces
# `wording.TAX_LABELS` the same structural way `run_audit_rule()`
# enforces `AUDIT_LABELS`. The Act-transition precondition (Decision 1
# — only FY governed by the Income-tax Act, 1961 may run any Tax rule
# at all) is NOT enforced here — it is an engagement-level precondition
# checked once by `app/services/tax_review_service.py` before any of
# these functions are ever called, the same layering
# `accounting_review_service.py` already uses for its own
# AccountingFrameworkNotSetError precondition. ---


def list_all_tax_rules() -> list[TaxRule]:
    """Every TaxRule row regardless of gating state — used only for the
    read-only catalogue display (which must show all 15 proposed rules,
    executable and gated alike, per the approved Stage 10 plan), never
    for execution. Execution always goes through
    `get_runnable_tax_rules()` below."""
    stmt = select(TaxRule).order_by(TaxRule.rule_id)
    return list(_session().scalars(stmt).all())


def get_runnable_tax_rules() -> list[TaxRule]:
    """Every TaxRule row that is (a) marked runnable in the DB
    (is_active=True, verification_status="VERIFIED") AND (b) has a
    matching coded module in TAX_RULES. A row can be VERIFIED (its
    legal citation is genuinely primary-sourced, e.g. TAX-ACM-010) and
    still never appear here if is_active=False or it has no coded
    module — the approved Stage 10 distinction between "law unverified"
    and "law fine, not yet executable" (see the implementation plan,
    Section 2). No framework dimension, same reasoning as Audit."""
    stmt = (
        select(TaxRule)
        .where(TaxRule.is_active == True)  # noqa: E712 — sandbox ORM shim doesn't support .is_(True)
        .order_by(TaxRule.rule_id)
    )
    rows = list(_session().scalars(stmt).all())
    return [row for row in rows if row.verification_status == "VERIFIED" and row.rule_id in TAX_RULES]


def run_tax_rule(rule_row: TaxRule, engagement, dataset: dict[str, list]) -> RuleOutcome:
    """Runs exactly one gated tax rule. Callers should only ever pass a
    row that already came from `get_runnable_tax_rules()` — this
    function re-checks the gate defensively anyway, the same
    "structural control, not a courtesy" approach every other
    run_*_rule() in this file uses. One check beyond the Audit mirror,
    per Stage 10's approved wording requirement: every
    `ExceptionDraft.label` the module returns must be a member of
    `wording.TAX_LABELS` — a tax module must never use an Accounting or
    Audit label, and must never imply a disallowance/violation is
    confirmed via a label outside this approved vocabulary. Same
    authoritative-override pattern as the other run_*_rule() functions:
    the module's own returned `outcome.rule_id` is always overwritten
    with `rule_row.rule_id` afterward."""
    if rule_row.verification_status != "VERIFIED":
        raise ValueError(
            f"Refusing to run rule {rule_row.rule_id!r}: verification_status is "
            f"{rule_row.verification_status!r}, not VERIFIED."
        )
    if not rule_row.is_active:
        raise ValueError(f"Refusing to run rule {rule_row.rule_id!r}: is_active is False.")
    module = TAX_RULES.get(rule_row.rule_id)
    if module is None:
        raise ValueError(f"No coded tax rule module found for rule_id {rule_row.rule_id!r}.")
    outcome = module.evaluate(engagement, dataset)
    for draft in outcome.exceptions:
        if draft.label not in wording.TAX_LABELS:
            raise ValueError(
                f"Tax rule {rule_row.rule_id!r} produced a finding with label {draft.label!r}, which is not one "
                f"of the permitted tax labels {wording.TAX_LABELS!r}."
            )
    outcome.rule_id = rule_row.rule_id  # authoritative override — never trust the module's self-reported id
    return outcome


def run_all_tax_rules(engagement, dataset: dict[str, list]) -> dict[str, RuleOutcome]:
    """rule_id -> RuleOutcome, for every gated-runnable tax rule. A rule
    whose own evaluate() raises is not swallowed — same reasoning as
    every other run_all_*_rules() in this file. Callers (tax_review_
    service.py) are responsible for the Act-transition precondition
    check BEFORE calling this — this function does not itself know
    about financial years or the Income-tax Act, 2025 at all."""
    return {
        rule_row.rule_id: run_tax_rule(rule_row, engagement, dataset)
        for rule_row in get_runnable_tax_rules()
    }
