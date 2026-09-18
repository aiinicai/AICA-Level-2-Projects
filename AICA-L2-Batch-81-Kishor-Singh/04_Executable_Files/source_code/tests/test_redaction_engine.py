"""Tests for core.redaction_engine: candidate detection and genuine content removal."""
from __future__ import annotations

import fitz
import pytest

from core.redaction_engine import (
    RedactionPatternKind,
    apply_redactions,
    find_redaction_candidates,
    verify_redaction,
)
from utils.validation import ValidationError


def _make_pdf_with_sensitive_data(path):
    doc = fitz.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((72, 100), "Client PAN: ABCDE1234F", fontsize=14)
    p.insert_text((72, 130), "GSTIN: 29ABCDE1234F1Z5", fontsize=14)
    p.insert_text((72, 160), "Aadhaar: 1234 5678 9012", fontsize=14)
    p.insert_text((72, 190), "Email: client@example.com", fontsize=14)
    p.insert_text((72, 220), "Mobile: 9876543210", fontsize=14)
    p.insert_text((72, 250), "This sentence must remain untouched after redaction.", fontsize=14)
    doc.save(str(path))
    doc.close()
    return path


def test_finds_pan_gstin_aadhaar_email_phone(tmp_path):
    src = _make_pdf_with_sensitive_data(tmp_path / "doc.pdf")
    candidates = find_redaction_candidates(src)
    found_kinds = {c.pattern_name for c in candidates}
    assert RedactionPatternKind.PAN in found_kinds
    assert RedactionPatternKind.GSTIN in found_kinds
    assert RedactionPatternKind.AADHAAR_LIKE in found_kinds
    assert RedactionPatternKind.EMAIL in found_kinds
    assert RedactionPatternKind.PHONE in found_kinds


def test_apply_redactions_genuinely_removes_content(tmp_path):
    src = _make_pdf_with_sensitive_data(tmp_path / "doc.pdf")
    candidates = find_redaction_candidates(src)
    for c in candidates:
        c.approved = True

    out = tmp_path / "redacted.pdf"
    applied = apply_redactions(src, out, candidates)
    # >= not == : the PAN's digits are also a literal substring of the GSTIN
    # (Indian GSTIN format embeds the entity's PAN as characters 3-12), so the
    # PAN candidate legitimately produces two redaction boxes on this page.
    assert applied >= len(candidates)

    still_present = verify_redaction(out, [c.matched_text for c in candidates])
    assert still_present == []

    with fitz.open(str(out)) as doc:
        remaining = doc[0].get_text()
    assert "untouched" in remaining.lower()


def test_unapproved_candidates_are_not_redacted(tmp_path):
    src = _make_pdf_with_sensitive_data(tmp_path / "doc.pdf")
    candidates = find_redaction_candidates(src)
    for c in candidates:
        c.approved = False  # explicitly not approved

    with pytest.raises(ValidationError):
        apply_redactions(src, tmp_path / "out.pdf", candidates)


def test_only_approved_subset_is_redacted(tmp_path):
    src = _make_pdf_with_sensitive_data(tmp_path / "doc.pdf")
    candidates = find_redaction_candidates(src)
    pan_candidate = next(c for c in candidates if c.pattern_name == RedactionPatternKind.PAN)
    email_candidate = next(c for c in candidates if c.pattern_name == RedactionPatternKind.EMAIL)
    pan_candidate.approved = True  # only redact the PAN, leave the email

    out = tmp_path / "partial.pdf"
    applied = apply_redactions(src, out, candidates)
    # 2, not 1: the PAN also appears embedded inside the (unapproved) GSTIN
    # text -- both literal occurrences of the approved PAN value are redacted.
    assert applied == 2

    still_present = verify_redaction(out, [pan_candidate.matched_text, email_candidate.matched_text])
    assert pan_candidate.matched_text not in still_present
    assert email_candidate.matched_text in still_present


def test_original_file_untouched_by_redaction(tmp_path):
    src = _make_pdf_with_sensitive_data(tmp_path / "doc.pdf")
    original_bytes = src.read_bytes()
    candidates = find_redaction_candidates(src)
    for c in candidates:
        c.approved = True
    apply_redactions(src, tmp_path / "out.pdf", candidates)
    assert src.read_bytes() == original_bytes


def test_no_candidates_found_in_clean_document(tmp_path):
    doc = fitz.open()
    doc.new_page(width=595, height=842).insert_text((72, 100), "Nothing sensitive here.")
    src = tmp_path / "clean.pdf"
    doc.save(str(src))
    doc.close()
    candidates = find_redaction_candidates(src, pattern_names=[RedactionPatternKind.PAN, RedactionPatternKind.EMAIL])
    assert candidates == []
