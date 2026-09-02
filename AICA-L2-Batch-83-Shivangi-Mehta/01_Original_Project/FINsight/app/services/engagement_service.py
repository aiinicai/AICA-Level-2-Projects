"""
Engagement / Entity Profile / Applicability persistence (Stage 5).

Real SQLAlchemy 2.x ORM code — Session via the module-level scoped
session (`app.extensions.SessionLocal`), `select()` queries, no raw
SQL. This is the first stage that actually persists data; Stages 2-4
only imported `sqlalchemy.create_engine`/`sessionmaker` for engine
plumbing and never touched the ORM layer for real.

No new tables or fields are used here — every field this module reads
or writes already exists in the approved Stage 3 schema
(`app/models/engagement.py`). "Current engagement" is a Flask session
cookie value (`flask_session["current_engagement_id"]`), not a
database row — deliberately, so LAN mode's multiple simultaneous
reviewers each get their own current-engagement context for free via
their own browser session, with no new table required.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app import extensions
from app.models.documents import Document
from app.models.engagement import Applicability, EntityProfile, Engagement
from app.models.exceptions import ExceptionRecord
from app.models.queries import QueryRecord, QueryResponse
from app.models.risk import RiskScore
from app.models.structured_datasets import FixedAsset, GstLineItem, TdsLineItem
from app.models.system import AuditLog
from app.models.transactions import Transaction
from app.models.uploads import DataMapping, UploadedFile
from app.services.applicability_engine import AREAS, suggest_applicability


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _session():
    """Deliberately re-reads `extensions.SessionLocal` on every call
    instead of doing `from app.extensions import SessionLocal` once at
    module-import time. `create_app()` can run more than once in the
    same process (every pytest test that calls it does exactly this),
    and each call rebinds `app.extensions.SessionLocal` to a fresh
    engine/session — a name-import here would freeze this module onto
    whichever engine existed at its *first* import, silently reading
    and writing a stale, orphaned in-memory database in every test
    after the first one bootstraps a real DB-touching route."""
    return extensions.SessionLocal


# --- Engagement -------------------------------------------------------

def list_engagements() -> list[Engagement]:
    stmt = select(Engagement).order_by(Engagement.updated_at.desc())
    return list(_session().scalars(stmt).all())


def find_engagement_by_entity_and_year(entity_name: str, financial_year: str) -> Engagement | None:
    """Added in Stage 8 for accounting rules that need a comparable
    prior-year engagement (e.g. depreciation-policy or provision-
    reversal consistency) — not a schema change, just a read helper
    alongside the existing `list_engagements()`/`get_engagement()`.
    Exact, case-sensitive `entity_name` match: a looser fuzzy match
    risks silently comparing two different entities' data."""
    stmt = select(Engagement).where(
        Engagement.entity_name == entity_name,
        Engagement.financial_year == financial_year,
    )
    return _session().scalars(stmt).first()


def get_engagement(engagement_id: int) -> Engagement | None:
    return _session().get(Engagement, engagement_id)


def create_engagement(entity_name: str, financial_year: str, created_by: str | None = None) -> Engagement:
    now = _now_iso()
    engagement = Engagement(
        entity_name=entity_name,
        financial_year=financial_year,
        status="DRAFT",
        created_at=now,
        updated_at=now,
        created_by=created_by or None,
    )
    _session().add(engagement)
    _session().commit()
    return engagement


def delete_engagement(engagement_id: int) -> None:
    """Stage 20 addition: until now there was no way to remove an
    engagement/client at all — once created, it stayed in the
    Engagements list forever, with no path to clean up a test entry or
    a client relationship that has ended. This permanently deletes the
    engagement and every row anywhere in the schema that traces back to
    it — there is no undo.

    No schema change: every dependent row is deleted explicitly, in
    FK-safe order (children before the parents they reference), the
    same `session.delete()`-per-row pattern `upload_service.
    delete_upload()` already established for exactly this reason — "so
    this works the same way against any SQLAlchemy-compatible session"
    — rather than relying solely on the two ORM `cascade=` relationships
    already declared on `Engagement` (EntityProfile, Applicability),
    which don't cover the rest of this dependency graph at all.

    QueryResponse/RiskScore/DataMapping have no `engagement_id` column
    of their own (only a FK one level up — query_id/exception_id/
    file_id) and this codebase's sandbox ORM shim supports neither
    `.join()` nor `.in_()` (see `query_service.py`'s own docstring for
    the same constraint) — so, consistent with every other service in
    this codebase, those three are fetched whole and filtered in Python
    against this engagement's own already-fetched parent-id sets,
    rather than a SQL `IN (...)`/join.

    Order (each step is a child of, i.e. FK-references, a table deleted
    at or after that step — see app/models/*.py for the exact FKs this
    mirrors): QueryResponse (-> queries) and Document (-> queries,
    exceptions) first; then RiskScore (-> exceptions); then QueryRecord/
    "queries" itself (-> exceptions); then ExceptionRecord/"exceptions"
    itself (-> transactions); then GstLineItem/TdsLineItem/FixedAsset
    (-> transactions/uploaded_files); then Transaction (->
    uploaded_files); then DataMapping (-> uploaded_files); then
    UploadedFile itself (with a best-effort disk-file unlink per file,
    mirroring delete_upload()'s own disk-cleanup pattern); then
    AuditLog; then Applicability/EntityProfile (already ORM-cascaded,
    deleted explicitly anyway for the same reason as everything else
    here); finally the Engagement row itself.

    Does NOT touch `flask_session["current_engagement_id"]` — that's a
    Flask session cookie, not a DB row, and `get_current_engagement()`
    already self-heals if it points at an engagement that no longer
    exists. The route calling this clears it proactively anyway, purely
    so the UI doesn't keep showing a stale "current" label until the
    next request.

    A no-op (returns without error) if `engagement_id` doesn't exist at
    all — mirrors `delete_upload()`'s own no-op-on-missing-row
    behaviour.
    """
    session = _session()
    engagement = session.get(Engagement, engagement_id)
    if engagement is None:
        return

    query_ids = [q.query_id for q in session.scalars(
        select(QueryRecord).where(QueryRecord.engagement_id == engagement_id)
    ).all()]
    exception_ids = [e.exception_id for e in session.scalars(
        select(ExceptionRecord).where(ExceptionRecord.engagement_id == engagement_id)
    ).all()]
    file_rows = list(session.scalars(
        select(UploadedFile).where(UploadedFile.engagement_id == engagement_id)
    ).all())
    file_ids = [f.file_id for f in file_rows]

    query_id_set = set(query_ids)
    exception_id_set = set(exception_ids)
    file_id_set = set(file_ids)

    if query_id_set:
        for row in session.scalars(select(QueryResponse)).all():
            if row.query_id in query_id_set:
                session.delete(row)
    for row in session.scalars(select(Document).where(Document.engagement_id == engagement_id)).all():
        session.delete(row)
    if exception_id_set:
        for row in session.scalars(select(RiskScore)).all():
            if row.exception_id in exception_id_set:
                session.delete(row)
    for row in session.scalars(select(QueryRecord).where(QueryRecord.engagement_id == engagement_id)).all():
        session.delete(row)
    for row in session.scalars(select(ExceptionRecord).where(ExceptionRecord.engagement_id == engagement_id)).all():
        session.delete(row)
    for row in session.scalars(select(GstLineItem).where(GstLineItem.engagement_id == engagement_id)).all():
        session.delete(row)
    for row in session.scalars(select(TdsLineItem).where(TdsLineItem.engagement_id == engagement_id)).all():
        session.delete(row)
    for row in session.scalars(select(FixedAsset).where(FixedAsset.engagement_id == engagement_id)).all():
        session.delete(row)
    for row in session.scalars(select(Transaction).where(Transaction.engagement_id == engagement_id)).all():
        session.delete(row)
    if file_id_set:
        for row in session.scalars(select(DataMapping)).all():
            if row.file_id in file_id_set:
                session.delete(row)
    for row in file_rows:
        session.delete(row)
    for row in session.scalars(select(AuditLog).where(AuditLog.engagement_id == engagement_id)).all():
        session.delete(row)
    for row in session.scalars(select(Applicability).where(Applicability.engagement_id == engagement_id)).all():
        session.delete(row)
    for row in session.scalars(select(EntityProfile).where(EntityProfile.engagement_id == engagement_id)).all():
        session.delete(row)

    session.delete(engagement)
    session.commit()

    for file_row in file_rows:
        try:
            Path(file_row.stored_path).unlink(missing_ok=True)
        except OSError:
            pass  # best-effort disk cleanup only — the database rows are already gone


# --- Entity Profile -----------------------------------------------------

def get_entity_profile(engagement_id: int) -> EntityProfile | None:
    stmt = select(EntityProfile).where(EntityProfile.engagement_id == engagement_id)
    return _session().scalars(stmt).first()


def save_entity_profile(engagement_id: int, fields: dict) -> EntityProfile:
    """Create-or-update the engagement's one EntityProfile row (the DB's
    own UNIQUE(engagement_id) constraint is the backstop; this get-then-
    update path is the normal case and keeps a single INSERT vs UPDATE
    decision in one place rather than relying on that constraint to
    reject a bad second insert)."""
    profile = get_entity_profile(engagement_id)
    if profile is None:
        profile = EntityProfile(engagement_id=engagement_id, **fields)
        _session().add(profile)
    else:
        for key, value in fields.items():
            setattr(profile, key, value)

    engagement = get_engagement(engagement_id)
    if engagement is not None:
        # First profile save moves a fresh engagement out of DRAFT.
        # This is a workflow default within the already-approved
        # `status` enum (Blueprint D.1) — not a new field/value — and
        # is easy to revisit if a later stage wants an explicit
        # DRAFT -> IN_PROGRESS action instead of an implicit one.
        if engagement.status == "DRAFT":
            engagement.status = "IN_PROGRESS"
        engagement.updated_at = _now_iso()

    _session().commit()
    refresh_applicability(engagement_id)
    return profile


# --- Applicability -------------------------------------------------------

def profile_facts(profile: EntityProfile) -> dict:
    """The subset of Entity Profile fields the applicability engine
    reads, as a plain dict — shared by `refresh_applicability()` (to
    compute suggestions) and `app/api/engagement_bp.py`'s applicability
    view (to render each area's "Entity Profile Input" line via
    `applicability_engine.entity_profile_input()`), so both always see
    exactly the same facts."""
    return {
        "accounting_framework": profile.accounting_framework,
        "statutory_audit_applicable": profile.statutory_audit_applicable,
        "tax_audit_status": profile.tax_audit_status,
        "is_listed": profile.is_listed,
    }


def refresh_applicability(engagement_id: int) -> list[Applicability]:
    """Recompute system_suggested_status/reason for every area from the
    current Entity Profile. Never touches user_confirmed_status/note/
    confirmed_by/confirmed_at on an existing row — a profile edit
    updates the *suggestion*, it does not silently erase a professional's
    prior confirmation. If the profile disagrees with an existing
    confirmation after this, that's visible on the Applicability Matrix
    screen (suggestion vs. confirmation shown side by side) for the
    reviewer to reconcile, not something this function decides."""
    profile = get_entity_profile(engagement_id)
    if profile is None:
        return []

    facts = profile_facts(profile)
    suggestions = suggest_applicability(facts)

    rows = []
    for area in AREAS:
        status, reason = suggestions[area]
        stmt = select(Applicability).where(
            Applicability.engagement_id == engagement_id,
            Applicability.area == area,
        )
        row = _session().scalars(stmt).first()
        if row is None:
            row = Applicability(
                engagement_id=engagement_id,
                area=area,
                system_suggested_status=status,
                system_suggested_reason=reason,
            )
            _session().add(row)
        else:
            row.system_suggested_status = status
            row.system_suggested_reason = reason
        rows.append(row)

    _session().commit()
    return rows


def list_applicability(engagement_id: int) -> list[Applicability]:
    stmt = (
        select(Applicability)
        .where(Applicability.engagement_id == engagement_id)
        .order_by(Applicability.applicability_id)
    )
    return list(_session().scalars(stmt).all())


def get_applicability_row(engagement_id: int, area: str) -> Applicability | None:
    stmt = select(Applicability).where(
        Applicability.engagement_id == engagement_id,
        Applicability.area == area,
    )
    return _session().scalars(stmt).first()


def get_enabled_review_modules(engagement_id: int) -> tuple:
    """Stage 18 (approved): which of unified_review_service.MODULES
    should run for this engagement, driven by the Applicability Matrix's
    Yes/No answers rather than a per-run checkbox screen. ACCOUNTING
    always runs — it is not a user-selectable task on the Stage 18
    Applicability Matrix (only Audit Review / Income Tax Review / Tax
    Audit Review are). AUDIT runs when "Audit Review" is confirmed Yes.
    TAX runs when EITHER "Income Tax Review" OR "Tax Audit Review" is
    confirmed Yes — FinSight's existing TAX module already covers both
    rule categories together; there is no separate Income-Tax-only vs
    Tax-Audit-only module to select between (see the Stage 18 report).

    An area with no user_confirmed_status yet (the professional has not
    saved the Applicability Matrix for this engagement) falls back to
    that area's own system_suggested_status, so an engagement nobody has
    touched this screen for keeps running everything, exactly as before
    Stage 18 — nothing is silently disabled by this change. Deliberately
    NOT imported by app/api/review_bp.py's legacy checkbox-based POST
    path (see that blueprint's docstring) — only the new one-click "Run
    Review" action (from the Upload screen) uses this."""
    rows_by_area = {r.area: r for r in list_applicability(engagement_id)}

    def is_yes(area: str) -> bool:
        row = rows_by_area.get(area)
        if row is None:
            return True
        if row.user_confirmed_status == "APPLICABLE":
            return True
        if row.user_confirmed_status == "NOT_APPLICABLE":
            return False
        return row.system_suggested_status == "YES"

    modules = ["ACCOUNTING"]
    if is_yes("Audit Review"):
        modules.append("AUDIT")
    if is_yes("Income Tax Review") or is_yes("Tax Audit Review"):
        modules.append("TAX")
    return tuple(modules)


def confirm_applicability(
    engagement_id: int,
    area: str,
    user_confirmed_status: str,
    user_confirmation_note: str | None,
    confirmed_by: str | None,
) -> Applicability:
    row = get_applicability_row(engagement_id, area)
    if row is None:
        raise ValueError(f"No applicability row for area {area!r} on engagement {engagement_id}")
    row.user_confirmed_status = user_confirmed_status
    row.user_confirmation_note = user_confirmation_note or None
    row.confirmed_by = confirmed_by or None
    row.confirmed_at = _now_iso()
    _session().commit()
    return row


# --- "Current engagement" (Flask session cookie, not a DB table) --------

def set_current_engagement(flask_session, engagement_id: int) -> None:
    flask_session["current_engagement_id"] = engagement_id


def clear_current_engagement(flask_session) -> None:
    flask_session.pop("current_engagement_id", None)


def get_current_engagement(flask_session) -> Engagement | None:
    engagement_id = flask_session.get("current_engagement_id")
    if not engagement_id:
        return None
    engagement = get_engagement(engagement_id)
    if engagement is None:
        # Stale cookie (e.g. DB reset in dev) — self-heal instead of
        # raising, since the app is deep in the browser's own session.
        flask_session.pop("current_engagement_id", None)
    return engagement
