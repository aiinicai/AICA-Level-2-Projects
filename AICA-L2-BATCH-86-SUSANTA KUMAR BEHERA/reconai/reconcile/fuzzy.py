from collections import defaultdict
import datetime
from decimal import Decimal
import re
from typing import List, Optional, Set, Tuple
from rapidfuzz import fuzz

from reconai.models.transaction import (
    StatementTransaction,
    LedgerEntry,
    MatchRecord,
    MatchStatus,
)
from reconai.config import ReconciliationConfig


def clean_narration_for_fuzzy(text: str) -> str:
    """Clean bank and accounting noise to isolate core vendor/purpose names."""
    if not text:
        return ""
    s = text.lower()
    # Strip common transaction headers / channels
    s = re.sub(r"\b(neft|rtgs|imps|ach|upi|pos|chq|clg|transfer|dr|cr|inr|to|by|for|a/c|acct|pvt|ltd|limited|corp)\b", " ", s)
    # Strip numbers / dates / slashes
    s = re.sub(r"[0-9/_\-\:\.]+", " ", s)
    # Strip excess whitespace
    return " ".join(s.split())


class FuzzyMatcher:
    """High-Performance Fuzzy String Similarity Matcher using Pre-Indexed Lookups."""

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

        if not avail_stmts or not avail_ledgers:
            return matches

        # Pre-clean ledger strings and index by (type, amount)
        ledger_by_amt = defaultdict(list)
        l_clean_cache = {}
        for l in avail_ledgers:
            ledger_by_amt[(l.type, l.amount)].append(l)
            l_clean_cache[l.id] = clean_narration_for_fuzzy(f"{l.description} {l.account_name or ''}")

        max_window = max(self.config.date_tolerance_days, 10)

        for s in avail_stmts:
            if s.id in matched_stmt_ids:
                continue

            candidates = ledger_by_amt.get((s.type, s.amount), [])
            if not candidates:
                continue

            s_clean = clean_narration_for_fuzzy(s.description)
            best_candidate: Optional[Tuple[LedgerEntry, float, float, int]] = None

            for l in candidates:
                if l.id in matched_ledger_ids:
                    continue

                amt_diff = abs(s.amount - l.amount)
                if amt_diff > self.config.amount_tolerance:
                    continue

                days_diff = abs((s.date - l.date).days)
                if days_diff > max_window:
                    continue

                l_clean = l_clean_cache.get(l.id, "")
                
                # RapidFuzz similarity ratios
                token_sort = fuzz.token_sort_ratio(s_clean, l_clean)
                token_set = fuzz.token_set_ratio(s_clean, l_clean)
                partial = fuzz.partial_ratio(s_clean, l_clean)
                sim_ratio = max(token_sort, token_set, (token_set * 0.6 + partial * 0.4))

                if sim_ratio >= self.config.fuzzy_narration_threshold:
                    if best_candidate is None or sim_ratio > best_candidate[1]:
                        best_candidate = (l, sim_ratio, float(amt_diff), days_diff)

            if best_candidate:
                l, sim_ratio, amt_diff, days_diff = best_candidate
                
                # Confidence score based on similarity and date closeness
                base_confidence = (sim_ratio / 100.0) * 0.85 + max(0, (10 - days_diff) / 10.0) * 0.15
                confidence = round(min(base_confidence, 0.94), 2)
                
                status = MatchStatus.MATCHED if confidence >= 0.85 else MatchStatus.PROBABLE

                match = MatchRecord(
                    statement_tx_id=s.id,
                    ledger_entry_id=l.id,
                    status=status,
                    confidence_score=confidence,
                    rule_applied=f"FUZZY_NARRATION_SIMILARITY_{int(sim_ratio)}PCT",
                    plain_english_reason=(
                        f"Amount ₹{s.amount:,.2f} matched with {int(sim_ratio)}% narration similarity "
                        f"(Statement: '{s.description}' vs Ledger: '{l.description}', {days_diff}d timing diff)."
                    ),
                )
                matches.append(match)
                matched_stmt_ids.add(s.id)
                matched_ledger_ids.add(l.id)

        return matches
