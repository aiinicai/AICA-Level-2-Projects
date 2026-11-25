import pytest

from noticemate.core import pii
from noticemate.core.errors import ValidationError
from noticemate.core.security import hash_password, sanitize_filename, validate_upload, verify_password
from noticemate.services.notice_parser import extract_particulars, parse_amount, split_queries
from noticemate.services.taxlaw import determine_applicable_law


def test_pii_redaction_and_verification():
    text = ("PQR Traders PAN AAAFP1234Z GSTIN 27AAAFP1234Z1Z5 email a.b@example.com mobile 9876543210 "
            "A/c No: 123456789012 IFSC ABCD0123456 Aadhaar 2345 6789 0123 amount Rs. 18,00,000")
    r = pii.redact(text, ["PQR Traders"])
    assert r.ok, r.residual
    for leak in ("AAAFP1234Z", "27AAAFP1234Z1Z5", "a.b@example.com", "9876543210", "123456789012", "ABCD0123456", "2345 6789 0123", "PQR Traders"):
        assert leak not in r.redacted_text
    assert "18,00,000" in r.redacted_text  # amounts preserved
    assert r.counts["PARTY_NAME"] == 1


def test_pii_blocks_on_residual():
    assert pii.verify_redaction("contact Rahul Sharma", ["Rahul Sharma"]) == {"PARTY_NAME": 1}


def test_password_hashing_and_policy():
    h = hash_password("Str0ng!Password")
    assert verify_password("Str0ng!Password", h) and not verify_password("wrong", h)
    with pytest.raises(ValidationError):
        hash_password("short")


def test_upload_validation():
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    with pytest.raises(ValidationError):
        validate_upload("x.exe", b"MZ..", 25)
    with pytest.raises(ValidationError):
        validate_upload("fake.pdf", b"not a pdf", 25)


def test_applicable_law_transition():
    old = determine_applicable_law("2026-27", "AY", "2026-11-10")
    assert old["substantive_law"] == "Income-tax Act, 1961"
    assert any("TRANSITION" in f for f in old["flags"]) and old["requires_ca_verification"]
    new = determine_applicable_law("2026-27", "TAX_YEAR")
    assert new["substantive_law"] == "Income-tax Act, 2025"


def test_notice_parser_never_guesses_deadline():
    p = extract_particulars("Notice u/s 142(1)\nAssessment Year 2025-26\nPlease furnish details within 15 days.")
    assert p["section"]["value"] == "142(1)"
    assert "service date NOT PROVIDED" in p["compliance_deadline"]["value"]
    assert p["compliance_deadline"]["needs_verification"] is True
    p2 = extract_particulars("Notice u/s 143(2)")
    assert p2["compliance_deadline"]["value"] == "NOT PROVIDED"
    assert p2["din"]["value"] == "NOT PROVIDED"


def test_amount_and_queries():
    assert parse_amount("Rs. 18,00,000") == 1800000
    assert parse_amount("₹1.5 lakh") == 150000
    q = split_queries("1. Please explain the source of cash deposits of Rs. 5,00,000.\n2. Furnish ledger copies of all loans.\n3. Heading")
    assert len(q) == 2
