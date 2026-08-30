"""
Stage 7 — app/services/mapping_service.py (real SQLAlchemy 2.x ORM
persistence). Run with:

    pip install -r requirements.txt
    pytest tests/unit/test_mapping_service.py -v

NOTE ON THIS SANDBOX: same real-Flask + shimmed-SQLAlchemy-over-real-
SQLite setup as tests/unit/test_upload_service.py — see that file's
docstring / the Stage 5 delivery notes for what the shim does and does
not implement.

Uses only synthetic, fabricated data — never real client/financial
data, per the standing instruction.
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import pytest


@pytest.fixture()
def svc(tmp_path):
    from sqlalchemy import create_engine

    from app import extensions
    from app.models import Base

    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    extensions.engine = engine

    from sqlalchemy.orm import scoped_session, sessionmaker
    extensions.SessionLocal = scoped_session(sessionmaker(bind=engine, future=True, expire_on_commit=False))

    from app.services import engagement_service, mapping_service, upload_service

    engagement = engagement_service.create_engagement("Acme Manufacturing Ltd", "2025-26")

    buf = io.BytesIO()
    pd.DataFrame([{"Account": "Cash", "Debit": 100000, "Credit": 0}]).to_csv(buf, index=False)
    uploaded_file_record = upload_service.save_uploaded_file(
        engagement_id=engagement.engagement_id,
        original_filename="trial_balance.csv",
        file_type="TB",
        file_bytes=buf.getvalue(),
        input_dir=tmp_path / "data_input",
    )

    class _Bundle:
        mapping = mapping_service
        upload = upload_service
        file_id = uploaded_file_record.file_id

    yield _Bundle

    extensions.SessionLocal.remove()


def test_no_confirmed_mappings_initially(svc):
    assert svc.mapping.get_confirmed_mappings(svc.file_id) == []


def test_confirm_mappings_persists_them_as_user_confirmed(svc):
    confirmed = svc.mapping.confirm_mappings(svc.file_id, [
        {"source_column": "Account", "target_field": "account_name", "confidence_score": 1.0},
        {"source_column": "Debit", "target_field": "debit_amount", "confidence_score": 1.0},
    ])
    assert len(confirmed) == 2
    for row in confirmed:
        assert row.is_user_confirmed is True
        assert row.confirmed_at is not None

    reloaded = svc.mapping.get_confirmed_mappings(svc.file_id)
    assert {m.source_column for m in reloaded} == {"Account", "Debit"}


def test_resubmitting_mappings_without_a_previously_confirmed_column_removes_it(svc):
    svc.mapping.confirm_mappings(svc.file_id, [
        {"source_column": "Account", "target_field": "account_name", "confidence_score": 1.0},
        {"source_column": "Debit", "target_field": "debit_amount", "confidence_score": 1.0},
    ])
    # Second submission only maps "Account" — "Debit" was unmapped by the user.
    svc.mapping.confirm_mappings(svc.file_id, [
        {"source_column": "Account", "target_field": "account_name", "confidence_score": 1.0},
    ])
    reloaded = svc.mapping.get_confirmed_mappings(svc.file_id)
    assert {m.source_column for m in reloaded} == {"Account"}


def test_confirming_again_with_a_different_target_field_updates_in_place(svc):
    svc.mapping.confirm_mappings(svc.file_id, [
        {"source_column": "Account", "target_field": "account_name", "confidence_score": 1.0},
    ])
    svc.mapping.confirm_mappings(svc.file_id, [
        {"source_column": "Account", "target_field": "party_name", "confidence_score": 0.6},
    ])
    reloaded = svc.mapping.get_confirmed_mappings(svc.file_id)
    assert len(reloaded) == 1
    assert reloaded[0].target_field == "party_name"


def test_mark_file_status_updates_upload_status(svc):
    svc.mapping.mark_file_status(svc.file_id, "MAPPED")
    record = svc.upload.get_upload(svc.file_id)
    assert record.upload_status == "MAPPED"
