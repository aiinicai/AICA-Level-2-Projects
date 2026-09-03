import logging
from typing import Dict, List, Optional, Set, Tuple

from reconai.models.transaction import (
    StatementTransaction,
    LedgerEntry,
    MatchRecord,
    MatchStatus,
    TransactionType,
)
from reconai.config import ReconciliationConfig
from reconai.reconcile.deterministic import DeterministicMatcher
from reconai.reconcile.fuzzy import FuzzyMatcher
from reconai.reconcile.ai_matcher import AIMatcher

logger = logging.getLogger(__name__)


class Reconciler:
    """Master Reconciler coordinating multi-pass deterministic, fuzzy, and AI reconciliation."""

    def __init__(self, config: Optional[ReconciliationConfig] = None):
        self.config = config or ReconciliationConfig()
        self.deterministic_matcher = DeterministicMatcher(self.config)
        self.fuzzy_matcher = FuzzyMatcher(self.config)
        self.ai_matcher = AIMatcher(self.config)

    def reconcile(
        self,
        statements: List[StatementTransaction],
        ledgers: List[LedgerEntry],
    ) -> List[MatchRecord]:
        matched_stmt_ids: Set[str] = set()
        matched_ledger_ids: Set[str] = set()
        all_matches: List[MatchRecord] = []

        # Reset matched flags
        for s in statements:
            s.matched = False
        for l in ledgers:
            l.matched = False

        # Pass 1: Deterministic Matcher (Exact amounts + dates + refs)
        det_matches = self.deterministic_matcher.match(
            statements, ledgers, matched_stmt_ids, matched_ledger_ids
        )
        all_matches.extend(det_matches)

        # Pass 2: Fuzzy Matcher (Rapidfuzz narration similarity)
        fuzzy_matches = self.fuzzy_matcher.match(
            statements, ledgers, matched_stmt_ids, matched_ledger_ids
        )
        all_matches.extend(fuzzy_matches)

        # Pass 3: AI Matcher (Semantic narration matching via AIClient)
        if self.config.enable_ai_matcher and self.ai_matcher.ai_client.is_available:
            ai_matches = self.ai_matcher.match(
                statements, ledgers, matched_stmt_ids, matched_ledger_ids
            )
            all_matches.extend(ai_matches)

        # Mark matched entries
        for s in statements:
            if s.id in matched_stmt_ids:
                s.matched = True
        for l in ledgers:
            if l.id in matched_ledger_ids:
                l.matched = True

        # Pass 4: Create explicit Unmatched Records for remaining statement transactions
        for s in statements:
            if s.id not in matched_stmt_ids:
                reason = self._diagnose_unmatched_statement(s, ledgers)
                match = MatchRecord(
                    statement_tx_id=s.id,
                    ledger_entry_id=None,
                    status=MatchStatus.UNMATCHED,
                    confidence_score=0.0,
                    rule_applied="UNMATCHED_BANK_STATEMENT_ENTRY",
                    plain_english_reason=reason,
                )
                all_matches.append(match)

        # Pass 5: Create explicit Unmatched Records for remaining ledger entries
        for l in ledgers:
            if l.id not in matched_ledger_ids:
                reason = self._diagnose_unmatched_ledger(l, statements)
                match = MatchRecord(
                    statement_tx_id=None,
                    ledger_entry_id=l.id,
                    status=MatchStatus.UNMATCHED,
                    confidence_score=0.0,
                    rule_applied="UNMATCHED_CLIENT_LEDGER_ENTRY",
                    plain_english_reason=reason,
                )
                all_matches.append(match)

        return all_matches

    def _diagnose_unmatched_statement(
        self, s: StatementTransaction, ledgers: List[LedgerEntry]
    ) -> str:
        desc_lower = s.description.lower()
        if "charge" in desc_lower or "fee" in desc_lower or "tax" in desc_lower or "gst" in desc_lower:
            return f"Bank debit of ₹{s.amount:,.2f} appears to be direct bank charges/fees not yet recorded in books."
        elif "interest" in desc_lower or "int.cr" in desc_lower or "dividend" in desc_lower:
            return f"Bank credit of ₹{s.amount:,.2f} appears to be interest/dividend credit not yet recorded in books."
        elif s.type == TransactionType.CREDIT:
            return f"Direct credit/deposit of ₹{s.amount:,.2f} received in bank without corresponding ledger receipt voucher."
        else:
            return f"Direct bank withdrawal of ₹{s.amount:,.2f} not found in client payment vouchers."

    def _diagnose_unmatched_ledger(
        self, l: LedgerEntry, statements: List[StatementTransaction]
    ) -> str:
        if l.type == TransactionType.DEBIT:
            return f"Payment voucher of ₹{l.amount:,.2f} ({l.description[:30]}) in books - possible unpresented cheque or pending clearance."
        else:
            return f"Receipt voucher of ₹{l.amount:,.2f} ({l.description[:30]}) in books - possible uncredited deposit / cheque deposited but not yet cleared."
