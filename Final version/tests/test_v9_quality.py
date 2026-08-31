import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import DIN_PATTERN, KNOWN_IT_SECTIONS, STATE_KEYS
from engines.draft_risk_checker import DraftRiskChecker
from app import redact_sensitive_text_for_ai


def test_admission_risk_accept_that_flagged():
    findings = DraftRiskChecker.run_passes_a_to_d(
        "I accept that the amount was not disclosed.",
        "No extraction required",
    )
    assert any(f["pass"] == "D" and "Outright admission" in f["issue"] for f in findings)


def test_realistic_din_patterns():
    samples = [
        "ITBA/AST/F/143(3)(SCN)/2025-26/1086168255(1)",
        "ITBA/NFAC/2024/1234567890",
        "ITBA/COM/F/17/2024-25/1234567890",
    ]
    assert all(DIN_PATTERN.search(sample) for sample in samples)


def test_common_sections_are_valid():
    for section in ["139(1)", "143(3)", "80CCD(2)", "271(1)(c)"]:
        assert section in KNOWN_IT_SECTIONS
    draft = "Section 139(1), Section 143(3), Section 80CCD(2), Section 271(1)(c)"
    assert DraftRiskChecker.run_passes_a_to_d(draft, draft) == []


def test_pii_masking_core_ids():
    text = (
        "PAN ABCDE1234F GSTIN 27ABCDE1234F1Z5 Aadhaar 1234 5678 9012 "
        "mobile 9876543210 email x@example.com IFSC HDFC0001234 "
        "CIN U12345MH2020PLC123456 TAN ABCD12345E Account No 123456789012"
    )
    masked, counts = redact_sensitive_text_for_ai(text)
    assert "ABCDE1234F" not in masked
    assert "27ABCDE1234F1Z5" not in masked
    assert "1234 5678 9012" not in masked
    assert "9876543210" not in masked
    assert "x@example.com" not in masked
    assert "HDFC0001234" not in masked
    assert "U12345MH2020PLC123456" not in masked
    assert "ABCD12345E" not in masked
    assert counts


def test_state_key_count_for_restore_contract():
    assert len(STATE_KEYS) >= 21
