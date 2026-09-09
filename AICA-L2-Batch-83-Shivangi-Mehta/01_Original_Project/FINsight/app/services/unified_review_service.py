"""
Unified Review Engine orchestration (Stage 12).

This module is a THIN orchestration layer over the three already-approved,
already-implemented review engines (`accounting_review_service.py`,
`audit_review_service.py`, `tax_review_service.py`) — it contains no new
Accounting, Audit, or Tax rule logic, no modified thresholds, and no
modified applicability logic of its own. Every module's own precondition
(Accounting's `AccountingFrameworkNotSetError`, Tax's
`ActEraNotSupportedError`, both engines' `EngagementNotFoundError`) and
every module's own re-run/reviewer-preservation behavior is left exactly
as Stage 8/9/10 built it — this module calls each engine's existing
`preview_*_review()` / `run_*_review()` functions unchanged and never
recreates their applicability decisions or persistence logic (Stage 12
spec, sections 4 and 6).

Scope, fixed by the approved Stage 11 scope change and restated by the
Stage 12 instruction: exactly three modules, always, never SEBI.
`MODULES` below is the single place that set is defined — nothing in
this file, or in review_bp.py / the templates, ever imports or offers a
fourth option.

Two things this module DOES add, since neither existed anywhere in the
codebase before Stage 12 (both are new orchestration behavior, not new
rule content, and neither required a schema change — see the Stage 12
report for the schema evaluation):

  1. `check_review_readiness()` / the readiness gate inside `_execute()`
     — Stage 12 section 5's new precondition: a Unified Review must never
     execute against raw/unvalidated data. This is enforced ONLY here, at
     the orchestrator layer; `dataset_service.load_engagement_dataset()`
     (which already silently excludes non-VALIDATED files) and each
     individual engine's own screen are both left exactly as they were —
     a professional visiting Accounting/Audit/Tax directly still sees
     today's behavior (a live preview against whatever validated data
     exists, however partial). Only the unified "Run Review" workflow
     refuses to execute at all until every uploaded file for the
     engagement is VALIDATED, showing the exact required message.

  2. Finding normalization (`NormalizedFinding` / `get_unified_findings()`)
     — a read-only presentation envelope over the three engines'
     already-persisted `ExceptionRecord` rows (via their own
     `get_last_review_results()`), for the Unified Findings Centre. It
     does not alter, re-word, or re-score anything; every module-specific
     field the three engines already expose is preserved in
     `module_fields` rather than discarded to force a uniform shape.

Error isolation (Stage 12 section 17): every module in a run is executed
inside its own try/except in `_execute()`'s loop, so one module raising
(whether its own documented precondition, or a genuine bug) never
prevents the remaining selected modules from running, and never discards
a result a module already produced before it. `UnifiedReviewSummary`
always reports each module's own outcome individually — there is no
"all succeeded" flag that could be true while a module actually failed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services import (
    accounting_review_service,
    audit_review_service,
    engagement_service,
    rule_runner_service,
    tax_review_service,
    upload_service,
)

# The fixed FinSight V1 module set (Stage 11 scope change, restated by the
# Stage 12 instruction, section 3: "Do NOT include: SEBI Review as an
# active selectable option."). Order here is the display/execution order
# used everywhere else in this file.
MODULES = ("ACCOUNTING", "AUDIT", "TAX")

# Stage 12 section 5's exact required message — never reworded.
BLOCKED_MESSAGE = "Review cannot be started until the data mapping and validation are completed."


class EngagementNotFoundError(Exception):
    """Raised when a unified review or findings lookup is requested for
    an engagement_id that does not exist at all. Distinct from each
    individual engine's own EngagementNotFoundError class (those are
    still raised and caught per-module inside `_execute()`) — this one
    is raised for the orchestrator-level checks that run before any
    per-module call happens at all (the readiness gate, findings
    lookups)."""


# --- Readiness gate (Stage 12 section 5) ------------------------------------


@dataclass
class ReviewReadiness:
    ready: bool
    reason: str | None
    uploads: list  # every UploadedFile row for the engagement, for a per-file status table


def check_review_readiness(engagement_id: int) -> ReviewReadiness:
    """An engagement is ready for a Unified Review only once it has at
    least one uploaded file AND every uploaded file for it is
    VALIDATED. A mix of VALIDATED and not-yet-validated files blocks
    the whole review, not just the unfinished file — "the data mapping
    and validation are completed" reads as a statement about the
    engagement's data preparation as a whole, not a per-file partial
    state. This is a deliberate, disclosed design choice (Stage 12
    report), not implied by any single existing field."""
    uploads = upload_service.list_uploads(engagement_id)
    if not uploads:
        return ReviewReadiness(ready=False, reason=BLOCKED_MESSAGE, uploads=uploads)
    if any(u.upload_status != "VALIDATED" for u in uploads):
        return ReviewReadiness(ready=False, reason=BLOCKED_MESSAGE, uploads=uploads)
    return ReviewReadiness(ready=True, reason=None, uploads=uploads)


# --- Orchestration (preview / run) ------------------------------------------

_PRECONDITION_ERRORS = {
    "ACCOUNTING": (
        accounting_review_service.EngagementNotFoundError,
        accounting_review_service.AccountingFrameworkNotSetError,
    ),
    "AUDIT": (audit_review_service.EngagementNotFoundError,),
    "TAX": (tax_review_service.EngagementNotFoundError, tax_review_service.ActEraNotSupportedError),
}

_PREVIEW_FN = {
    "ACCOUNTING": accounting_review_service.preview_accounting_review,
    "AUDIT": audit_review_service.preview_audit_review,
    "TAX": tax_review_service.preview_tax_review,
}

_RUN_FN = {
    "ACCOUNTING": accounting_review_service.run_accounting_review,
    "AUDIT": audit_review_service.run_audit_review,
    "TAX": tax_review_service.run_tax_review,
}


def _normalize_modules(modules) -> tuple:
    """None (or falsy) -> every V1 module, the approved "all selected by
    default" behavior (Stage 12 section 3). Anything else is filtered
    against MODULES, silently dropping an unrecognized value (e.g. a
    stray "SEBI" in a hand-crafted POST) rather than erroring — the
    same "never a working SEBI option" guarantee MODULES itself gives,
    just defensive against a malformed request too. Order is always
    MODULES' own order, regardless of the input order."""
    if not modules:
        return MODULES
    selected = set(modules)
    return tuple(m for m in MODULES if m in selected)


@dataclass
class ModuleRunOutcome:
    module: str
    status: str  # COMPLETED / BLOCKED / FAILED
    result: object | None = None  # AccountingReviewResult / AuditReviewResult / TaxReviewResult
    error_message: str | None = None


@dataclass
class UnifiedReviewSummary:
    engagement_id: int
    executed: bool  # False if nothing ran at all (readiness gate, or no modules selected)
    blocked_reason: str | None
    requested_modules: tuple = ()
    module_outcomes: list = field(default_factory=list)  # list[ModuleRunOutcome]
    persisted: bool = False  # True for run_unified_review(), False for preview_unified_review()

    @property
    def any_failed(self) -> bool:
        return any(o.status == "FAILED" for o in self.module_outcomes)

    @property
    def any_blocked(self) -> bool:
        return any(o.status == "BLOCKED" for o in self.module_outcomes)

    @property
    def all_completed(self) -> bool:
        return bool(self.module_outcomes) and all(o.status == "COMPLETED" for o in self.module_outcomes)

    @property
    def total_persisted_exceptions(self) -> int:
        return sum(
            getattr(o.result, "persisted_exception_count", 0) or 0
            for o in self.module_outcomes if o.result is not None
        )

    @property
    def total_preserved_exceptions(self) -> int:
        return sum(
            getattr(o.result, "preserved_exception_count", 0) or 0
            for o in self.module_outcomes if o.result is not None
        )


def _execute(engagement_id: int, modules, *, persist: bool) -> UnifiedReviewSummary:
    engagement = engagement_service.get_engagement(engagement_id)
    if engagement is None:
        raise EngagementNotFoundError(f"No engagement found with engagement_id={engagement_id}.")

    selected = _normalize_modules(modules)
    if not selected:
        return UnifiedReviewSummary(
            engagement_id=engagement_id, executed=False,
            blocked_reason="No review modules were selected.", requested_modules=(), persisted=persist,
        )

    readiness = check_review_readiness(engagement_id)
    if not readiness.ready:
        return UnifiedReviewSummary(
            engagement_id=engagement_id, executed=False,
            blocked_reason=readiness.reason, requested_modules=selected, persisted=persist,
        )

    fn_map = _RUN_FN if persist else _PREVIEW_FN
    outcomes: list[ModuleRunOutcome] = []
    for module in selected:
        try:
            result = fn_map[module](engagement_id)
            outcomes.append(ModuleRunOutcome(module=module, status="COMPLETED", result=result))
        except _PRECONDITION_ERRORS[module] as exc:
            # A documented, expected precondition (e.g. no Entity Profile
            # yet, or an Act-era-unsupported financial year) — not a bug.
            # Reported distinctly from FAILED so the Result Summary can
            # say *why* this module didn't run, never just that it "failed".
            outcomes.append(ModuleRunOutcome(module=module, status="BLOCKED", error_message=str(exc)))
        except Exception as exc:  # noqa: BLE001 — error isolation (Stage 12 section 17): one module's
            # exception must never stop the loop or discard another module's already-collected result.
            outcomes.append(ModuleRunOutcome(module=module, status="FAILED", error_message=str(exc)))

    return UnifiedReviewSummary(
        engagement_id=engagement_id, executed=True, blocked_reason=None,
        requested_modules=selected, module_outcomes=outcomes, persisted=persist,
    )


def preview_unified_review(engagement_id: int, modules=None) -> UnifiedReviewSummary:
    """Read-only across every selected module — calls each engine's own
    `preview_*_review()`, which itself writes nothing. Still subject to
    the readiness gate: showing a "preview" built from data that isn't
    fully mapped/validated yet would be misleading on the one screen
    whose entire purpose is a single, trustworthy Run Review action."""
    return _execute(engagement_id, modules, persist=False)


def run_unified_review(engagement_id: int, modules=None) -> UnifiedReviewSummary:
    """Persists — calls each selected engine's own `run_*_review()`,
    which handles its own re-run/reviewer-preservation behavior
    unchanged (Stage 12 section 18): this function does not touch
    ExceptionRecord/QueryRecord directly at all."""
    return _execute(engagement_id, modules, persist=True)


# --- Finding normalization (Stage 12 sections 8, 9, 12, 13) -----------------


@dataclass
class NormalizedFinding:
    """The common envelope (Stage 12 section 9) plus `module_fields` for
    everything module-specific that must NOT be discarded or forced into
    uniform terminology (Accounting: framework/standard; Audit:
    area/assertions/suggested procedure; Tax: legislative act/AY). Every
    value here is read directly from an already-persisted ExceptionRecord
    / its rule catalogue row / its linked QueryRecord — nothing is
    computed or invented for display purposes."""
    module: str
    finding_id: int
    rule_id: str | None
    title: str
    risk_level: str | None
    status: str
    trigger_condition: str | None
    explanation: str | None
    reference: str | None
    suggested_query: str | None
    suggested_evidence: str | None
    data_sources: list | None
    related_transaction_id: int | None
    module_fields: dict
    raw_exception: object  # the underlying ExceptionRecord, for anything a template needs beyond the envelope


def _accounting_rules_by_id() -> dict:
    """rule_id -> AccountingRule, every row (mirrors
    tax_review_service.get_tax_rules_by_id() /
    audit_review_service.get_audit_rules_by_id() — accounting_review_
    service.py has no equivalent public helper of its own, so it's built
    here from the same rule_runner_service.list_all_accounting_rules()
    every other catalogue display already uses)."""
    return {row.rule_id: row for row in rule_runner_service.list_all_accounting_rules()}


def get_unified_findings(
    engagement_id: int, *, modules=None, status: str | None = None,
    risk_level: str | None = None, rule_id: str | None = None,
) -> list[NormalizedFinding]:
    """Every currently-persisted finding across the selected modules
    (default: all three), normalized for the Unified Findings Centre.
    Purely additive/read-only over each engine's own
    `get_last_review_results()` — no ExceptionRecord/QueryRecord is
    created, changed, or deleted here."""
    selected = _normalize_modules(modules)

    standards_by_id = rule_runner_service.get_standards_by_id()
    accounting_rules = _accounting_rules_by_id()
    audit_rules = audit_review_service.get_audit_rules_by_id()
    tax_rules = tax_review_service.get_tax_rules_by_id()

    findings: list[NormalizedFinding] = []

    if "ACCOUNTING" in selected:
        for item in accounting_review_service.get_last_review_results(engagement_id):
            rule = accounting_rules.get(item.exception.rule_id)
            standard = standards_by_id.get(rule.standard_id) if rule and rule.standard_id else None
            findings.append(NormalizedFinding(
                module="ACCOUNTING",
                finding_id=item.exception.exception_id,
                rule_id=item.exception.rule_id,
                title=rule.topic if rule else (item.exception.area or "Accounting Finding"),
                risk_level=item.exception.risk_level,
                status=item.exception.status,
                trigger_condition=item.exception.trigger_condition,
                explanation=item.exception.description,
                reference=item.exception.standard_reference,
                suggested_query=item.query.question_text if item.query else None,
                # Accounting's rule catalogue has no suggested_evidence column
                # (only Audit's does, per Stage 9 Decision A) — left None
                # rather than substituting a different field under the same
                # label, which would misrepresent what was actually recorded.
                suggested_evidence=None,
                data_sources=item.data_sources,
                related_transaction_id=item.exception.related_transaction_id,
                module_fields={
                    "framework": rule.framework if rule else None,
                    "standard_code": standard.code if standard else None,
                    "suggested_action": rule.suggested_action if rule else None,
                },
                raw_exception=item.exception,
            ))

    if "AUDIT" in selected:
        for item in audit_review_service.get_last_review_results(engagement_id):
            rule = audit_rules.get(item.exception.rule_id)
            findings.append(NormalizedFinding(
                module="AUDIT",
                finding_id=item.exception.exception_id,
                rule_id=item.exception.rule_id,
                title=rule.topic if rule else (item.exception.area or "Audit Finding"),
                risk_level=item.exception.risk_level,
                status=item.exception.status,
                trigger_condition=item.exception.trigger_condition,
                explanation=item.exception.description,
                reference=item.exception.standard_reference,
                suggested_query=item.query.question_text if item.query else None,
                suggested_evidence=rule.suggested_evidence if rule else None,
                data_sources=item.data_sources,
                related_transaction_id=item.exception.related_transaction_id,
                module_fields={
                    "audit_area": rule.audit_area if rule else None,
                    "assertions": item.assertions,
                    "suggested_audit_procedure": rule.suggested_audit_procedure if rule else None,
                },
                raw_exception=item.exception,
            ))

    if "TAX" in selected:
        for item in tax_review_service.get_last_review_results(engagement_id):
            rule = tax_rules.get(item.exception.rule_id)
            findings.append(NormalizedFinding(
                module="TAX",
                finding_id=item.exception.exception_id,
                rule_id=item.exception.rule_id,
                title=rule.topic if rule else (item.exception.area or "Tax Finding"),
                risk_level=item.exception.risk_level,
                status=item.exception.status,
                trigger_condition=item.exception.trigger_condition,
                explanation=item.exception.description,
                reference=item.exception.standard_reference,
                suggested_query=item.query.question_text if item.query else None,
                # Tax's rule catalogue also has no suggested_evidence column — see the Accounting note above.
                suggested_evidence=None,
                data_sources=item.data_sources,
                related_transaction_id=item.exception.related_transaction_id,
                module_fields={
                    "legislative_act": rule.legislative_act if rule else None,
                    "applicable_from_ay": rule.applicable_from_ay if rule else None,
                    "suggested_action": rule.suggested_action if rule else None,
                },
                raw_exception=item.exception,
            ))

    if status:
        findings = [f for f in findings if f.status == status]
    if risk_level:
        findings = [f for f in findings if f.risk_level == risk_level]
    if rule_id:
        findings = [f for f in findings if f.rule_id == rule_id]

    findings.sort(key=lambda f: (f.module, f.finding_id))
    return findings


def get_finding(engagement_id: int, module: str, finding_id: int) -> NormalizedFinding | None:
    """One finding by (module, finding_id) — the Finding Detail Page's
    lookup. Re-derives the full normalized list and filters, the same
    "recompute live, never cache" pattern every other read in this
    codebase already uses; findings tables are never large enough for
    this to matter offline."""
    for f in get_unified_findings(engagement_id, modules=(module,)):
        if f.finding_id == finding_id:
            return f
    return None


def group_findings_by_transaction(findings: list) -> dict:
    """Stage 12 section 10's "same transaction, multiple perspectives"
    grouping — keyed strictly off `related_transaction_id`, the one
    identifier the schema already carries for exactly this purpose. This
    deliberately does NOT fall back to a weaker proxy such as "these
    findings share a source file_id": findings from the same uploaded
    file are not necessarily the same transaction (a file can hold
    thousands of distinct transactions), and grouping by file overlap
    would misrepresent the review as showing transaction-level linkage
    it cannot actually support.

    Stage 19 activated this mechanism, exactly as this function's own
    prior note predicted it would with no further change here: a subset
    of single-row rule modules across all three engines now set
    `ExceptionDraft.related_transaction_id` (see `app/services/
    dataset_service.py`'s `attach_transaction_ids()`) — an aggregate/
    computed rule (a balance, a ratio, a period-level check) still
    deliberately never sets it, so this can still legitimately return
    an empty grouping for an engagement whose findings happen not to
    share a transaction, not only for one where nothing was ever
    populated."""
    groups: dict[int, list] = {}
    for f in findings:
        if f.related_transaction_id is not None:
            groups.setdefault(f.related_transaction_id, []).append(f)
    return {tx_id: items for tx_id, items in groups.items() if len(items) > 1}


def unified_dashboard_summary(engagement_id: int) -> dict:
    """Stage 12 section 11's Unified Dashboard/Review Summary numbers:
    total findings, a per-module count, and a risk-level distribution
    built ONLY from risk levels that actually appear on a persisted
    finding — never a fixed/invented LOW..CRITICAL scaffold with zeros
    papered in for a level nothing used."""
    findings = get_unified_findings(engagement_id)
    per_module = {m: 0 for m in MODULES}
    per_risk_level: dict[str, int] = {}
    for f in findings:
        per_module[f.module] = per_module.get(f.module, 0) + 1
        if f.risk_level:
            per_risk_level[f.risk_level] = per_risk_level.get(f.risk_level, 0) + 1
    return {
        "total_findings": len(findings),
        "per_module": per_module,
        "per_risk_level": per_risk_level,
    }
