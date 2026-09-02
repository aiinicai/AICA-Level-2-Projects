"""
Accounting Review orchestration (Stage 8): ties `dataset_service`
(validated + confirmed data only) to `rule_runner_service` (gated rule
execution) and persists results as `ExceptionRecord` + linked
`QueryRecord` rows, module="ACCOUNTING" — reusing the exact schema
approved since Stage 3, no new table or field.

Two entry points, deliberately separate:
  - `preview_accounting_review()` — read-only, computes fresh outcomes
    every call (including Insufficient Data reasons) and writes nothing.
    Follows the same "recompute live, never cache" pattern already used
    twice (Stage 6/7 mapping+validation, Stage 8 `dataset_service`)
    rather than inventing a new persisted "last run" concept.
  - `run_accounting_review()` — the explicit, reviewer-triggered "commit
    this run's exceptions" action. Only the Potential-Exception/Review-
    Required/Potential-Inconsistency findings become `ExceptionRecord`
    rows; Insufficient Data is, by definition, not an exception and is
    never persisted as one — a reviewer sees it via
    `preview_accounting_review()`'s live output on the same screen.

Re-run behavior (a disclosed design decision, not a schema change — see
the Stage 8 report): re-running does not blindly wipe every prior
ACCOUNTING exception. Only exceptions still in their untouched,
freshly-auto-generated state (`status == "OPEN"`, no `reviewer_notes`/
`status_reason`, and no `QueryResponse` recorded against their linked
query) are cleared before the new batch is inserted, so repeated runs
don't pile up duplicate rows. Anything a reviewer has already started
working on is left exactly as it is — never deleted, never silently
duplicated.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select

from app import extensions
from app.models.exceptions import ExceptionRecord
from app.models.queries import QueryRecord, QueryResponse
from app.models.rules import Standard
from app.rules.base_rule import RuleOutcome
from app.services import dataset_service, engagement_service, rule_runner_service


def _session():
    """See engagement_service._session()'s docstring — same reasoning."""
    return extensions.SessionLocal


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class EngagementNotFoundError(Exception):
    """Raised when an accounting review is requested for an engagement_id
    that does not exist."""


class AccountingFrameworkNotSetError(Exception):
    """Raised when an accounting review is requested for an engagement
    whose Entity Profile doesn't exist yet, or whose
    `accounting_framework` isn't set — Stage 8 Round 2's framework-aware
    rule gating (correction #1) has nothing to select rules against in
    that state, so this is surfaced as a clear "complete the Entity
    Profile first" condition rather than silently running zero rules or
    guessing a framework."""


@dataclass
class AccountingReviewResult:
    engagement_id: int
    framework: str | None = None  # "AS" or "IND_AS" — which rule set this run actually selected
    rule_outcomes: dict[str, RuleOutcome] = field(default_factory=dict)
    persisted_exception_count: int = 0
    preserved_exception_count: int = 0  # reviewer-touched rows left alone on a run() call; 0 for preview()


@dataclass
class PersistedException:
    """One ExceptionRecord + its linked QueryRecord (if any), with the
    JSON-string columns already parsed back into plain dict/list, for
    templates to render without doing their own json.loads()."""
    exception: ExceptionRecord
    query: QueryRecord | None
    threshold_used: dict | None
    data_sources: list | None


def _compute_outcomes(
    engagement_id: int, *, persist_transactions: bool = False,
) -> tuple[object, str, dict[str, list], dict[str, RuleOutcome]]:
    """`persist_transactions=True` is Stage 19's one addition: only
    `run_accounting_review()` (below) passes it — never
    `preview_accounting_review()`, whose docstring's "touches the
    database at all" promise must stay literally true. When True, this
    refreshes `transactions` (see `dataset_service.attach_transaction_ids()`)
    BEFORE rules run, so a rule module has a real transaction_id
    available to put in `ExceptionDraft.related_transaction_id` for any
    finding it raises against one specific row."""
    engagement = engagement_service.get_engagement(engagement_id)
    if engagement is None:
        raise EngagementNotFoundError(f"No engagement found with engagement_id={engagement_id}.")

    profile = engagement_service.get_entity_profile(engagement_id)
    framework = profile.accounting_framework if profile is not None else None
    if not framework:
        raise AccountingFrameworkNotSetError(
            f"Engagement {engagement_id} has no Entity Profile (or no accounting_framework set) yet — the "
            f"accounting framework must be known before framework-aware rules can be selected."
        )

    dataset = dataset_service.load_engagement_dataset(engagement_id)
    if persist_transactions:
        dataset_service.attach_transaction_ids(engagement_id, dataset)
    outcomes = rule_runner_service.run_all_accounting_rules(engagement, dataset, framework)
    return engagement, framework, dataset, outcomes


def preview_accounting_review(engagement_id: int) -> AccountingReviewResult:
    """Read-only. Computes every gated-runnable accounting rule's
    outcome — for the engagement's own accounting framework only, per
    Stage 8 Round 2 correction #1 — against this engagement's current
    validated + confirmed data, and returns it without touching the
    database at all."""
    _engagement, framework, _dataset, outcomes = _compute_outcomes(engagement_id)
    return AccountingReviewResult(engagement_id=engagement_id, framework=framework, rule_outcomes=outcomes)


def _clear_stale_automated_exceptions(engagement_id: int) -> int:
    stmt = select(ExceptionRecord).where(
        ExceptionRecord.engagement_id == engagement_id,
        ExceptionRecord.module == "ACCOUNTING",
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
    """(rule_id, trigger_condition) for every ACCOUNTING exception still
    on file for this engagement — called AFTER
    `_clear_stale_automated_exceptions()`, so what remains is exactly
    the reviewer-touched rows a fresh run must not delete. Used to also
    skip inserting a brand-new duplicate row for the same finding a
    reviewer is already working on, while still inserting any other
    finding this run turned up."""
    stmt = select(ExceptionRecord).where(
        ExceptionRecord.engagement_id == engagement_id, ExceptionRecord.module == "ACCOUNTING",
    )
    return {
        (exc.rule_id, exc.trigger_condition)
        for exc in _session().scalars(stmt).all()
        if exc.rule_id is not None
    }


def run_accounting_review(engagement_id: int) -> AccountingReviewResult:
    """Computes fresh outcomes, clears untouched-automated prior
    exceptions (see module docstring), then persists every exception
    this run found as an ExceptionRecord + linked QueryRecord pair —
    except a finding that exactly matches one already preserved because
    a reviewer is working on it (same rule_id + trigger_condition),
    which is left as the reviewer's single existing row rather than
    duplicated. Insufficient Data outcomes are never persisted — they
    only ever exist in the returned `rule_outcomes`, same as
    `preview_...()`."""
    engagement, framework, _dataset, outcomes = _compute_outcomes(engagement_id, persist_transactions=True)

    preserved_before = _count_all_accounting_exceptions(engagement_id)
    cleared = _clear_stale_automated_exceptions(engagement_id)
    preserved = preserved_before - cleared
    preserved_keys = _preserved_finding_keys(engagement_id)

    rule_rows_by_id = {row.rule_id: row for row in rule_runner_service.get_runnable_accounting_rules(framework)}

    to_insert = []  # (ExceptionRecord, ExceptionDraft)
    for rule_id, outcome in outcomes.items():
        rule_row = rule_rows_by_id.get(rule_id)
        standard = None
        if rule_row is not None and rule_row.standard_id is not None:
            standard = _session().get(Standard, rule_row.standard_id)

        for draft in outcome.exceptions:
            if (rule_id, draft.trigger_condition) in preserved_keys:
                continue  # a reviewer is already working on this exact finding — don't duplicate it
            exc = ExceptionRecord(
                engagement_id=engagement_id,
                module="ACCOUNTING",
                area=draft.area,
                rule_id=rule_id,
                standard_reference=standard.source_reference if standard is not None else None,
                description=draft.explanation,
                related_transaction_id=draft.related_transaction_id,
                amount=draft.amount_paise,
                risk_level=draft.risk_level,
                status="OPEN",
                created_at=_now_iso(),
                trigger_condition=draft.trigger_condition,
                threshold_used_json=json.dumps(draft.threshold_used) if draft.threshold_used else None,
                data_sources_json=json.dumps(draft.data_sources) if draft.data_sources else None,
            )
            _session().add(exc)
            to_insert.append((exc, draft))

    _session().commit()  # assigns exception_id to every new row above

    for exc, draft in to_insert:
        query = QueryRecord(
            engagement_id=engagement_id,
            exception_id=exc.exception_id,
            category="ACCOUNTING",
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

    return AccountingReviewResult(
        engagement_id=engagement_id,
        framework=framework,
        rule_outcomes=outcomes,
        persisted_exception_count=len(to_insert),
        preserved_exception_count=preserved,
    )


def _count_all_accounting_exceptions(engagement_id: int) -> int:
    """Total ACCOUNTING exceptions currently on file, any status — used
    only as the "before" half of `preserved_before - cleared =
    preserved` in run_accounting_review(); not itself status-filtered."""
    stmt = select(ExceptionRecord).where(
        ExceptionRecord.engagement_id == engagement_id,
        ExceptionRecord.module == "ACCOUNTING",
    )
    return len(list(_session().scalars(stmt).all()))


def get_last_review_results(engagement_id: int) -> list[PersistedException]:
    """Every currently-persisted ACCOUNTING exception for this
    engagement (from any past run() call, whether preserved across
    later runs or freshly inserted by the most recent one) — the
    durable half of the review; Insufficient Data status is never part
    of this since it is never persisted (see module docstring). Each
    exception is paired with its linked QueryRecord (the "Suggested
    Query" half of the why-flagged chain) when one exists."""
    stmt = (
        select(ExceptionRecord)
        .where(ExceptionRecord.engagement_id == engagement_id, ExceptionRecord.module == "ACCOUNTING")
        .order_by(ExceptionRecord.exception_id)
    )
    exceptions = list(_session().scalars(stmt).all())

    results = []
    for exc in exceptions:
        q_stmt = select(QueryRecord).where(QueryRecord.exception_id == exc.exception_id)
        query = _session().scalars(q_stmt).first()
        threshold_used = json.loads(exc.threshold_used_json) if exc.threshold_used_json else None
        data_sources = json.loads(exc.data_sources_json) if exc.data_sources_json else None
        results.append(PersistedException(
            exception=exc, query=query, threshold_used=threshold_used, data_sources=data_sources,
        ))
    return results
