"""Tests for core.submission_pack_engine: the CA-specific submission pack builder."""
from __future__ import annotations

import json
import zipfile

import fitz
import pytest

from core.submission_pack_engine import SubmissionPackConfig, SubmissionPackItem, build_submission_pack
from utils.validation import ValidationError


def _pdf(path, pages, label):
    doc = fitz.open()
    for i in range(pages):
        doc.new_page(width=595, height=842).insert_text((72, 100), f"{label} page {i + 1}")
    doc.save(str(path))
    doc.close()
    return path


def test_build_pack_combines_documents_in_order(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "First")
    b = _pdf(tmp_path / "b.pdf", 1, "Second")
    config = SubmissionPackConfig(
        client_name="Test Client", engagement="Test Engagement",
        items=[SubmissionPackItem(file_path=str(a)), SubmissionPackItem(file_path=str(b))],
    )
    result = build_submission_pack(config, tmp_path / "out")

    with fitz.open(result.combined_pdf_path) as doc:
        # No cover letter, no bates -> just TOC page + 2 content pages.
        assert doc.page_count == 3
        assert "First page 1" in doc[1].get_text()
        assert "Second page 1" in doc[2].get_text()


def test_missing_checklist_items_are_flagged(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "Invoice")
    config = SubmissionPackConfig(
        client_name="Test Client", engagement="Test Engagement",
        items=[SubmissionPackItem(file_path=str(a), category="Invoice")],
        checklist=["Invoice", "Bank Statement", "Audit Report"],
    )
    result = build_submission_pack(config, tmp_path / "out")
    assert result.missing_from_checklist == ["Bank Statement", "Audit Report"]


def test_no_missing_when_checklist_fully_covered(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "Invoice")
    config = SubmissionPackConfig(
        client_name="Test Client", engagement="Test Engagement",
        items=[SubmissionPackItem(file_path=str(a), category="Invoice")],
        checklist=["Invoice"],
    )
    result = build_submission_pack(config, tmp_path / "out")
    assert result.missing_from_checklist == []


def test_annexure_labels_auto_assigned_alphabetically(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "A")
    b = _pdf(tmp_path / "b.pdf", 1, "B")
    config = SubmissionPackConfig(
        client_name="Test", engagement="Test",
        items=[SubmissionPackItem(file_path=str(a)), SubmissionPackItem(file_path=str(b))],
    )
    result = build_submission_pack(config, tmp_path / "out")
    assert result.manifest_entries[0].annexure_label == "Annexure A"
    assert result.manifest_entries[1].annexure_label == "Annexure B"


def test_bates_numbering_applied_continuously_across_pack(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 2, "A")
    b = _pdf(tmp_path / "b.pdf", 2, "B")
    config = SubmissionPackConfig(
        client_name="Test", engagement="Test", bates_prefix="ABC-",
        items=[SubmissionPackItem(file_path=str(a)), SubmissionPackItem(file_path=str(b))],
    )
    result = build_submission_pack(config, tmp_path / "out")
    with fitz.open(result.combined_pdf_path) as doc:
        full_text = "\n".join(doc[i].get_text() for i in range(doc.page_count))
        assert "ABC-000001" in full_text
        assert f"ABC-{result.total_pages:06d}" in full_text


def test_manifest_records_correct_page_ranges(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 3, "A")
    b = _pdf(tmp_path / "b.pdf", 2, "B")
    config = SubmissionPackConfig(
        client_name="Test", engagement="Test",
        items=[SubmissionPackItem(file_path=str(a)), SubmissionPackItem(file_path=str(b))],
    )
    result = build_submission_pack(config, tmp_path / "out")
    entry_a, entry_b = result.manifest_entries
    assert entry_a.page_count == 3
    assert entry_b.page_count == 2
    assert entry_b.start_page_in_pack == entry_a.end_page_in_pack + 1


def test_manifest_sha256_matches_actual_source_file(tmp_path):
    import hashlib

    a = _pdf(tmp_path / "a.pdf", 1, "A")
    config = SubmissionPackConfig(client_name="Test", engagement="Test", items=[SubmissionPackItem(file_path=str(a))])
    result = build_submission_pack(config, tmp_path / "out")
    expected = hashlib.sha256(a.read_bytes()).hexdigest()
    assert result.manifest_entries[0].sha256 == expected


def test_cover_letter_appears_as_first_pages(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "A")
    config = SubmissionPackConfig(
        client_name="Kishor Singh and Co.", engagement="Reply",
        items=[SubmissionPackItem(file_path=str(a))],
        cover_letter_text="This is a cover letter for the submission.",
    )
    result = build_submission_pack(config, tmp_path / "out")
    with fitz.open(result.combined_pdf_path) as doc:
        assert "cover letter" in doc[0].get_text().lower()
        assert "Kishor Singh and Co." in doc[0].get_text()


def test_zip_contains_pdf_and_manifest(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "A")
    config = SubmissionPackConfig(client_name="Test", engagement="Test", items=[SubmissionPackItem(file_path=str(a))])
    result = build_submission_pack(config, tmp_path / "out")
    with zipfile.ZipFile(result.zip_path) as zf:
        names = zf.namelist()
        assert any(n.endswith(".pdf") for n in names)
        assert any(n.endswith(".json") for n in names)


def test_manifest_json_is_valid_and_complete(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "A")
    config = SubmissionPackConfig(
        client_name="Kishor Singh and Co.", engagement="Audit", financial_year="FY 2024-25",
        items=[SubmissionPackItem(file_path=str(a), category="Working Paper")],
    )
    result = build_submission_pack(config, tmp_path / "out")
    manifest = json.loads(open(result.manifest_path, encoding="utf-8").read())
    assert manifest["client_name"] == "Kishor Singh and Co."
    assert manifest["financial_year"] == "FY 2024-25"
    assert len(manifest["documents"]) == 1
    assert manifest["documents"][0]["category"] == "Working Paper"


def test_empty_items_list_raises(tmp_path):
    config = SubmissionPackConfig(client_name="Test", engagement="Test", items=[])
    with pytest.raises(ValidationError):
        build_submission_pack(config, tmp_path / "out")


def test_per_item_page_expression_respected(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 5, "A")
    config = SubmissionPackConfig(
        client_name="Test", engagement="Test",
        items=[SubmissionPackItem(file_path=str(a), page_expression="1,3,5")],
    )
    result = build_submission_pack(config, tmp_path / "out")
    assert result.manifest_entries[0].page_count == 3


def test_original_source_files_untouched(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "A")
    original = a.read_bytes()
    config = SubmissionPackConfig(client_name="Test", engagement="Test", items=[SubmissionPackItem(file_path=str(a))])
    build_submission_pack(config, tmp_path / "out")
    assert a.read_bytes() == original
