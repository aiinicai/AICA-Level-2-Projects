"""Tests for core.integrity_engine: QR/Doc-ID stamping and local hash-registry verification."""
from __future__ import annotations

import fitz
import pytest

from core.integrity_engine import (
    compute_sha256,
    extract_document_id,
    generate_document_id,
    register_final_hash,
    stamp_document_id,
    verify_file,
)
from core.watermark_engine import TextWatermarkOptions, add_text_watermark
from utils.database import Database


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "test.db")


def _pdf(path, text="Original content."):
    doc = fitz.open()
    doc.new_page(width=595, height=842).insert_text((72, 100), text)
    doc.save(str(path))
    doc.close()
    return path


def test_generate_document_id_is_unique_and_well_formed():
    ids = {generate_document_id() for _ in range(50)}
    assert len(ids) == 50
    assert all(len(i) == 12 for i in ids)


def test_stamp_document_id_embeds_readable_id(tmp_path):
    src = _pdf(tmp_path / "doc.pdf")
    out = tmp_path / "stamped.pdf"
    result = stamp_document_id(src, out)
    found_id = extract_document_id(out)
    assert found_id == result.document_id


def test_stamp_uses_provided_document_id_when_given(tmp_path):
    src = _pdf(tmp_path / "doc.pdf")
    out = tmp_path / "stamped.pdf"
    result = stamp_document_id(src, out, document_id="ABCDEF123456")
    assert result.document_id == "ABCDEF123456"
    assert extract_document_id(out) == "ABCDEF123456"


def test_extract_document_id_returns_none_when_absent(tmp_path):
    src = _pdf(tmp_path / "doc.pdf")
    assert extract_document_id(src) is None


def test_full_workflow_stamp_process_register_verify(tmp_path, db):
    src = _pdf(tmp_path / "doc.pdf")
    stamped = tmp_path / "stamped.pdf"
    stamp_result = stamp_document_id(src, stamped)

    # Further processing happens AFTER stamping (order matters -- the ID must
    # be fixed before any content that follows it).
    final = tmp_path / "final.pdf"
    add_text_watermark(stamped, final, TextWatermarkOptions(text="FINAL"))

    register_final_hash(db, stamp_result.document_id, final, operator="CA Kishor Singh")

    result = verify_file(final, db)
    assert result.registered_locally
    assert result.hash_matches is True
    assert result.current_sha256 == compute_sha256(final)


def test_verify_detects_tampering_after_registration(tmp_path, db):
    src = _pdf(tmp_path / "doc.pdf")
    stamped = tmp_path / "stamped.pdf"
    stamp_result = stamp_document_id(src, stamped)
    register_final_hash(db, stamp_result.document_id, stamped, operator="tester")

    # Genuine structural tampering (not a raw byte replace, which wouldn't
    # touch the actual encoded/compressed content stream).
    tampered = tmp_path / "tampered.pdf"
    with fitz.open(str(stamped)) as doc:
        doc.new_page(width=595, height=842).insert_text((72, 100), "Injected page.")
        doc.save(str(tampered))

    result = verify_file(tampered, db)
    assert result.registered_locally
    assert result.hash_matches is False


def test_verify_unregistered_document_id_reports_not_registered(tmp_path, db):
    src = _pdf(tmp_path / "doc.pdf")
    stamped = tmp_path / "stamped.pdf"
    stamp_document_id(src, stamped)  # never registered
    result = verify_file(stamped, db)
    assert result.document_id is not None
    assert result.registered_locally is False
    assert result.hash_matches is None


def test_verify_file_with_no_stamp_at_all(tmp_path, db):
    src = _pdf(tmp_path / "unrelated.pdf", "Never touched by this system.")
    result = verify_file(src, db)
    assert result.document_id is None
    assert result.registered_locally is False
    assert result.hash_matches is None


def test_position_presets_produce_valid_output(tmp_path):
    from models.enums import PositionPreset

    src = _pdf(tmp_path / "doc.pdf")
    for preset in (PositionPreset.BOTTOM_LEFT, PositionPreset.BOTTOM_RIGHT, PositionPreset.TOP_LEFT, PositionPreset.TOP_RIGHT):
        out = tmp_path / f"stamped_{preset.name}.pdf"
        result = stamp_document_id(src, out, position=preset)
        assert extract_document_id(out) == result.document_id


def test_original_file_untouched_by_stamping(tmp_path):
    src = _pdf(tmp_path / "doc.pdf")
    original = src.read_bytes()
    stamp_document_id(src, tmp_path / "out.pdf")
    assert src.read_bytes() == original


def test_re_registering_same_document_id_updates_record(tmp_path, db):
    src = _pdf(tmp_path / "doc.pdf")
    stamped = tmp_path / "stamped.pdf"
    result = stamp_document_id(src, stamped)

    register_final_hash(db, result.document_id, stamped, operator="first")
    record = db.get_integrity_record(result.document_id)
    assert record["operator"] == "first"

    register_final_hash(db, result.document_id, stamped, operator="second")
    record = db.get_integrity_record(result.document_id)
    assert record["operator"] == "second"
