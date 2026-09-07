import json
import logging
from typing import List, Optional, Set

from reconai.models.transaction import (
    StatementTransaction,
    LedgerEntry,
    MatchRecord,
    MatchStatus,
)
from reconai.config import ReconciliationConfig
from reconai.ai.client import AIClient

logger = logging.getLogger(__name__)


class AIMatcher:
    """AI-Assisted Matcher for complex or abbreviated narrations via AIClient."""

    def __init__(
        self,
        config: Optional[ReconciliationConfig] = None,
        ai_client: Optional[AIClient] = None,
    ):
        self.config = config or ReconciliationConfig()
        self.ai_client = ai_client or AIClient(
            api_key=self.config.api_key,
            model=self.config.ai_model,
        )

    def match(
        self,
        statements: List[StatementTransaction],
        ledgers: List[LedgerEntry],
        matched_stmt_ids: Set[str],
        matched_ledger_ids: Set[str],
    ) -> List[MatchRecord]:
        if not self.config.enable_ai_matcher or not self.ai_client.is_available:
            return []

        avail_stmts = [s for s in statements if s.id not in matched_stmt_ids]
        avail_ledgers = [l for l in ledgers if l.id not in matched_ledger_ids]

        if not avail_stmts or not avail_ledgers:
            return []

        matches: List[MatchRecord] = []

        try:
            # Prepare candidate summary payload
            stmt_payload = [
                {
                    "id": s.id,
                    "date": str(s.date),
                    "amount": str(s.amount),
                    "type": s.type.value,
                    "description": s.description,
                }
                for s in avail_stmts[:20]
            ]
            ledger_payload = [
                {
                    "id": l.id,
                    "date": str(l.date),
                    "amount": str(l.amount),
                    "type": l.type.value,
                    "description": l.description,
                    "party": l.account_name,
                }
                for l in avail_ledgers[:30]
            ]

            prompt = (
                "You are an expert Chartered Accountant reviewing unmatched bank statement transactions and client ledger records.\n"
                "Match corresponding transactions between the two lists where possible, considering abbreviations, acronyms, and timing differences.\n"
                "Return a valid JSON array of matched pairs with this schema:\n"
                '[{\n'
                '  "statement_id": "...",\n'
                '  "ledger_id": "...",\n'
                '  "confidence_score": 0.85,\n'
                '  "plain_english_reason": "..."\n'
                '}]\n\n'
                f"Bank Statement Transactions:\n{json.dumps(stmt_payload, indent=2)}\n\n"
                f"Client Ledger Entries:\n{json.dumps(ledger_payload, indent=2)}\n"
            )

            pairs = self.ai_client.generate_json(
                prompt=prompt,
                system_instruction="You are a professional financial reconciliation auditor."
            )

            if isinstance(pairs, list):
                for pair in pairs:
                    stmt_id = pair.get("statement_id")
                    ledger_id = pair.get("ledger_id")
                    conf = float(pair.get("confidence_score", 0.8))
                    reason = pair.get("plain_english_reason", "AI-assisted semantic match.")

                    if (
                        stmt_id in [s.id for s in avail_stmts]
                        and ledger_id in [l.id for l in avail_ledgers]
                        and stmt_id not in matched_stmt_ids
                        and ledger_id not in matched_ledger_ids
                    ):
                        status = MatchStatus.MATCHED if conf >= 0.85 else MatchStatus.PROBABLE
                        match = MatchRecord(
                            statement_tx_id=stmt_id,
                            ledger_entry_id=ledger_id,
                            status=status,
                            confidence_score=conf,
                            rule_applied="AI_GEMINI_SEMANTIC_MATCH",
                            plain_english_reason=f"[AI Analysis] {reason}",
                        )
                        matches.append(match)
                        matched_stmt_ids.add(stmt_id)
                        matched_ledger_ids.add(ledger_id)

        except Exception as e:
            logger.warning(f"AI matcher call failed or skipped: {e}")

        return matches
