import json
import logging
from decimal import Decimal
from typing import List, Optional

from reconai.models.transaction import (
    LedgerEntry,
    AuditFlag,
    AuditSeverity,
    AuditCategory,
    TransactionType,
)
from reconai.config import AuditConfig, ReconciliationConfig
from reconai.ai.client import AIClient

logger = logging.getLogger(__name__)

# Heuristic patterns for sensitive or vague personal/misc charges
VAGUE_EXPENSE_TERMS = ["misc", "miscellaneous", "sundry", "general exp", "cash expenses", "petty cash direct"]
PERSONAL_RISK_TERMS = ["jewel", "club", "spa", "resort", "vacation", "personal", "liquor", "casino", "gaming"]


class AIFlagger:
    """AI and Semantic Anomaly Flagger for Expense Audits via AIClient."""

    def __init__(
        self,
        audit_config: Optional[AuditConfig] = None,
        recon_config: Optional[ReconciliationConfig] = None,
        ai_client: Optional[AIClient] = None,
    ):
        self.audit_config = audit_config or AuditConfig()
        self.recon_config = recon_config or ReconciliationConfig()
        self.ai_client = ai_client or AIClient(
            api_key=self.recon_config.api_key,
            model=self.recon_config.ai_model,
        )

    def audit(self, entries: List[LedgerEntry]) -> List[AuditFlag]:
        if not self.audit_config.enable_ai_audit:
            return []

        flags: List[AuditFlag] = []

        # 1. Fast Semantic Heuristic Pass (Always runs locally)
        for entry in entries:
            if entry.type == TransactionType.DEBIT:
                desc_lower = entry.description.lower()
                
                # Check personal/lifestyle risk
                for term in PERSONAL_RISK_TERMS:
                    if term in desc_lower:
                        flags.append(
                            AuditFlag(
                                target_type="LEDGER",
                                source_row_ref=entry.source_row_ref,
                                entry_id=entry.id,
                                rule_name="POTENTIAL_PERSONAL_NON_BUSINESS_EXPENSE",
                                severity=AuditSeverity.HIGH,
                                category=AuditCategory.SUSPICIOUS_PATTERN,
                                plain_english_reason=(
                                    f"Narration contains '{term}' which may indicate personal/non-business expenditure (disallowable under Income Tax Section 37(1))."
                                ),
                                suggested_action="Verify commercial expediency and business nexus documentation.",
                                entry_summary={"voucher": str(entry.source_row_ref), "description": entry.description},
                            )
                        )
                        break

                # Check vague miscellaneous large amounts
                if entry.amount >= Decimal("10000.00"):
                    for term in VAGUE_EXPENSE_TERMS:
                        if term in desc_lower:
                            flags.append(
                                AuditFlag(
                                    target_type="LEDGER",
                                    source_row_ref=entry.source_row_ref,
                                    entry_id=entry.id,
                                    rule_name="VAGUE_DESCRIPTION_HIGH_VALUE",
                                    severity=AuditSeverity.MEDIUM,
                                    category=AuditCategory.ANOMALOUS_CATEGORY,
                                    plain_english_reason=(
                                        f"High-value expense of ₹{entry.amount:,.2f} has vague/generic narration '{entry.description}'. Lacks audit trail specificity."
                                    ),
                                    suggested_action="Request itemized breakdown of expenses from client.",
                                    entry_summary={"voucher": str(entry.source_row_ref), "amount": str(entry.amount)},
                                )
                            )
                            break

        # 2. Gemini AI Semantic Pass (if API key available)
        if self.ai_client.is_available:
            try:
                ai_flags = self._call_ai_audit(entries)
                flags.extend(ai_flags)
            except Exception as e:
                logger.warning(f"AI audit call failed: {e}")

        return flags

    def _call_ai_audit(self, entries: List[LedgerEntry]) -> List[AuditFlag]:
        """Deep semantic analysis using AIClient."""
        debits = [e for e in entries if e.type == TransactionType.DEBIT and e.amount >= Decimal("10000.00")]
        if not debits:
            return []

        payload = [
            {
                "voucher": str(e.source_row_ref),
                "date": str(e.date),
                "amount": str(e.amount),
                "description": e.description,
                "account": e.account_name,
            }
            for e in debits[:25]
        ]

        prompt = (
            "You are a forensic Chartered Accountant auditing client expenses.\n"
            "Analyze these expense entries for subtle anomalies (e.g. unusual vendor descriptions, potential non-business items, suspicious round splits).\n"
            "Return a JSON array of findings:\n"
            '[{\n'
            '  "voucher": "...",\n'
            '  "rule_name": "AI_FLAG_NAME",\n'
            '  "severity": "HIGH"|"MEDIUM"|"LOW",\n'
            '  "category": "ANOMALOUS_CATEGORY"|"SUSPICIOUS_PATTERN",\n'
            '  "plain_english_reason": "...",\n'
            '  "suggested_action": "..."\n'
            '}]\n\n'
            f"Expense Entries:\n{json.dumps(payload, indent=2)}"
        )

        items = self.ai_client.generate_json(
            prompt=prompt,
            system_instruction="You are a forensic financial auditor. Identify compliance risks and anomalous expenses in the given dataset."
        )

        if not isinstance(items, list):
            return []

        entry_map = {str(e.source_row_ref): e for e in debits}
        flags: List[AuditFlag] = []

        for item in items:
            vch = str(item.get("voucher"))
            if vch in entry_map:
                e = entry_map[vch]
                sev = AuditSeverity(item.get("severity", "MEDIUM").upper())
                cat = AuditCategory(item.get("category", "ANOMALOUS_CATEGORY").upper())
                flags.append(
                    AuditFlag(
                        target_type="LEDGER",
                        source_row_ref=e.source_row_ref,
                        entry_id=e.id,
                        rule_name=item.get("rule_name", "AI_SEMANTIC_ANOMALY"),
                        severity=sev,
                        category=cat,
                        plain_english_reason=f"[AI Insight] {item.get('plain_english_reason', '')}",
                        suggested_action=item.get("suggested_action", "Review underlying supporting documents."),
                        entry_summary={"voucher": vch, "amount": str(e.amount)},
                    )
                )

        return flags
