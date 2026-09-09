"""
Stage 6 — app/services/upload_service.py (real SQLAlchemy 2.x ORM
persistence + safe file handling). Run with:

    pip install -r requirements.txt
    pytest tests/unit/test_upload_service.py -v

NOTE ON THIS SANDBOX: ran for real under `pytest`, but NOT against real
SQLAlchemy — it's still uninstallable here (network to PyPI/apt
confirmed 403 again during Stage 5). What makes this file executable at
all: a genuinely real Flask 3.1.3 this sandbox happens to have cached,
real pandas/openpyxl (also genuinely available here — used for real,
not stubbed), and a scoped SQLAlchemy 2.x declarative-ORM shim (not
part of this repo) that layers real Python<->SQL row mapping on a real,
on-disk SQLite database. See the Stage 5 delivery notes for what the
shim does and does not implement. This file's assertions run unmodified
against real SQLAlchemy once it's installed.

Uses only synthetic, fabricated data (fake trial balance / GL rows) —
never real client or financial data, per the standing instruction.
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import pytest


@pytest.fixture()
def svc(tmp_path):
    """A fresh upload_service + engagement_service pair, wired to a
    fresh, empty, real SQLite database for this one test, plus a
    scratch `input_dir` for uploaded files to land in."""
    from sqlalchemy import create_engine

    from app import extensions
    from app.models import Base

    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    extensions.engine = engine

    from sqlalchemy.orm import scoped_session, sessionmaker
    extensions.SessionLocal = scoped_session(sessionmaker(bind=engine, future=True, expire_on_commit=False))

    from app.services import engagement_service
    from app.services import upload_service

    engagement = engagement_service.create_engagement("Acme Manufacturing Ltd", "2025-26")

    class _Bundle:
        upload = upload_service
        engagement_id = engagement.engagement_id
        input_dir = tmp_path / "data_input"

    yield _Bundle

    extensions.SessionLocal.remove()


# --- Synthetic test data (never real client/financial data) ---------------

SYNTHETIC_TB_ROWS = [
    {"account": "Cash", "debit": 100000, "credit": 0},
    {"account": "Sales", "debit": 0, "credit": 100000},
]


def _csv_bytes(rows) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue()


def _xlsx_bytes(rows) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


def test_save_uploaded_csv_persists_with_correct_row_count(svc):
    record = svc.upload.save_uploaded_file(
        engagement_id=svc.engagement_id,
        original_filename="trial_balance.csv",
        file_type="TB",
        file_bytes=_csv_bytes(SYNTHETIC_TB_ROWS),
        input_dir=svc.input_dir,
    )
    assert record.file_id is not None
    assert record.row_count == 2  # header excluded
    assert record.upload_status == "UPLOADED"
    assert record.checksum is not None
    assert Path(record.stored_path).exists()


def test_save_uploaded_xlsx_persists_with_correct_row_count(svc):
    record = svc.upload.save_uploaded_file(
        engagement_id=svc.engagement_id,
        original_filename="general_ledger.xlsx",
        file_type="GL",
        file_bytes=_xlsx_bytes(SYNTHETIC_TB_ROWS),
        input_dir=svc.input_dir,
    )
    assert record.row_count == 2
    assert Path(record.stored_path).suffix == ".xlsx"


def test_duplicate_upload_same_engagement_same_checksum_rejected(svc):
    file_bytes = _csv_bytes(SYNTHETIC_TB_ROWS)
    svc.upload.save_uploaded_file(
        engagement_id=svc.engagement_id, original_filename="trial_balance.csv",
        file_type="TB", file_bytes=file_bytes, input_dir=svc.input_dir,
    )
    with pytest.raises(svc.upload.DuplicateUploadError):
        svc.upload.save_uploaded_file(
            engagement_id=svc.engagement_id, original_filename="trial_balance_copy.csv",
            file_type="TB", file_bytes=file_bytes, input_dir=svc.input_dir,
        )
    # The rejected duplicate must not have been persisted a second time.
    assert len(svc.upload.list_uploads(svc.engagement_id)) == 1


def test_same_content_different_engagement_is_not_a_duplicate(svc):
    from app.services import engagement_service
    other_engagement = engagement_service.create_engagement("Beta Traders LLP", "2025-26")
    file_bytes = _csv_bytes(SYNTHETIC_TB_ROWS)

    svc.upload.save_uploaded_file(
        engagement_id=svc.engagement_id, original_filename="trial_balance.csv",
        file_type="TB", file_bytes=file_bytes, input_dir=svc.input_dir,
    )
    # Must NOT raise — same bytes, different engagement.
    record = svc.upload.save_uploaded_file(
        engagement_id=other_engagement.engagement_id, original_filename="trial_balance.csv",
        file_type="TB", file_bytes=file_bytes, input_dir=svc.input_dir,
    )
    assert record.engagement_id == other_engagement.engagement_id


def test_unreadable_file_rejected_and_nothing_persisted_or_written(svc):
    garbage = b"this is not a valid csv or xlsx file \x00\x01\x02" * 50
    with pytest.raises(svc.upload.UnreadableFileError):
        svc.upload.save_uploaded_file(
            engagement_id=svc.engagement_id, original_filename="mystery.xlsx",
            file_type="OTHER", file_bytes=garbage, input_dir=svc.input_dir,
        )
    assert svc.upload.list_uploads(svc.engagement_id) == []
    # Nothing should have been written to disk for a rejected upload.
    assert not svc.input_dir.exists() or not any(svc.input_dir.rglob("*"))


def test_stored_filename_is_sanitized_against_path_traversal(svc):
    record = svc.upload.save_uploaded_file(
        engagement_id=svc.engagement_id,
        original_filename="../../../etc/passwd.csv",
        file_type="OTHER",
        file_bytes=_csv_bytes(SYNTHETIC_TB_ROWS),
        input_dir=svc.input_dir,
    )
    stored = Path(record.stored_path).resolve()
    engagement_dir = (svc.input_dir / str(svc.engagement_id)).resolve()
    assert str(stored).startswith(str(engagement_dir))
    assert ".." not in stored.parts


def test_list_uploads_returns_every_upload_for_the_engagement(svc):
    # Not asserting a specific order here: both uploads can legitimately
    # land in the same second (`uploaded_at` has second precision), so
    # asserting "most recent first" would be timing-flaky. What's
    # actually guaranteed — every upload for the engagement comes back,
    # exactly once each — is what's checked.
    svc.upload.save_uploaded_file(
        engagement_id=svc.engagement_id, original_filename="a.csv",
        file_type="TB", file_bytes=_csv_bytes(SYNTHETIC_TB_ROWS), input_dir=svc.input_dir,
    )
    svc.upload.save_uploaded_file(
        engagement_id=svc.engagement_id, original_filename="b.csv",
        file_type="GL", file_bytes=_csv_bytes(SYNTHETIC_TB_ROWS[:1]), input_dir=svc.input_dir,
    )
    uploads = svc.upload.list_uploads(svc.engagement_id)
    assert {u.original_filename for u in uploads} == {"a.csv", "b.csv"}
