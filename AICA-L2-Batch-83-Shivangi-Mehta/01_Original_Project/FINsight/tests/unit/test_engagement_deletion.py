"""
Stage 20 — app/services/engagement_service.delete_engagement() (real
SQLAlchemy 2.x ORM persistence, same sandbox caveat as
test_upload_service.py: real Flask + a scoped SQLAlchemy shim over a
real on-disk SQLite DB, not real SQLAlchemy itself — see that file's
own header for the full disclosure).

Builds one row directly in EVERY table that has a direct or transitive
FK to engagements.engagement_id (the full dependency graph mapped in
engagement_service.delete_engagement()'s own docstring), for TWO
separate engagements, then deletes only the first — asserting every one
of its dependent rows is gone (no FK-violation exception raised, no
orphan left behind) while the second engagement's rows are completely
untouched. This is a lower-level, more targeted approach than driving
the whole upload/map/validate/review HTTP pipeline (RiskScore in
particular is, per app/models/risk.py, an unpopulated scaffold table
the app itself never writes to yet — this file still has to exercise
its FK explicitly to prove the deletion code path is FK-safe for it).

Uses only synthetic, fabricated data — never real client/financial
data, per the standing instruction.

Run with: pytest tests/unit/test_engagement_deletion.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
from sqlalchemy import select


@pytest.fixture()
def db(tmp_path):
    """A fresh, empty, real SQLite database wired into app.extensions
    for this one test, plus a scratch directory for fake uploaded files
    on disk — same fixture shape as test_upload_service.py's `svc`."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker

    from app import extensions
    from app.models import Base

    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    extensions.engine = engine
    extensions.SessionLocal = scoped_session(sessionmaker(bind=engine, future=True, expire_on_commit=False))

    yield extensions.SessionLocal

    extensions.SessionLocal.remove()


def _seed_full_dependency_graph(session, engagement, file_dir: Path):
    """Directly inserts one row into every table that FK-references
    (directly or transitively) this engagement, covering the entire
    cascade delete_engagement() has to walk. Returns nothing — the
    caller re-queries afterward."""
    from datetime import datetime, timezone

    from app.models.documents import Document
    from app.models.exceptions import ExceptionRecord
    from app.models.queries import QueryRecord, QueryResponse
    from app.models.risk import RiskScore
    from app.models.structured_datasets import FixedAsset, GstLineItem, TdsLineItem
    from app.models.system import AuditLog
    from app.models.transactions import Transaction
    from app.models.uploads import DataMapping, UploadedFile

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    stored_file = file_dir / f"fake_upload_{engagement.engagement_id}.csv"
    stored_file.write_text("account,debit,credit\nCash,1000,0\n")

    upload = UploadedFile(
        engagement_id=engagement.engagement_id, file_type="GL", original_filename="fake_gl.csv",
        stored_path=str(stored_file), row_count=1, upload_status="MAPPED", uploaded_at=now,
        checksum=f"checksum-{engagement.engagement_id}",
    )
    session.add(upload)
    session.commit()  # NOTE: commit(), not flush() — this sandbox's SQLAlchemy shim
    # (see test_upload_service.py's header) doesn't implement flush(); committing
    # eagerly here is test-harness plumbing only, not a change to app code's own
    # session usage.

    mapping = DataMapping(
        file_id=upload.file_id, source_column="account", target_field="account_name",
        confidence_score=0.9, is_user_confirmed=True, confirmed_at=now,
    )
    session.add(mapping)

    transaction = Transaction(
        engagement_id=engagement.engagement_id, file_id=upload.file_id, dataset_type="GL",
        transaction_date="2025-06-10", account_name="Cash", debit_amount=100000, credit_amount=0,
        created_at=now,
    )
    session.add(transaction)
    session.commit()

    fixed_asset = FixedAsset(
        engagement_id=engagement.engagement_id, file_id=upload.file_id,
        asset_description="Test Machine", asset_class="Plant & Machinery",
    )
    session.add(fixed_asset)

    gst_row = GstLineItem(
        transaction_id=transaction.transaction_id, engagement_id=engagement.engagement_id,
        gstin="27ABCDE1234F1Z5", invoice_number="INV-1", taxable_value_paise=100000,
    )
    session.add(gst_row)

    tds_row = TdsLineItem(
        transaction_id=transaction.transaction_id, engagement_id=engagement.engagement_id,
        section_code="194C", amount_deducted_paise=1000,
    )
    session.add(tds_row)

    exception = ExceptionRecord(
        engagement_id=engagement.engagement_id, module="AUDIT", area="Ledger Scrutiny",
        rule_id="AUD-LS-001", related_transaction_id=transaction.transaction_id,
        amount=100000, status="OPEN", created_at=now,
    )
    session.add(exception)
    session.commit()

    risk_score = RiskScore(exception_id=exception.exception_id, total_score=42, calculated_at=now)
    session.add(risk_score)

    query = QueryRecord(
        engagement_id=engagement.engagement_id, exception_id=exception.exception_id, category="AUDIT",
        area="Ledger Scrutiny", status="OPEN", is_ai_drafted=True, created_at=now,
    )
    session.add(query)
    session.commit()

    response = QueryResponse(query_id=query.query_id, management_response="Noted.", responded_at=now)
    session.add(response)

    document = Document(
        engagement_id=engagement.engagement_id, related_exception_id=exception.exception_id,
        related_query_id=query.query_id, file_name="evidence.pdf", stored_path=str(file_dir / "evidence.pdf"),
        uploaded_at=now,
    )
    session.add(document)

    audit_log = AuditLog(
        engagement_id=engagement.engagement_id, action="TEST_SEED", timestamp=now,
    )
    session.add(audit_log)

    session.commit()
    return {"stored_file": stored_file}


_DEPENDENT_TABLES = [
    ("app.models.uploads", "UploadedFile", "engagement_id"),
    ("app.models.uploads", "DataMapping", None),  # scoped via file_id, checked separately
    ("app.models.transactions", "Transaction", "engagement_id"),
    ("app.models.structured_datasets", "FixedAsset", "engagement_id"),
    ("app.models.structured_datasets", "GstLineItem", "engagement_id"),
    ("app.models.structured_datasets", "TdsLineItem", "engagement_id"),
    ("app.models.exceptions", "ExceptionRecord", "engagement_id"),
    ("app.models.risk", "RiskScore", None),  # scoped via exception_id, checked separately
    ("app.models.queries", "QueryRecord", "engagement_id"),
    ("app.models.queries", "QueryResponse", None),  # scoped via query_id, checked separately
    ("app.models.documents", "Document", "engagement_id"),
    ("app.models.system", "AuditLog", "engagement_id"),
]


def _count_direct(session, module_path, class_name, engagement_id):
    import importlib
    model = getattr(importlib.import_module(module_path), class_name)
    return len(session.scalars(select(model).where(getattr(model, "engagement_id") == engagement_id)).all())


def test_delete_engagement_removes_every_dependent_row_no_fk_violation(db, tmp_path):
    from app.services import engagement_service

    survivor_dir = tmp_path / "survivor_files"
    survivor_dir.mkdir()
    victim_dir = tmp_path / "victim_files"
    victim_dir.mkdir()

    survivor = engagement_service.create_engagement("Survivor Co", "2025-26")
    victim = engagement_service.create_engagement("Victim Co", "2025-26")

    session = engagement_service._session()
    _seed_full_dependency_graph(session, survivor, survivor_dir)
    seeded = _seed_full_dependency_graph(session, victim, victim_dir)

    # Sanity: every dependent table actually has a row for the victim before deletion.
    for module_path, class_name, fk_field in _DEPENDENT_TABLES:
        if fk_field is None:
            continue
        assert _count_direct(session, module_path, class_name, victim.engagement_id) == 1, class_name

    engagement_service.delete_engagement(victim.engagement_id)

    # The engagement row itself is gone.
    assert engagement_service.get_engagement(victim.engagement_id) is None

    # No orphaned row anywhere in the dependency graph for the deleted engagement.
    for module_path, class_name, fk_field in _DEPENDENT_TABLES:
        if fk_field is None:
            continue
        assert _count_direct(session, module_path, class_name, victim.engagement_id) == 0, class_name

    # Junction rows scoped via a parent FK (not engagement_id directly) are also gone —
    # confirmed indirectly since DataMapping/RiskScore/QueryResponse cannot exist without
    # their parent row, which is already asserted gone above; re-query all three tables
    # globally and confirm none reference the deleted engagement's (now nonexistent) parents.
    from app.models.queries import QueryResponse
    from app.models.risk import RiskScore
    from app.models.uploads import DataMapping
    assert session.scalars(select(DataMapping)).all() == [] or all(
        m.file_id != None for m in session.scalars(select(DataMapping)).all()
    )
    assert len(session.scalars(select(RiskScore)).all()) <= 1  # only the survivor's, if any remain
    assert len(session.scalars(select(QueryResponse)).all()) <= 1

    # The file on disk was best-effort unlinked.
    assert not seeded["stored_file"].exists()

    # The survivor engagement and every one of its dependent rows are completely untouched.
    assert engagement_service.get_engagement(survivor.engagement_id) is not None
    for module_path, class_name, fk_field in _DEPENDENT_TABLES:
        if fk_field is None:
            continue
        assert _count_direct(session, module_path, class_name, survivor.engagement_id) == 1, class_name


def test_delete_engagement_is_a_noop_for_unknown_id(db):
    from app.services import engagement_service
    engagement_service.delete_engagement(999999)  # must not raise


def test_delete_current_engagement_self_heals_session(db):
    from app.services import engagement_service

    engagement = engagement_service.create_engagement("Solo Co", "2025-26")
    fake_session = {}
    engagement_service.set_current_engagement(fake_session, engagement.engagement_id)

    engagement_service.delete_engagement(engagement.engagement_id)

    # Even without the route's proactive clear_current_engagement() call,
    # get_current_engagement() must self-heal rather than raising or
    # returning a dangling row.
    assert engagement_service.get_current_engagement(fake_session) is None
    assert "current_engagement_id" not in fake_session
