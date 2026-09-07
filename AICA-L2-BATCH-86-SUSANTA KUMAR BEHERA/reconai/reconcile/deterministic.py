from collections import defaultdict
import datetime
from decimal import Decimal
import re
from typing import List, Optional, Set, Tuple

from reconai.models.transaction import (
    StatementTransaction,
    LedgerEntry,
    MatchRecord,
    MatchStatus,
)
from reconai.config import ReconciliationConfig


def extract_reference_numbers(text: str) -> Set[str]:
    """Extract numeric/alphanumeric reference codes, UTR, cheque numbers from text."""
    if not text:
        return set()
    tokens = re.findall(r"\b[A-Za-z0-9]{4,16}\b", text)
    stop_words = {"NEFT", "RTGS", "IMPS", "ACH", "UPI", "POS", "BANK", "CHQ", "CLG", "DR", "CR", "INR", "PAID", "BILL"}
    return {t.upper() for t in tokens if t.upper() not in stop_words and not t.isalpha()}


class DeterministicMatcher:
    """High-Performance Deterministic Rule-Based Matcher using Hash-Indexed Lookups."""

    def __init__(self, config: Optional[ReconciliationConfig] = None):
        self.config = config or ReconciliationConfig()

    def match(
        self,
        statements: List[StatementTransaction],
        ledgers: List[LedgerEntry],
        matched_stmt_ids: Set[str],
        matched_ledger_ids: Set[str],
    ) -> List[MatchRecord]:
        matches: List[MatchRecord] = []

        avail_stmts = [s for s in statements if s.id not in matched_stmt_ids]
        avail_ledgers = [l for l in ledgers if l.id not in matched_ledger_ids]

        # Index available ledgers by (type, amount) for O(1) candidate lookup
        ledger_by_amt = defaultdict(list)
        for l in avail_ledgers:
            ledger_by_amt[(l.type, l.amount)].append(l)

        # Precompute reference sets for ledgers to avoid regex re-parsing
        l_refs_cache = {}
        for l in avail_ledgers:
            l_refs_cache[l.id] = extract_reference_numbers(f"{l.description} {l.source_row_ref}")

        # Pass 1A: Exact Amount + Exact Reference / Cheque Number
        for s in avail_stmts:
            if s.id in matched_stmt_ids:
                continue
            s_refs = extract_reference_numbers(s.description)
            if not s_refs:
                continue

            candidates = ledger_by_amt.get((s.type, s.amount), [])
            for l in candidates:
                if l.id in matched_ledger_ids:
                    continue

                common_refs = s_refs.intersection(l_refs_cache.get(l.id, set()))
                if common_refs:
                    ref_str = ", ".join(common_refs)
                    days_diff = abs((s.date - l.date).days)
                    match = MatchRecord(
                        statement_tx_id=s.id,
                        ledger_entry_id=l.id,
                        status=MatchStatus.MATCHED,
                        confidence_score=1.0,
                        rule_applied="DETERMINISTIC_EXACT_AMOUNT_AND_REF",
                        plain_english_reason=(
                            f"Exact amount INR {s.amount:,.2f} matched with common reference [{ref_str}] "
                            f"(Statement date: {s.date.strftime('%d-%b-%Y')}, Ledger date: {l.date.strftime('%d-%b-%Y')}, diff: {days_diff}d)."
                        ),
                    )
                    matches.append(match)
                    matched_stmt_ids.add(s.id)
                    matched_ledger_ids.add(l.id)
                    break

        # Pass 1B: Exact Amount + Same Date (0 days difference)
        for s in avail_stmts:
            if s.id in matched_stmt_ids:
                continue

            candidates = [
                l for l in ledger_by_amt.get((s.type, s.amount), [])
                if l.id not in matched_ledger_ids and s.date == l.date
            ]

            if candidates:
                l = candidates[0]
                match = MatchRecord(
                    statement_tx_id=s.id,
                    ledger_entry_id=l.id,
                    status=MatchStatus.MATCHED,
                    confidence_score=0.98 if len(candidates) == 1 else 0.94,
                    rule_applied="DETERMINISTIC_EXACT_AMOUNT_SAME_DATE",
                    plain_english_reason=(
                        f"Exact amount INR {s.amount:,.2f} matched on identical date ({s.date.strftime('%d-%b-%Y')}) "
                        f"between statement '{s.description[:35]}' and ledger '{l.description[:35]}' (Voucher {l.source_row_ref})."
                    ),
                )
                matches.append(match)
                matched_stmt_ids.add(s.id)
                matched_ledger_ids.add(l.id)

        # Pass 1C: Exact Amount + Date within Tolerance Window (1 to N days)
        for s in avail_stmts:
            if s.id in matched_stmt_ids:
                continue

            candidates: List[Tuple[LedgerEntry, int]] = []
            for l in ledger_by_amt.get((s.type, s.amount), []):
                if l.id in matched_ledger_ids:
                    continue
                days_diff = abs((s.date - l.date).days)
                if 1 <= days_diff <= self.config.date_tolerance_days:
                    candidates.append((l, days_diff))

            if candidates:
                candidates.sort(key=lambda x: x[1])
                l, days_diff = candidates[0]
                status = MatchStatus.MATCHED if (len(candidates) == 1 and days_diff <= 3) else MatchStatus.PROBABLE
                score = round(0.95 - (days_diff * 0.02), 2) if len(candidates) == 1 else 0.82
                match = MatchRecord(
                    statement_tx_id=s.id,
                    ledger_entry_id=l.id,
                    status=status,
                    confidence_score=score,
                    rule_applied=f"DETERMINISTIC_EXACT_AMOUNT_DATE_DIFF_{days_diff}D",
                    plain_english_reason=(
                        f"Exact amount INR {s.amount:,.2f} matched with timing difference of {days_diff} day(s) "
                        f"(Statement: {s.date.strftime('%d-%b-%Y')}, Ledger: {l.date.strftime('%d-%b-%Y')}, Voucher: {l.source_row_ref})."
                    ),
                )
                matches.append(match)
                matched_stmt_ids.add(s.id)
                matched_ledger_ids.add(l.id)

        return matches
