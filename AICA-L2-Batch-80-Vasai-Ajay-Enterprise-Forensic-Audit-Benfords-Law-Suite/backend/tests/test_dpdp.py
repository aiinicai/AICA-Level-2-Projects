"""
Tests for Indian DPDP Act 2023 Compliance & Security Shell.
"""

import pytest
from backend.app.engine.dpdp_compliance import (
    validate_verhoeff,
    generate_verhoeff,
    validate_pan,
    validate_gstin,
    validate_ifsc,
    mask_aadhaar,
    mask_pan,
    mask_gstin,
    mask_bank_account,
    mask_phone,
    mask_email,
    pseudonymize_value,
    DPDPComplianceEngine,
    HITLSecurityGateway
)


def test_aadhaar_verhoeff_checksum():
    """Validates Verhoeff algorithm on valid Aadhaar numbers and invalid candidates."""
    # Compute valid Aadhaar numbers using exact Verhoeff checksum algorithm
    sample_prefix_1 = "21098765432"
    valid_uid_1 = sample_prefix_1 + generate_verhoeff(sample_prefix_1)
    
    sample_prefix_2 = "99999999001"
    valid_uid_2 = sample_prefix_2 + generate_verhoeff(sample_prefix_2)

    sample_prefix_3 = "54321098765"
    valid_uid_3 = sample_prefix_3 + generate_verhoeff(sample_prefix_3)

    assert validate_verhoeff(valid_uid_1) is True
    assert validate_verhoeff(valid_uid_2) is True
    assert validate_verhoeff(valid_uid_3) is True

    # Invalid Aadhaar numbers (checksum corrupted or starting with 0/1)
    invalid_samples = [
        "999999990010",  # Checksum digit altered
        "012345678901",  # Starts with 0
        "123456789012",  # Starts with 1
        "12345",         # Length < 12
        "ABCD12345678"   # Non-numeric
    ]
    for uid in invalid_samples:
        assert validate_verhoeff(uid) is False


def test_pan_structural_and_entity_validation():
    """Validates PAN format and 4th character entity extraction."""
    # Individual PAN ('P' at index 3)
    valid_ind, entity = validate_pan("ABCPE1234F")
    assert valid_ind is True
    assert "Individual" in entity

    # Company PAN ('C' at index 3)
    valid_co, entity_co = validate_pan("AAACC1234G")
    assert valid_co is True
    assert "Company" in entity_co

    # Firm PAN ('F' at index 3)
    valid_f, entity_f = validate_pan("AAAFZ9999K")
    assert valid_f is True
    assert "Firm" in entity_f

    # Invalid PANs
    assert validate_pan("ABC1234")[0] is False
    assert validate_pan("12345ABCDE")[0] is False


def test_gstin_validation():
    """Validates 15-character GSTIN structure and Indian state code lookup."""
    # Maharashtra GSTIN (State 27)
    valid_mh, state_mh = validate_gstin("27AAACC1234G1Z5")
    assert valid_mh is True
    assert state_mh == "Maharashtra"

    # Delhi GSTIN (State 07)
    valid_dl, state_dl = validate_gstin("07ABCDE1234F1Z8")
    assert valid_dl is True
    assert state_dl == "Delhi"

    # Invalid GSTIN
    assert validate_gstin("999INVALID")[0] is False


def test_masking_functions():
    """Validates PII masking patterns."""
    assert mask_aadhaar("999999990019") == "XXXX-XXXX-0019"
    assert mask_pan("ABCPE1234F") == "ABXXXXX34F"
    assert mask_gstin("27AAACC1234G1Z5") == "27XXXXXXXXXG1Z5"
    assert mask_bank_account("123456789012") == "XXXXXXXX9012"
    assert mask_phone("9876543210") == "+91-XXXXX-XX210"
    assert mask_email("forensic.auditor@icai.org") == "f**************r@icai.org"


def test_deterministic_pseudonymization():
    """Verifies that same input with session salt yields identical token, preserving relational integrity."""
    salt = "TEST_AUDIT_SALT_123"
    token1 = pseudonymize_value("M/S Apex Enterprises", "VENDOR", salt)
    token2 = pseudonymize_value("M/S Apex Enterprises", "VENDOR", salt)
    token_diff = pseudonymize_value("M/S Zenith Technologies", "VENDOR", salt)

    assert token1 == token2
    assert token1.startswith("VEND-PSEUDO-")
    assert token1 != token_diff


def test_hitl_air_gap_gateway():
    """Verifies that external egress is blocked by default under Indian DPDP Act 2023."""
    gateway = HITLSecurityGateway()
    # Default is air-gapped
    res = gateway.check_egress_authorization("EXTERNAL_CLOUD_API", {"data": "test"})
    assert res["authorized"] is False
    assert res["status"] == "BLOCKED_AIR_GAP_ENFORCED"
