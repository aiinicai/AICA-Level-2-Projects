"""
Tax Review orchestration (Stage 10): ties `dataset_service` (validated
+ confirmed data only) to `rule_runner_service` (gated tax-rule
execution) and persists results as `ExceptionRecord` + linked
`QueryRecord` rows, module="TAX" — reusing the exact schema approved
since Stage 3 (Blueprint Section 2.6/2.12), no new table or field, per
Decision 5.

Mirrors `audit_review_service.py`'s two-entry-point pattern
(`preview_tax_review()` read-only / `run_tax_review()` persists) and
its re-run preservation behavior (untouched, freshly-auto-generated
TAX exceptions are cleared before a new batch is inserted; anything a
reviewer has started working on is left exactly as it is), with ONE
deliberate difference from both Audit and Accounting:

  Act-transition precondition (Decision 1, approved). Every Tax rule
  currently coded is verified and gated against the Income-tax Act,
  1961 only. `_compute_outcomes()` checks
  `act_transition.is_old_act_fy(engagement.financial_year)` BEFORE
  calling `rule_runner_service.run_all_tax_rules()` at all, and raises
  `ActEraNotSupportedError` if the engagement's financial year falls
  under the (largely unverified) Income-tax Act, 2025 — the same
  "surfaced as a clear precondition, never silently guessed" approach
  `AccountingFrameworkNotSetError` already established for Accounting's
  framework precondition.

`standard_reference` is populated from `TaxRule.provision_reference`
(free text, e.g. "Section 40A(3), Section 40A(3A), Income-tax Act,
1961") — the verified OLD-Act citation only. The New Act 2025 forward
reference lives in `TaxRule.description` and is never copied into
`standard_reference` or any persisted exception field, consistent with
it being non-gating, display-only metadata (Stage 10 plan, Section 7).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select

from app import extensions
from app.models.exceptions import ExceptionRecord
from app.models.queries import QueryRecord, QueryResponse
from app.models.rules import TaxRule
from app.rules.base_rule import RuleOutcome
from app.rules.tax import act_transition
from app.services import dataset_service, engagement_service, rule_runner_service


def _session():
    """See engagement_service._session()'s docstring — same reasoning."""
    return extensions.SessionLocal


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class EngagementNotFoundError(Exception):
    """Raised when a tax review is requested for an engagement_id that
    does not exist."""


class ActEraNotSupportedError(Exception):
    """Raised when a tax review is requested for an engagement whose
    financial year falls under the Income-tax Act, 2025 — every Tax
    rule currently coded is verified and gated against the 1961 Act
    only (Decision 1), so there is nothing FinSight can currently run
    for such an engagement. Surfaced as a clear precondition, exactly
    like AccountingFrameworkNotSetError, rather than silently running
    zero rules or (worse) running 1961-Act-verified rules against a
    2026-27+ engagement they were never verified for."""


@dataclass
class TaxReviewResult:
    engagement_id: int
    rule_outcomes: dict[str, RuleOutcome] = field(default_factory=dict)
    persisted_exception_count: int = 0
    preserved_exception_count: int = 0  # reviewer-touched rows left alone on a run() call; 0 for preview()


@dataclass
class PersistedTaxException:
    """One ExceptionRecord + its linked QueryRecord (if any), with the
    JSON-string columns already parsed back into plain dict/list, for
    templates to render without doing their own json.loads(). Mirrors
    audit_review_service.PersistedAuditException minus `assertions`
    (a Tax exception has no assertion snapshot — that field is
    Audit-only, per the existing model comment)."""
    exception: ExceptionRecord
    query: QueryRecord | None
    threshold_used: dict | None
    data_sources: list | None


def _compute_outcomes(
    engagement_id: int, *, persist_transactions: bool = False,
) -> tuple[object, dict[str, list], dict[str, RuleOutcome]]:
    """See accounting_review_service.py's `_compute_outcomes()` for why
    `persist_transactions` exists and why only `run_tax_review()`
    passes True — `preview_tax_review()` must stay fully read-only."""
    engagement = engagement_service.get_engagement(engagement_id)
    if engagement is None:
        raise EngagementNotFoundError(f"No engagement found with engagement_id={engagement_id}.")

    if not act_transition.is_old_act_fy(engagement.financial_year):
        raise ActEraNotSupportedError(
            f"Engagement {engagement_id}'s financial year (\"{engagement.financial_year}\") falls under the "
            f"Income-tax Act, 2025 — every Tax rule currently coded in FinSight is verified and gated against "
            f"the Income-tax Act, 1961 (FY 2025-26 / AY 2026-27 and earlier) only. No tax rule can run for this "
            f"engagement until the Income-tax Act, 2025's provisions are independently verified in a future stage."
        )

    dataset = dataset_service.load_engagement_dataset(engagement_id)
    if persist_transactions:
        dataset_service.attach_transaction_ids(engagement_id, dataset)
    outcomes = rule_runner_service.run_all_tax_rules(engagement, dataset)
    return engagement, dataset, outcomes


def preview_tax_review(engagement_id: int) -> TaxReviewResult:
    """Read-only. Computes every gated-runnable tax rule's outcome
    against this engagement's current validated + confirmed data, and
    returns it without touching the database at all."""
    _engagement, _dataset, outcomes = _compute_outcomes(engagement_id)
    return TaxReviewResult(engagement_id=engagement_id, rule_outcomes=outcomes)


def _clear_stale_automated_exceptions(engagement_id: int) -> int:
    stmt = select(ExceptionRecord).where(
        ExceptionRecord.engagement_id == engagement_id,
        ExceptionRecord.module == "TAX",
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
    stmt = select(ExceptionRecord).where(
        ExceptionRecord.engagement_id == engagement_id, ExceptionRecord.module == "TAX",
    )
    return {
        (exc.rule_id, exc.trigger_condition)
        for exc in _session().scalars(stmt).all()
        if exc.rule_id is not None
    }


def _count_all_tax_exceptions(engagement_id: int) -> int:
    stmt = select(ExceptionRecord).where(
        ExceptionRecord.engagement_id == engagement_id,
        ExceptionRecord.module == "TAX",
    )
    return len(list(_session().scalars(stmt).all()))


def run_tax_review(engagement_id: int) -> TaxReviewResult:
    """Computes fresh outcomes, clears untouched-automated prior TAX
    exceptions, then persists every exception this run found as an
    ExceptionRecord + linked QueryRecord pair — except a finding that
    exactly matches one already preserved because a reviewer is working
    on it. Insufficient Data outcomes are never persisted — same as
    Accounting and Audit."""
    engagement, _dataset, outcomes = _compute_outcomes(engagement_id, persist_transactions=True)

    preserved_before = _count_all_tax_exceptions(engagement_id)
    cleared = _clear_stale_automated_exceptions(engagement_id)
    preserved = preserved_before - cleared
    preserved_keys = _preserved_finding_keys(engagement_id)

    rule_rows_by_id = {row.rule_id: row for row in rule_runner_service.get_runnable_tax_rules()}

    to_insert = []  # (ExceptionRecord, ExceptionDraft)
    for rule_id, outcome in outcomes.items():
        rule_row = rule_rows_by_id.get(rule_id)
        standard_reference = rule_row.provision_reference if rule_row is not None else None

        for draft in outcome.exceptions:
            if (rule_id, draft.trigger_condition) in preserved_keys:
                continue  # a reviewer is already working on this exact finding — don't duplicate it
            exc = ExceptionRecord(
                engagement_id=engagement_id,
                module="TAX",
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
            )
            _session().add(exc)
            to_insert.append((exc, draft))

    _session().commit()  # assigns exception_id to every new row above

    for exc, draft in to_insert:
        query = QueryRecord(
            engagement_id=engagement_id,
            exception_id=exc.exception_id,
            category="TAX",
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

    return TaxReviewResult(
        engagement_id=engagement_id,
        rule_outcomes=outcomes,
        persisted_exception_count=len(to_insert),
        preserved_exception_count=preserved,
    )


def get_last_review_results(engagement_id: int) -> list[PersistedTaxException]:
    """Every currently-persisted TAX exception for this engagement.
    Mirrors audit_review_service.get_last_review_results() minus the
    assertions_snapshot parsing (Tax exceptions never populate that
    field)."""
    stmt = (
        select(ExceptionRecord)
        .where(ExceptionRecord.engagement_id == engagement_id, ExceptionRecord.module == "TAX")
        .order_by(ExceptionRecord.exception_id)
    )
    exceptions = list(_session().scalars(stmt).all())

    results = []
    for exc in exceptions:
        q_stmt = select(QueryRecord).where(QueryRecord.exception_id == exc.exception_id)
        query = _session().scalars(q_stmt).first()
        threshold_used = json.loads(exc.threshold_used_json) if exc.threshold_used_json else None
        data_sources = json.loads(exc.data_sources_json) if exc.data_sources_json else None
        results.append(PersistedTaxException(
            exception=exc, query=query, threshold_used=threshold_used, data_sources=data_sources,
        ))
    return results


def get_tax_rules_by_id() -> dict[str, TaxRule]:
    """rule_id -> TaxRule, for joining Provision/Legislative Act/AY/
    Effective Date/Verified Source/FinSight Analytical Test onto both
    the live preview and the persisted-exception display — the same
    "recompute live, never cache" pattern already used for Audit's rule
    lookup. Returns EVERY tax rule (all 15), not just runnable ones —
    the catalogue and detail views need to show gated rules too."""
    return {row.rule_id: row for row in rule_runner_service.list_all_tax_rules()}
