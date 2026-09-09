"""
Query & Working Papers orchestration (Stage 13).

Operates entirely on the existing `ExceptionRecord` / `QueryRecord` /
`QueryResponse` schema (plus the three Stage 13-approved additive
columns — see `database/migrations/versions/
0003_query_reviewer_editing_and_evidence.py`) and the existing
`AuditLog` table. No new table is introduced here.

Two status fields exist and are DELIBERATELY kept independent, per your
explicit Stage 13 approval:

  - `ExceptionRecord.status` (8 values: OPEN / UNDER_REVIEW /
    QUERY_RAISED / RESPONSE_RECEIVED / RESOLVED / REVIEWED_NO_ISSUE /
    NOT_APPLICABLE / CLOSED) — this is the one Stage 13 actually
    manages. The reviewer-facing "conclusion" labels (Confirmed /
    Cleared / Not Applicable / Further Review Required) are a pure
    *display* mapping over these same underlying values — see
    `CONCLUSION_LABELS` below. `status_reason` is enforced as required
    whenever the reviewer sets REVIEWED_NO_ISSUE or NOT_APPLICABLE
    (`StatusReasonRequiredError`), matching the rule the model's own
    docstring already documented but that no code had enforced yet.
  - `QueryRecord.status` — left exactly as Stage 3 built it (still
    always "OPEN", since nothing before Stage 13 ever transitioned it,
    and Stage 13 does not redesign it either). It is displayed, never
    silently hidden, so the UI can distinguish "Finding Status" from
    "Query Status" per your instruction, but no route or function in
    this module ever writes to it.

Traceability (your explicit requirement): `QueryRecord.question_text`
(the original, FinSight-generated query) is NEVER read from a form and
written back here — only `reviewer_query_text` is ever set by
`update_working_paper()`. Likewise `ExceptionRecord.description` /
`.trigger_condition` (the original automated finding) are never written
by anything in this module — only `reviewer_notes` and `status`/
`status_reason` are reviewer-editable exception fields.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from app import extensions
from app.models.exceptions import ExceptionRecord
from app.models.queries import QueryRecord, QueryResponse
from app.models.system import AuditLog
from app.models.transactions import Transaction
from app.services import unified_review_service

# ExceptionRecord.status is the one FULL vocabulary Stage 13 exposes to
# the reviewer for both "status" and "conclusion" — reused verbatim, no
# new enum (per your explicit approval). Order matches the model's own
# documented flow.
STATUS_VALUES = (
    "OPEN", "UNDER_REVIEW", "QUERY_RAISED", "RESPONSE_RECEIVED",
    "RESOLVED", "REVIEWED_NO_ISSUE", "NOT_APPLICABLE", "CLOSED",
)

# Reviewer-facing "conclusion" label for each underlying status value —
# display only. The database always stores the left-hand value; nothing
# in this file ever stores "Confirmed"/"Cleared"/etc. as data.
CONCLUSION_LABELS = {
    "OPEN": "Open",
    "UNDER_REVIEW": "Further Review Required",
    "QUERY_RAISED": "Query Raised",
    "RESPONSE_RECEIVED": "Response Received",
    "RESOLVED": "Confirmed",
    "REVIEWED_NO_ISSUE": "Cleared",
    "NOT_APPLICABLE": "Not Applicable",
    "CLOSED": "Closed",
}

# Statuses that require a non-blank status_reason before they may be
# saved (Blueprint Section 7, enforced here for the first time). Public
# (no leading underscore) — app/api/exceptions_bp.py reads this to tell
# the reviewer, in the UI, which statuses need an explanation.
STATUS_REQUIRES_REASON = ("REVIEWED_NO_ISSUE", "NOT_APPLICABLE")
_STATUS_REQUIRES_REASON = STATUS_REQUIRES_REASON  # internal alias, unchanged call sites below

# Statuses that count as "this finding is settled" for resolved_at.
_TERMINAL_STATUSES = ("RESOLVED", "REVIEWED_NO_ISSUE", "NOT_APPLICABLE", "CLOSED")


def _session():
    """See engagement_service._session()'s docstring — same reasoning."""
    return extensions.SessionLocal


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class WorkingPaperNotFoundError(Exception):
    """Raised when a working paper / query action is requested for an
    exception_id that does not exist."""


class InvalidStatusError(ValueError):
    """Raised when a status value outside STATUS_VALUES is submitted."""


class StatusReasonRequiredError(ValueError):
    """Raised when the reviewer tries to save REVIEWED_NO_ISSUE or
    NOT_APPLICABLE without a status_reason — "Do not silently allow
    those statuses without the required reviewer explanation," per your
    explicit instruction."""


# --- Audit trail -------------------------------------------------------------


def _log(engagement_id: int, action: str, entity_affected: str, detail: dict, performed_by: str | None = None) -> None:
    """The first code in FinSight to actually write to `AuditLog`
    (Stage 3 schema, unused until now) — reused exactly as it already
    exists, no second audit-log mechanism introduced."""
    entry = AuditLog(
        engagement_id=engagement_id,
        action=action,
        entity_affected=entity_affected,
        performed_by=performed_by,
        timestamp=_now_iso(),
        detail_json=json.dumps(detail) if detail else None,
    )
    _session().add(entry)


def get_audit_trail(exception_id: int) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.entity_affected == f"exceptions.{exception_id}")
        .order_by(AuditLog.log_id)
    )
    return list(_session().scalars(stmt).all())


# --- Lookups -------------------------------------------------------------


def _get_query_for_exception(exception_id: int) -> QueryRecord | None:
    stmt = select(QueryRecord).where(QueryRecord.exception_id == exception_id)
    return _session().scalars(stmt).first()


def _get_latest_response(query_id: int) -> QueryResponse | None:
    stmt = (
        select(QueryResponse)
        .where(QueryResponse.query_id == query_id)
        .order_by(QueryResponse.response_id.desc())
    )
    return _session().scalars(stmt).first()


@dataclass
class WorkingPaper:
    """Everything the Working Paper screen needs, assembled read-only
    from the existing tables — never a duplicate copy of the finding.
    `finding` is the Stage 12 `NormalizedFinding` (title, why-flagged,
    reference, module-specific fields — all reused, not recomputed
    here)."""
    exception: ExceptionRecord
    finding: object | None  # unified_review_service.NormalizedFinding
    query: QueryRecord | None
    response: QueryResponse | None
    audit_trail: list


def get_working_paper(exception_id: int) -> WorkingPaper | None:
    exc = _session().get(ExceptionRecord, exception_id)
    if exc is None:
        return None
    finding = unified_review_service.get_finding(exc.engagement_id, exc.module, exc.exception_id)
    query = _get_query_for_exception(exception_id)
    response = _get_latest_response(query.query_id) if query is not None else None
    audit_trail = get_audit_trail(exception_id)
    return WorkingPaper(exception=exc, finding=finding, query=query, response=response, audit_trail=audit_trail)


# --- Reviewer actions (single combined save, granular audit entries) --------


def update_working_paper(
    exception_id: int,
    *,
    assigned_to: str | None = None,
    reviewer_query_text: str | None = None,
    management_response: str | None = None,
    evidence_description: str | None = None,
    evidence_reference: str | None = None,
    reviewer_comments: str | None = None,
    resolution: str | None = None,
    reviewer_notes: str | None = None,
    status: str | None = None,
    status_reason: str | None = None,
) -> WorkingPaper:
    """One form submission from the Working Paper screen, applied as a
    set of independent, individually-audited updates. Every parameter
    is the FULL current value for that field (the HTTP layer always
    submits the whole form) — a value equal to what's already stored is
    a no-op (no audit entry), and an empty string clears a field to
    None, exactly like every other text field in this codebase.

    Never touches `ExceptionRecord.description`/`.trigger_condition`
    (the original automated finding) or `QueryRecord.question_text`
    (the original FinSight-generated query) — those two are read-only
    everywhere in this function."""
    exc = _session().get(ExceptionRecord, exception_id)
    if exc is None:
        raise WorkingPaperNotFoundError(f"No exception found with exception_id={exception_id}.")

    if status is not None and status != "" and status not in STATUS_VALUES:
        raise InvalidStatusError(f"{status!r} is not one of the approved status values {STATUS_VALUES!r}.")
    if status in _STATUS_REQUIRES_REASON and not (status_reason or "").strip():
        raise StatusReasonRequiredError(
            f"Saving status {status!r} requires a status_reason explaining the reviewer's conclusion — "
            f"it was left blank."
        )

    entity_key = f"exceptions.{exception_id}"
    reviewer_name = (assigned_to or exc.assigned_to) or None

    # --- Exception-level fields: assigned_to, reviewer_notes, status/status_reason ---
    if assigned_to is not None and assigned_to != (exc.assigned_to or ""):
        _log(exc.engagement_id, "REVIEWER_ASSIGNED", entity_key,
             {"from": exc.assigned_to, "to": assigned_to or None}, reviewer_name)
        exc.assigned_to = assigned_to or None

    if reviewer_notes is not None and reviewer_notes != (exc.reviewer_notes or ""):
        _log(exc.engagement_id, "REVIEWER_NOTES_CHANGED", entity_key,
             {"from": exc.reviewer_notes, "to": reviewer_notes or None}, reviewer_name)
        exc.reviewer_notes = reviewer_notes or None

    if status is not None and status != "" and status != exc.status:
        _log(exc.engagement_id, "STATUS_CHANGED", entity_key,
             {"from": exc.status, "to": status, "conclusion_label": CONCLUSION_LABELS.get(status),
              "status_reason": status_reason or None},
             reviewer_name)
        exc.status = status
        exc.status_reason = status_reason or None if status in _STATUS_REQUIRES_REASON else (status_reason or exc.status_reason)
        exc.resolved_at = _now_iso() if status in _TERMINAL_STATUSES else None
    elif status_reason is not None and status_reason != (exc.status_reason or ""):
        # Reason edited without a status change (e.g. clarifying an
        # already-set REVIEWED_NO_ISSUE) — still logged, still honored.
        _log(exc.engagement_id, "STATUS_REASON_CHANGED", entity_key,
             {"from": exc.status_reason, "to": status_reason or None}, reviewer_name)
        exc.status_reason = status_reason or None

    # --- Query-level: reviewer_query_text only (question_text is never touched) ---
    query = _get_query_for_exception(exception_id)
    if query is not None and reviewer_query_text is not None and reviewer_query_text != (query.reviewer_query_text or ""):
        _log(exc.engagement_id, "QUERY_TEXT_EDITED", entity_key,
             {"query_id": query.query_id, "from": query.reviewer_query_text, "to": reviewer_query_text or None,
              "original_question_text_unchanged": query.question_text},
             reviewer_name)
        query.reviewer_query_text = reviewer_query_text or None

    # --- Response-level: response + evidence (upsert the one current response) ---
    response_fields_given = any(
        v is not None for v in (management_response, evidence_description, evidence_reference, reviewer_comments, resolution)
    )
    if query is not None and response_fields_given:
        response = _get_latest_response(query.query_id)
        is_new = response is None
        if is_new:
            response = QueryResponse(query_id=query.query_id)
            _session().add(response)

        response_changed = False
        evidence_changed = False
        if management_response is not None and management_response != (response.management_response or ""):
            response_changed = True
            response.management_response = management_response or None
        if reviewer_comments is not None and reviewer_comments != (response.reviewer_comments or ""):
            response_changed = True
            response.reviewer_comments = reviewer_comments or None
        if resolution is not None and resolution != (response.resolution or ""):
            response_changed = True
            response.resolution = resolution or None
        if evidence_description is not None and evidence_description != (response.evidence_description or ""):
            evidence_changed = True
            response.evidence_description = evidence_description or None
        if evidence_reference is not None and evidence_reference != (response.evidence_reference or ""):
            evidence_changed = True
            response.evidence_reference = evidence_reference or None

        if response_changed or evidence_changed or is_new:
            response.responded_at = _now_iso()

        if response_changed:
            _log(exc.engagement_id, "RESPONSE_ADDED" if is_new else "RESPONSE_UPDATED", entity_key,
                 {"query_id": query.query_id, "management_response": response.management_response,
                  "resolution": response.resolution},
                 reviewer_name)
        if evidence_changed:
            _log(exc.engagement_id, "EVIDENCE_ADDED" if is_new else "EVIDENCE_UPDATED", entity_key,
                 {"query_id": query.query_id, "evidence_description": response.evidence_description,
                  "evidence_reference": response.evidence_reference},
                 reviewer_name)

    _session().commit()
    return get_working_paper(exception_id)


# --- Query Centre (list + filter + summary) ----------------------------------


@dataclass
class QueryListItem:
    query: QueryRecord
    exception: ExceptionRecord
    latest_response: QueryResponse | None
    # Stage 19: the specific transaction row this finding was raised
    # against, when the rule that raised it recorded one (see
    # dataset_service.attach_transaction_ids()) — None for a finding
    # with no single linked row (an aggregate/period-level check, or a
    # FIXED_ASSETS/GST/TDS row, or simply an older finding raised
    # before this feature existed). Never a second copy of the data —
    # this is the actual `transactions` row, looked up once per
    # list_queries() call and attached here so templates/exports don't
    # each need their own join.
    transaction: Transaction | None = None

    @property
    def account_name(self) -> str | None:
        return self.transaction.account_name if self.transaction is not None else None

    @property
    def transaction_date(self) -> str | None:
        return self.transaction.transaction_date if self.transaction is not None else None

    @property
    def module(self) -> str:
        return self.exception.module

    @property
    def rule_id(self) -> str | None:
        return self.exception.rule_id

    @property
    def effective_query_text(self) -> str | None:
        """The query text currently in effect — the reviewer's edit if
        one exists, otherwise the original. Both remain independently
        readable via `.query.question_text` / `.query.reviewer_query_text`."""
        return self.query.reviewer_query_text or self.query.question_text

    @property
    def finding_status(self) -> str:
        return self.exception.status

    @property
    def conclusion_label(self) -> str:
        return CONCLUSION_LABELS.get(self.exception.status, self.exception.status)

    @property
    def last_updated(self) -> str | None:
        """Derived, not stored — the latest of created_at / a response's
        responded_at / the exception's resolved_at. No new "updated_at"
        column was added for this (not part of the approved schema
        proposal); this is computed from timestamps that already exist."""
        candidates = [self.query.created_at]
        if self.latest_response and self.latest_response.responded_at:
            candidates.append(self.latest_response.responded_at)
        if self.exception.resolved_at:
            candidates.append(self.exception.resolved_at)
        return max(c for c in candidates if c)


def list_queries(
    engagement_id: int, *, module: str | None = None, status: str | None = None,
    risk_level: str | None = None, rule_id: str | None = None, search: str | None = None,
) -> list[QueryListItem]:
    """Every query for this engagement, joined (in Python — the sandbox
    ORM shim supports neither multi-column select() nor .join(), same
    constraint every other service in this codebase already works
    around) with its exception and latest response. `status` filters on
    `ExceptionRecord.status` (the vocabulary Stage 13 actually manages —
    see the module docstring for why `QueryRecord.status` is not
    filterable here)."""
    exc_stmt = select(ExceptionRecord).where(ExceptionRecord.engagement_id == engagement_id)
    exceptions_by_id = {e.exception_id: e for e in _session().scalars(exc_stmt).all()}

    q_stmt = select(QueryRecord).where(QueryRecord.engagement_id == engagement_id)
    queries = list(_session().scalars(q_stmt).all())

    # Stage 19: one batch lookup of every Transaction for this
    # engagement, rather than a query per row — same "fetch by
    # engagement_id, join in Python" pattern this function already uses
    # for exceptions_by_id above (the sandbox ORM shim supports neither
    # multi-column select(), .join(), nor .in_()).
    txn_stmt = select(Transaction).where(Transaction.engagement_id == engagement_id)
    transactions_by_id = {t.transaction_id: t for t in _session().scalars(txn_stmt).all()}

    items = []
    for q in queries:
        exc = exceptions_by_id.get(q.exception_id) if q.exception_id is not None else None
        if exc is None:
            continue  # a query must be linked to a finding to appear in the Query Centre
        response = _get_latest_response(q.query_id)
        transaction = transactions_by_id.get(exc.related_transaction_id) if exc.related_transaction_id else None
        items.append(QueryListItem(query=q, exception=exc, latest_response=response, transaction=transaction))

    if module:
        items = [i for i in items if i.module == module]
    if status:
        items = [i for i in items if i.finding_status == status]
    if risk_level:
        items = [i for i in items if i.exception.risk_level == risk_level]
    if rule_id:
        items = [i for i in items if i.rule_id == rule_id]
    if search:
        needle = search.strip().lower()
        items = [
            i for i in items
            if needle in str(i.query.query_id).lower()
            or needle in str(i.exception.exception_id).lower()
            or needle in (i.rule_id or "").lower()
            or needle in (i.query.question_text or "").lower()
            or needle in (i.query.reviewer_query_text or "").lower()
        ]

    items.sort(key=lambda i: i.query.query_id)
    return items


# --- Working Paper Excel export (Stage 18, approved) -------------------------


def export_working_papers_workbook(engagement_id: int):
    """Builds the Query & Working Papers Excel export: one row per
    query, in the same Sr No / Account Name / Date / Amount /
    Observation / Additional Note / Client Remark shape the on-screen
    table uses (see queries/index.html). "Additional Note" is
    `QueryResponse.reviewer_comments` and "Client Remark" is
    `QueryResponse.management_response` — the same two existing fields
    the on-screen table's inline edit already writes via
    `update_working_paper()`, reused here rather than adding any new
    column.

    Account Name and Date (Stage 19): populated when the finding was
    raised against one specific transaction row AND that row came from
    a ledger-style file (TB/GL/JE/SALES/PURCHASE/BANK/AR/AP/PRIOR_YEAR/
    OTHER — see `dataset_service.TRANSACTION_DATASET_TYPES`). Left
    blank for an aggregate/period-level finding with no single row to
    point at, for a FIXED_ASSETS/GST/TDS-triggered finding (those
    dataset types aren't wired into this yet), or for a finding raised
    before this feature existed. A reviewer can always fill either
    column in by hand for a row that's blank.

    Returns an `openpyxl.Workbook` — turning it into bytes and an HTTP
    response is left to `app/api/queries_bp.py`, matching this
    codebase's "service module owns the logic, blueprint owns
    request/response" split."""
    from openpyxl import Workbook

    from app.utils.currency import paise_to_rupees_float

    items = list_queries(engagement_id)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Working Papers"
    sheet.append([
        "Sr No", "Account Name", "Date", "Amount (INR)", "Observation", "Additional Note", "Client Remark",
    ])
    for idx, item in enumerate(items, start=1):
        response = item.latest_response
        sheet.append([
            idx,
            item.account_name or "",
            item.transaction_date or "",
            paise_to_rupees_float(item.exception.amount),
            item.effective_query_text or "",
            (response.reviewer_comments if response else "") or "",
            (response.management_response if response else "") or "",
        ])
    return workbook


def query_summary(engagement_id: int) -> dict:
    """Stage 13 section 15's Query/Working Paper summary — computed
    from actual QueryRecord/ExceptionRecord data, no hard-coded counts."""
    items = list_queries(engagement_id)
    by_status = {s: 0 for s in STATUS_VALUES}
    by_module = {m: 0 for m in unified_review_service.MODULES}
    for i in items:
        by_status[i.finding_status] = by_status.get(i.finding_status, 0) + 1
        by_module[i.module] = by_module.get(i.module, 0) + 1
    return {"total": len(items), "by_status": by_status, "by_module": by_module}
