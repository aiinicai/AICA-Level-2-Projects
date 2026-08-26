"""
Unit Tests for Tamper-Evident SHA-256 Chained Audit Ledger & Verification Engine.
"""

import pytest
from backend.app.engine.audit_ledger import ChainedAuditLedger


def test_genesis_block_and_chaining():
    """Validates initial genesis block and hash link continuity."""
    ledger = ChainedAuditLedger(auditor_id="FORENSIC_LEAD")
    assert len(ledger.chain) == 1
    genesis = ledger.chain[0]
    assert genesis.index == 0
    assert genesis.action == "GENESIS_SESSION_INITIALIZED"

    # Append events
    b1 = ledger.log_event("TEST_EVENT_1", "ABC123HASH", {"param": 1})
    b2 = ledger.log_event("TEST_EVENT_2", "DEF456HASH", {"param": 2})

    assert len(ledger.chain) == 3
    assert b1.prev_hash == genesis.block_hash
    assert b2.prev_hash == b1.block_hash

    is_valid, msg, corrupt_idx = ledger.verify_integrity()
    assert is_valid is True
    assert corrupt_idx is None


def test_tamper_detection():
    """
    Intentionally mutates an intermediate block to verify that the cryptographic
    auditor catches the alteration and identifies the exact block index.
    """
    ledger = ChainedAuditLedger()
    ledger.log_event("EVENT_1", "HASH1", {"amt": 100})
    ledger.log_event("EVENT_2", "HASH2", {"amt": 200})
    ledger.log_event("EVENT_3", "HASH3", {"amt": 300})

    # Tamper with Block 2 details
    ledger.chain[2].details["amt"] = 999999  # Malicious alteration!

    is_valid, msg, corrupt_idx = ledger.verify_integrity()
    assert is_valid is False
    assert corrupt_idx == 2
    assert "Tampering detected" in msg
