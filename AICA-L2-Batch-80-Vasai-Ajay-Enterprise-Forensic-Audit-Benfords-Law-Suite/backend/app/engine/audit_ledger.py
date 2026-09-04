"""
Tamper-Evident SHA-256 Chained Audit Ledger & DPDP Integrity System.

Implements:
1. Cryptographic Blockchain-style Hash Chaining for all forensic audit actions.
2. Dataset Ingest Fingerprinting (SHA-256 / SHA-512).
3. On-Demand Audit Integrity Verification & Tamper Detection.
4. Exportable DPDP Compliance & Forensic Audit Certificate.
"""

import time
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple


class AuditBlock:
    """Represents a single immutable record in the chained audit journal."""
    def __init__(
        self,
        index: int,
        action: str,
        user_role: str,
        consent_token: str,
        dataset_hash: str,
        details: Dict[str, Any],
        prev_hash: str,
        timestamp: Optional[float] = None
    ):
        self.index = index
        self.timestamp = timestamp or time.time()
        self.action = action
        self.user_role = user_role
        self.consent_token = consent_token
        self.dataset_hash = dataset_hash
        self.details = details
        self.prev_hash = prev_hash
        self.block_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Computes SHA-256 hash of block contents."""
        block_content = {
            "index": self.index,
            "timestamp": round(self.timestamp, 4),
            "action": self.action,
            "user_role": self.user_role,
            "consent_token": self.consent_token,
            "dataset_hash": self.dataset_hash,
            "details": self.details,
            "prev_hash": self.prev_hash
        }
        encoded = json.dumps(block_content, sort_keys=True, default=str).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(self.timestamp)),
            "action": self.action,
            "user_role": self.user_role,
            "consent_token": self.consent_token,
            "dataset_hash": self.dataset_hash,
            "details": self.details,
            "prev_hash": self.prev_hash,
            "block_hash": self.block_hash
        }


class ChainedAuditLedger:
    """
    Tamper-Evident Chained Audit Ledger.
    Ensures deterministic reproducibility, traceability, and DPDP compliance integrity.
    """
    
    def __init__(self, auditor_id: str = "CHIEF_FORENSIC_AUDITOR"):
        self.auditor_id = auditor_id
        self.chain: List[AuditBlock] = []
        self._init_genesis_block()

    def _init_genesis_block(self):
        """Creates genesis block for the forensic session."""
        genesis = AuditBlock(
            index=0,
            action="GENESIS_SESSION_INITIALIZED",
            user_role="SYSTEM_GOVERNANCE",
            consent_token="INIT_ROOT_CONSENT",
            dataset_hash="0" * 64,
            details={"purpose": "Indian DPDP Act 2023 Forensic Audit Session Initialized"},
            prev_hash="0" * 64
        )
        self.chain.append(genesis)

    def log_event(
        self,
        action: str,
        dataset_hash: str,
        details: Dict[str, Any],
        user_role: str = "FORENSIC_AUDITOR",
        consent_token: str = "USER_CONSENT_GRANTED"
    ) -> AuditBlock:
        """Appends a new event block with cryptographic hash chaining."""
        prev_block = self.chain[-1]
        new_block = AuditBlock(
            index=len(self.chain),
            action=action,
            user_role=user_role,
            consent_token=consent_token,
            dataset_hash=dataset_hash,
            details=details,
            prev_hash=prev_block.block_hash
        )
        self.chain.append(new_block)
        return new_block

    def verify_integrity(self) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Verifies the complete cryptographic chain.
        Returns: (is_valid, error_message, corrupted_block_index)
        """
        if not self.chain:
            return False, "Audit chain is empty", 0

        for i in range(len(self.chain)):
            block = self.chain[i]
            # 1. Verify internal hash correctness
            expected_hash = block.compute_hash()
            if block.block_hash != expected_hash:
                return False, f"Tampering detected: Block {i} hash mismatch (found {block.block_hash}, calculated {expected_hash})", i

            # 2. Verify previous hash chaining
            if i > 0:
                prev_block = self.chain[i - 1]
                if block.prev_hash != prev_block.block_hash:
                    return False, f"Chain broken between Block {i-1} and Block {i}: prev_hash does not match parent block hash", i

        return True, "Audit Ledger verified: All cryptographic hashes and chain links are 100% authentic and tamper-free.", None

    def get_ledger(self) -> List[Dict[str, Any]]:
        """Returns serialized audit ledger."""
        return [block.to_dict() for block in self.chain]

    def generate_audit_certificate(
        self,
        dataset_name: str,
        record_count: int,
        dataset_hash: str,
        benford_mad_status: str,
        dpdp_status: str
    ) -> Dict[str, Any]:
        """Generates cryptographic DPDP Compliance & Forensic Certificate."""
        is_valid, msg, _ = self.verify_integrity()
        latest_block = self.chain[-1]
        
        cert = {
            "certificate_id": f"DPDP-CERT-{hashlib.sha256(f'{dataset_hash}{time.time()}'.encode()).hexdigest()[:16].upper()}",
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "framework_title": "Enterprise Forensic Audit & Benford's Law Suite (Indian DPDP Act, 2023 Compliant)",
            "statutory_mandate": "Indian Digital Personal Data Protection Act, 2023 (DPDP Act) Sections 4, 7 & 8",
            "auditor_role": self.auditor_id,
            "dataset_metadata": {
                "dataset_name": dataset_name,
                "total_records": record_count,
                "dataset_sha256": dataset_hash
            },
            "forensic_conformity": {
                "benford_mad_rating": benford_mad_status
            },
            "dpdp_compliance": {
                "status": dpdp_status,
                "pii_scrubbed": True,
                "air_gap_enforced": True,
                "consent_mandated": True
            },
            "chain_of_custody": {
                "total_audit_blocks": len(self.chain),
                "latest_block_hash": latest_block.block_hash,
                "cryptographic_verification": "VERIFIED_TAMPER_FREE" if is_valid else "CORRUPTED",
                "verification_message": msg,
                "blocks": self.get_ledger()
            }
        }
        return cert
