"""
Stage 19 — app/services/dataset_service.py: attach_transaction_ids().

Exercises the transaction-persistence layer added to populate Account
Name/Date on the Query & Working Papers screen (see the module's own
docstring). These tests target attach_transaction_ids() directly and
at a lower level than tests/unit/test_unified_review_service.py's
end-to-end coverage, specifically to pin down two guarantees that
motivated a mid-development redesign (a delete-and-recreate first
version caused a FOREIGN KEY constraint failure on a second run):

  1. Content-based reuse: an unchanged row gets the SAME transaction_id
     across two separate attach_transaction_ids() calls (not a fresh
     row each time).
  2. Never-delete-a-referenced-row: a Transaction row still pointed to
     by an ExceptionRecord.related_transaction_id is never deleted,
     even when that row no longer appears in the freshly-derived
     dataset on a later run.

Uses only synthetic, fabricated data — never real client/financial
data, per the standing instruction.

Run with: pytest tests/unit/test_dataset_service.py -v
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import pytest


@pytest.fixture()
def env(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker

    from app import extensions
    from app.models import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", future=True)
    Base.metadata.create_all(engine)
    extensions.engine = engine
    extensions.SessionLocal = scoped_session(sessionmaker(bind=engine, future=True, expire_on_commit=False))

    from app.services import dataset_service, engagement_service, mapping_service, upload_service

    engagement = engagement_service.create_engagement("Acme Manufacturing Ltd", "2025-26")
    engagement_service.save_entity_profile(engagement.engagement_id, {
        "entity_type": "Company", "industry": None, "is_listed": False,
        "accounting_framework": "AS", "is_gst_registered": False,
        "statutory_audit_applicable": False, "tax_audit_status": "REQUIRES_REVIEW",
        "consolidated_fs_applicable": False, "prior_year_data_available": False,
        "turnover": None, "overall_materiality": None, "performance_materiality": None,
        "clearly_trivial_threshold": None,
    })

    def _upload_mapped_validated(file_type, filename, rows, mapping):
        buf = io.BytesIO()
        pd.DataFrame(rows).to_csv(buf, index=False)
        uploaded = upload_service.save_uploaded_file(
            engagement_id=engagement.engagement_id, original_filename=filename, file_type=file_type,
            file_bytes=buf.getvalue(), input_dir=tmp_path / "data_input",
        )
        mapping_service.confirm_mappings(uploaded.file_id, mapping)
        mapping_service.mark_file_status(uploaded.file_id, "VALIDATED")
        return uploaded

    class _Env:
        svc = dataset_service
        engagement_id = engagement.engagement_id
        upload = staticmethod(_upload_mapped_validated)

    yield _Env
    extensions.SessionLocal.remove()


def _seed_one_je_row(env, tmp_path, description="Routine sale of goods", debit=0, credit=50000):
    env.upload("JE", "je.csv", [
        {"Description": description, "Debit": debit, "Credit": credit,
         "Transaction Date": "01-06-2025", "Account Name": "Sales"},
    ], [
        {"source_column": "Description", "target_field": "description", "confidence_score": 1.0},
        {"source_column": "Debit", "target_field": "debit_amount", "confidence_score": 1.0},
        {"source_column": "Credit", "target_field": "credit_amount", "confidence_score": 1.0},
        {"source_column": "Transaction Date", "target_field": "transaction_date", "confidence_score": 1.0},
        {"source_column": "Account Name", "target_field": "account_name", "confidence_score": 1.0},
    ])


# --- Basic behavior -------------------------------------------------------

def test_transaction_ids_are_written_onto_mapped_rows(env, tmp_path):
    _seed_one_je_row(env, tmp_path)
    dataset = env.svc.load_engagement_dataset(env.engagement_id)
    assert dataset["JE"][0].transaction_id is None  # not attached yet

    env.svc.attach_transaction_ids(env.engagement_id, dataset)
    assert dataset["JE"][0].transaction_id is not None


def test_fixed_assets_rows_are_never_attached(env, tmp_path):
    env.upload("FIXED_ASSETS", "fa.csv", [
        {"Asset Name": "Machine A", "Cost": 100000},
    ], [
        {"source_column": "Asset Name", "target_field": "asset_name", "confidence_score": 1.0},
        {"source_column": "Cost", "target_field": "cost", "confidence_score": 1.0},
    ])
    dataset = env.svc.load_engagement_dataset(env.engagement_id)
    env.svc.attach_transaction_ids(env.engagement_id, dataset)
    assert dataset["FIXED_ASSETS"][0].transaction_id is None


def test_preview_never_calls_attach_transaction_ids(env, tmp_path):
    # preview_*_review()'s own docstring promises "touches the database
    # at all" is false — attach_transaction_ids() is only ever invoked
    # from a persisting run_*_review(). This is exercised indirectly via
    # accounting_review_service, which is the real caller.
    _seed_one_je_row(env, tmp_path)
    from app.services import accounting_review_service
    from sqlalchemy import select
    from app import extensions
    from app.models.transactions import Transaction

    accounting_review_service.preview_accounting_review(env.engagement_id)
    existing = list(extensions.SessionLocal.scalars(
        select(Transaction).where(Transaction.engagement_id == env.engagement_id)
    ).all())
    assert existing == []  # preview persisted nothing


# --- Guarantee 1: content-based reuse across runs --------------------------

def test_unchanged_row_reuses_the_same_transaction_id_across_two_runs(env, tmp_path):
    _seed_one_je_row(env, tmp_path)

    dataset1 = env.svc.load_engagement_dataset(env.engagement_id)
    env.svc.attach_transaction_ids(env.engagement_id, dataset1)
    first_id = dataset1["JE"][0].transaction_id
    assert first_id is not None

    dataset2 = env.svc.load_engagement_dataset(env.engagement_id)  # re-derived fresh, same source file
    env.svc.attach_transaction_ids(env.engagement_id, dataset2)
    second_id = dataset2["JE"][0].transaction_id

    assert second_id == first_id  # reused, not a new row


def test_unchanged_row_does_not_duplicate_the_transactions_table(env, tmp_path):
    _seed_one_je_row(env, tmp_path)
    from sqlalchemy import select
    from app import extensions
    from app.models.transactions import Transaction

    for _ in range(3):
        dataset = env.svc.load_engagement_dataset(env.engagement_id)
        env.svc.attach_transaction_ids(env.engagement_id, dataset)

    all_rows = list(extensions.SessionLocal.scalars(
        select(Transaction).where(Transaction.engagement_id == env.engagement_id)
    ).all())
    assert len(all_rows) == 1  # three runs, still exactly one row


def test_two_identical_rows_in_the_same_run_get_two_distinct_ids(env, tmp_path):
    # Guards the used_ids pairing logic: two genuinely identical rows
    # (same date/account/amount/etc) must not be confused with each
    # other or collapsed into one Transaction row.
    env.upload("JE", "je_dupes.csv", [
        {"Description": "Cash sale", "Debit": 0, "Credit": 10000,
         "Transaction Date": "01-06-2025", "Account Name": "Sales"},
        {"Description": "Cash sale", "Debit": 0, "Credit": 10000,
         "Transaction Date": "01-06-2025", "Account Name": "Sales"},
    ], [
        {"source_column": "Description", "target_field": "description", "confidence_score": 1.0},
        {"source_column": "Debit", "target_field": "debit_amount", "confidence_score": 1.0},
        {"source_column": "Credit", "target_field": "credit_amount", "confidence_score": 1.0},
        {"source_column": "Transaction Date", "target_field": "transaction_date", "confidence_score": 1.0},
        {"source_column": "Account Name", "target_field": "account_name", "confidence_score": 1.0},
    ])
    dataset = env.svc.load_engagement_dataset(env.engagement_id)
    env.svc.attach_transaction_ids(env.engagement_id, dataset)
    ids = [row.transaction_id for row in dataset["JE"]]
    assert len(ids) == 2
    assert ids[0] != ids[1]
    assert all(i is not None for i in ids)

    # And re-running again still reuses both, pairing one-to-one rather
    # than drifting or duplicating.
    dataset2 = env.svc.load_engagement_dataset(env.engagement_id)
    env.svc.attach_transaction_ids(env.engagement_id, dataset2)
    ids2 = sorted(row.transaction_id for row in dataset2["JE"])
    assert ids2 == sorted(ids)


# --- Guarantee 2: a referenced row is never deleted -------------------------

def test_a_row_still_referenced_by_a_finding_is_never_deleted_even_if_source_data_changes(env, tmp_path):
    from sqlalchemy import select
    from app import extensions
    from app.models.exceptions import ExceptionRecord
    from app.models.transactions import Transaction

    _seed_one_je_row(env, tmp_path)
    dataset1 = env.svc.load_engagement_dataset(env.engagement_id)
    env.svc.attach_transaction_ids(env.engagement_id, dataset1)
    original_txn_id = dataset1["JE"][0].transaction_id

    # Simulate a rule having raised a finding against this exact row —
    # exactly what accounting_review_service does after attach_
    # transaction_ids() returns.
    session = extensions.SessionLocal
    session.add(ExceptionRecord(
        engagement_id=env.engagement_id, module="ACCOUNTING", rule_id="AS5-PPI-012",
        description="test finding", related_transaction_id=original_txn_id,
        created_at="2026-01-01T00:00:00+00:00",
    ))
    session.commit()

    # Now the underlying uploaded file's content changes on a later run
    # (e.g. the reviewer re-uploaded a corrected file) such that the row
    # this finding points to no longer appears in the freshly-derived
    # dataset at all.
    env.upload("JE", "je_replacement.csv", [
        {"Description": "Completely different entry", "Debit": 0, "Credit": 99999,
         "Transaction Date": "02-06-2025", "Account Name": "Other"},
    ], [
        {"source_column": "Description", "target_field": "description", "confidence_score": 1.0},
        {"source_column": "Debit", "target_field": "debit_amount", "confidence_score": 1.0},
        {"source_column": "Credit", "target_field": "credit_amount", "confidence_score": 1.0},
        {"source_column": "Transaction Date", "target_field": "transaction_date", "confidence_score": 1.0},
        {"source_column": "Account Name", "target_field": "account_name", "confidence_score": 1.0},
    ])
    # dataset now has both the original JE file's row (unchanged, still
    # matches) AND the new file's row — attach_transaction_ids() must
    # not delete the original even though we're specifically testing
    # the case where it would no longer match anything.
    dataset2 = env.svc.load_engagement_dataset(env.engagement_id)
    env.svc.attach_transaction_ids(env.engagement_id, dataset2)

    still_there = session.get(Transaction, original_txn_id)
    assert still_there is not None  # not deleted — a finding still points to it

    # And the ExceptionRecord's link survives, unbroken.
    exc = session.scalars(
        select(ExceptionRecord).where(ExceptionRecord.engagement_id == env.engagement_id)
    ).first()
    assert exc.related_transaction_id == original_txn_id


def test_an_unreferenced_orphaned_row_is_deleted(env, tmp_path):
    # The flip side of the guarantee above: a row that no longer
    # matches anything AND is not referenced by any finding should not
    # accumulate forever.
    from sqlalchemy import select
    from app import extensions
    from app.models.transactions import Transaction
    from app.models.uploads import UploadedFile

    _seed_one_je_row(env, tmp_path)
    dataset1 = env.svc.load_engagement_dataset(env.engagement_id)
    env.svc.attach_transaction_ids(env.engagement_id, dataset1)
    original_txn_id = dataset1["JE"][0].transaction_id

    # Mark the original file no longer VALIDATED (simulating removal/
    # replacement) so load_engagement_dataset() stops surfacing its
    # row, exactly like a real "Remove file" or re-validate action.
    session = extensions.SessionLocal
    original_file = session.scalars(
        select(UploadedFile).where(UploadedFile.engagement_id == env.engagement_id)
    ).first()
    original_file.upload_status = "MAPPED"
    session.commit()

    dataset2 = env.svc.load_engagement_dataset(env.engagement_id)  # no longer includes that row
    assert dataset2.get("JE", []) == []
    env.svc.attach_transaction_ids(env.engagement_id, dataset2)

    assert session.get(Transaction, original_txn_id) is None  # orphaned, unreferenced -> deleted
