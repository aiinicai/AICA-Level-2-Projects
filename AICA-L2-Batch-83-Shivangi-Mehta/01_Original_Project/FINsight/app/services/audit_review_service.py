"""
Audit Review orchestration (Stage 9): ties `dataset_service` (validated
+ confirmed data only) to `rule_runner_service` (gated audit-rule
execution) and persists results as `ExceptionRecord` + linked
`QueryRecord` rows, module="AUDIT" — reusing the exact schema approved
since Stage 3 (plus the Stage 9 Decision A `suggested_evidence` column
on `AuditRule`), no other new table or field.

Mirrors `accounting_review_service.py`'s two-entry-point pattern
(`preview_audit_review()` read-only / `run_audit_review()` persists)
and its re-run preservation behavior (untouched, freshly-auto-generated
AUDIT exceptions are cleared before a new batch is inserted; anything a
reviewer has started working on is left exactly as it is) — with three
deliberate differences from the Accounting version:

  1. No framework precondition. Audit rules are not framework-gated
     (Stage 9 design — SA-based procedures apply regardless of AS/Ind
     AS), so there is no `AccountingFrameworkNotSetError` equivalent
     here and no Entity Profile lookup at all.
  2. `standard_reference` is populated from `AuditRule.related_sa`
     (free text, e.g. "SA 240, SA 330") rather than a single `Standard`
     row's `source_reference` — Stage 9's disclosed design decision,
     since a single `standard_id` FK cannot cleanly hold a multi-SA
     citation. One `Standard` row per distinct SA (framework="SA")
     still exists for catalogue-display join purposes; `standard_id` on
     the `AuditRule` row itself is set to the primary/first-listed SA
     only (see `database/seed/seed_audit_rules.py`).
  3. `assertions_snapshot` (JSON list of assertion codes, e.g.
     `["OCCURRENCE", "CUT_OFF"]`) is populated per exception at persist
     time via the `AuditRuleAssertion` junction — a field that already
     existed on `ExceptionRecord` (Blueprint Section 2.12), unused until
     now since Accounting exceptions never populate it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select

from app import extensions
from app.models.exceptions import ExceptionRecord
from app.models.queries import QueryRecord, QueryResponse
from app.models.rules import AuditAssertion, AuditRule, AuditRuleAssertion
from app.rules.base_rule import RuleOutcome
from app.services import dataset_service, engagement_service, rule_runner_service


def _session():
    """See engagement_service._session()'s docstring — same reasoning."""
    return extensions.SessionLocal


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class EngagementNotFoundError(Exception):
    """Raised when an audit review is requested for an engagement_id
    that does not exist."""


@dataclass
class AuditReviewResult:
    engagement_id: int
    rule_outcomes: dict[str, RuleOutcome] = field(default_factory=dict)
    persisted_exception_count: int = 0
    preserved_exception_count: int = 0  # reviewer-touched rows left alone on a run() call; 0 for preview()


@dataclass
class PersistedAuditException:
    """One ExceptionRecord + its linked QueryRecord (if any), with the
    JSON-string columns already parsed back into plain dict/list, for
    templates to render without doing their own json.loads(). Mirrors
    accounting_review_service.PersistedException, plus `assertions`
    (parsed from assertions_snapshot) since Audit is the only module
    that populates that field."""
    exception: ExceptionRecord
    query: QueryRecord | None
    threshold_used: dict | None
    data_sources: list | None
    assertions: list | None


def _assertion_codes_by_rule_id() -> dict[str, list[str]]:
    """rule_id -> [assertion codes], via the AuditRuleAssertion junction
    — computed live each call (same "recompute live, never cache"
    pattern used throughout the codebase), not stored anywhere except
    the persisted snapshot this function feeds. Deliberately two plain
    single-model selects joined in Python, not a SQL join — the sandbox
    ORM shim supports neither multi-column select() nor .join()
    (confirmed the hard way; see rule_runner_service.get_standards_by_id()'s
    own docstring for the same "explicit select, no relationship
    traversal" precedent this follows)."""
    assertions_by_id = {a.assertion_id: a.code for a in _session().scalars(select(AuditAssertion)).all()}
    result: dict[str, list[str]] = {}
    for link in _session().scalars(select(AuditRuleAssertion)).all():
        code = assertions_by_id.get(link.assertion_id)
        if code is not None:
            result.setdefault(link.rule_id, []).append(code)
    return result


def _compute_outcomes(
    engagement_id: int, *, persist_transactions: bool = False,
) -> tuple[object, dict[str, list], dict[str, RuleOutcome]]:
    """See accounting_review_service.py's `_compute_outcomes()` for why
    `persist_transactions` exists and why only `run_audit_review()`
    passes True — `preview_audit_review()` must stay fully read-only."""
    engagement = engagement_service.get_engagement(engagement_id)
    if engagement is None:
        raise EngagementNotFoundError(f"No engagement found with engagement_id={engagement_id}.")

    dataset = dataset_service.load_engagement_dataset(engagement_id)
    if persist_transactions:
        dataset_service.attach_transaction_ids(engagement_id, dataset)
    outcomes = rule_runner_service.run_all_audit_rules(engagement, dataset)
    return engagement, dataset, outcomes


def preview_audit_review(engagement_id: int) -> AuditReviewResult:
    """Read-only. Computes every gated-runnable audit rule's outcome
    against this engagement's current validated + confirmed data, and
    returns it without touching the database at all."""
    _engagement, _dataset, outcomes = _compute_outcomes(engagement_id)
    return AuditReviewResult(engagement_id=engagement_id, rule_outcomes=outcomes)


def _clear_stale_automated_exceptions(engagement_id: int) -> int:
    stmt = select(ExceptionRecord).where(
        ExceptionRecord.engagement_id == engagement_id,
        ExceptionRecord.module == "AUDIT",
    )
    cleared = 0
    for exc in list(_session().scalars(stmt).all()):
        if exc.status != "OPEN" or exc.reviewer_notes or exc.status_reason:
            continue  # a reviewer has started working on this — preserve it, never delete or duplicate it

        q_stmt = select(QueryRecord).where(QueryRecord.exception_id == exc.exception_id)
        linked_queries = list(_session().scalars(q_stmt).all())
        has_response = False
        for q in linked_queries:
            r_stmt = select(QueryResponse).where(QueryResponse.query_id == q.query_id)
            if _session().scalars(r_stmt).first() is not None:
                has_response = True
                break
        if has_response:
            continue  # a management response exists against this exception's query — preserve it

        for q in linked_queries:
            _session().delete(q)
        _session().delete(exc)
        cleared += 1

    _session().commit()
    return cleared


def _preserved_finding_keys(engagement_id: int) -> set[tuple[str, str]]:
    """(rule_id, trigger_condition) for every AUDIT exception still on
    file for this engagement — same purpose as
    accounting_review_service._preserved_finding_keys()."""
    stmt = select(ExceptionRecord).where(
        ExceptionRecord.engagement_id == engagement_id, ExceptionRecord.module == "AUDIT",
    )
    return {
        (exc.rule_id, exc.trigger_condition)
        for exc in _session().scalars(stmt).all()
        if exc.rule_id is not None
    }


def _count_all_audit_exceptions(engagement_id: int) -> int:
    stmt = select(ExceptionRecord).where(
        ExceptionRecord.engagement_id == engagement_id,
        ExceptionRecord.module == "AUDIT",
    )
    return len(list(_session().scalars(stmt).all()))


def run_audit_review(engagement_id: int) -> AuditReviewResult:
    """Computes fresh outcomes, clears untouched-automated prior AUDIT
    exceptions, then persists every exception this run found as an
    ExceptionRecord + linked QueryRecord pair — except a finding that
    exactly matches one already preserved because a reviewer is working
    on it. Insufficient Data outcomes are never persisted — same as
    Accounting."""
    engagement, _dataset, outcomes = _compute_outcomes(engagement_id, persist_transactions=True)

    preserved_before = _count_all_audit_exceptions(engagement_id)
    cleared = _clear_stale_automated_exceptions(engagement_id)
    preserved = preserved_before - cleared
    preserved_keys = _preserved_finding_keys(engagement_id)

    rule_rows_by_id = {row.rule_id: row for row in rule_runner_service.get_runnable_audit_rules()}
    assertion_codes_by_rule_id = _assertion_codes_by_rule_id()

    to_insert = []  # (ExceptionRecord, ExceptionDraft)
    for rule_id, outcome in outcomes.items():
        rule_row = rule_rows_by_id.get(rule_id)
        standard_reference = rule_row.related_sa if rule_row is not None else None
        assertions = assertion_codes_by_rule_id.get(rule_id)

        for draft in outcome.exceptions:
            if (rule_id, draft.trigger_condition) in preserved_keys:
                continue  # a reviewer is already working on this exact finding — don't duplicate it
            exc = ExceptionRecord(
                engagement_id=engagement_id,
                module="AUDIT",
                area=draft.area,
                rule_id=rule_id,
                standard_reference=standard_reference,
                description=draft.explanation,
                related_transaction_id=draft.related_transaction_id,
                amount=draft.amount_paise,
                risk_level=draft.risk_level,
                status="OPEN",
                created_at=_now_iso(),
                trigger_condition=draft.trigger_condition,
                threshold_used_json=json.dumps(draft.threshold_used) if draft.threshold_used else None,
                data_sources_json=json.dumps(draft.data_sources) if draft.data_sources else None,
                assertions_snapshot=json.dumps(assertions) if assertions else None,
            )
            _session().add(exc)
            to_insert.append((exc, draft))

    _session().commit()  # assigns exception_id to every new row above

    for exc, draft in to_insert:
        query = QueryRecord(
            engagement_id=engagement_id,
            exception_id=exc.exception_id,
            category="AUDIT",
            area=draft.area,
            observation=draft.explanation,
            question_text=draft.suggested_query,
            risk_level=draft.risk_level,
            status="OPEN",
            is_ai_drafted=False,
            created_at=_now_iso(),
        )
        _session().add(query)

    _session().commit()

    return AuditReviewResult(
        engagement_id=engagement_id,
        rule_outcomes=outcomes,
        persisted_exception_count=len(to_insert),
        preserved_exception_count=preserved,
    )


def get_last_review_results(engagement_id: int) -> list[PersistedAuditException]:
    """Every currently-persisted AUDIT exception for this engagement.
    Mirrors accounting_review_service.get_last_review_results(), plus
    parsing `assertions_snapshot` back into a plain list."""
    stmt = (
        select(ExceptionRecord)
        .where(ExceptionRecord.engagement_id == engagement_id, ExceptionRecord.module == "AUDIT")
        .order_by(ExceptionRecord.exception_id)
    )
    exceptions = list(_session().scalars(stmt).all())

    results = []
    for exc in exceptions:
        q_stmt = select(QueryRecord).where(QueryRecord.exception_id == exc.exception_id)
        query = _session().scalars(q_stmt).first()
        threshold_used = json.loads(exc.threshold_used_json) if exc.threshold_used_json else None
        data_sources = json.loads(exc.data_sources_json) if exc.data_sources_json else None
        assertions = json.loads(exc.assertions_snapshot) if exc.assertions_snapshot else None
        results.append(PersistedAuditException(
            exception=exc, query=query, threshold_used=threshold_used, data_sources=data_sources,
            assertions=assertions,
        ))
    return results


def get_assertion_codes_by_rule_id() -> dict[str, list[str]]:
    """Public wrapper around `_assertion_codes_by_rule_id()` — used by
    `audit_bp.py` to annotate the LIVE preview's rule_outcomes with
    assertion codes (the persisted side gets this from each exception's
    own `assertions_snapshot` instead; a live RuleOutcome has no such
    field, since ExceptionDraft is deliberately free of any DB-lookup
    concern per `base_rule.py`'s docstring)."""
    return _assertion_codes_by_rule_id()


def get_audit_rules_by_id() -> dict[str, AuditRule]:
    """rule_id -> AuditRule, for joining Audit Area / SA reference /
    Suggested Audit Procedure / Suggested Evidence onto both the live
    preview and the persisted-exception display — the same "recompute
    live, never cache" pattern already used for Accounting's Standard
    lookup (`rule_runner_service.get_standards_by_id()`). Neither
    `suggested_audit_procedure` nor `suggested_evidence` is stored per-
    exception-instance; both are catalogue-level static text looked up
    through this map at display time, avoiding any further schema
    additions beyond the one approved `suggested_evidence` column."""
    return {row.rule_id: row for row in rule_runner_service.list_all_audit_rules()}
