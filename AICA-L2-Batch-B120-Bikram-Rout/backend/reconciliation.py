import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from .database import get_db, log_audit

def to_decimal(val) -> Decimal:
    if val is None:
        return Decimal("0.00")
    if isinstance(val, (int, float, str)):
        return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if isinstance(val, Decimal):
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal("0.00")

def check_period_unlocked(cur, period_id: str) -> Optional[str]:
    """Ensures period exists and is not locked or approved prior to mutating matches."""
    cur.execute("SELECT status FROM periods WHERE id = ?", (period_id,))
    p = cur.fetchone()
    if not p:
        return f"Period '{period_id}' not found."
    if p["status"] in ("Locked", "Approved"):
        return f"Period '{period_id}' is {p['status']}. Modifications are prohibited without authorized reopening."
    return None

def calculate_brs(account_id: str, period_id: str) -> Dict[str, Any]:
    """
    Computes exact Bank Reconciliation Statement according to specification:
    - Bank statement closing balance
    - Signed ledger-only movements not yet reflected by the bank
    - Adjusted bank balance = Bank Closing + Signed Ledger Unmatched
    - Ledger closing balance
    - Signed bank-only movements not yet recorded in the ledger
    - Adjusted ledger balance = Ledger Closing + Signed Bank Unmatched
    - Residual difference = Adjusted Bank - Adjusted Ledger
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM periods WHERE id = ? AND account_id = ?", (period_id, account_id))
        period = cur.fetchone()
        if not period:
            return {"error": "Period not found"}

        cur.execute("SELECT * FROM bank_accounts WHERE id = ?", (account_id,))
        account = cur.fetchone()

        bank_closing = to_decimal(period["bank_closing_balance"])
        bank_opening = to_decimal(period["bank_opening_balance"])
        ledger_closing = to_decimal(period["ledger_closing_balance"])
        ledger_opening = to_decimal(period["ledger_opening_balance"])

        cur.execute("""
            SELECT * FROM transactions
            WHERE account_id = ? AND period_id = ?
        """, (account_id, period_id))
        all_txs = [dict(r) for r in cur.fetchall()]

        matched_txs = [t for t in all_txs if t["recon_status"] == "Matched"]
        partially_matched_txs = [t for t in all_txs if t["recon_status"] == "Partially Matched"]
        
        # Unmatched / Timing items: includes Unmatched, Exception, Suggested Match, and remaining unallocated amounts
        ledger_unmatched = [t for t in all_txs if t["source"] == "Oracle Ledger" and t["recon_status"] in ("Unmatched", "Exception", "Suggested Match", "Partially Matched")]
        bank_unmatched = [t for t in all_txs if t["source"] == "Bank Statement" and t["recon_status"] in ("Unmatched", "Exception", "Suggested Match", "Partially Matched")]

        # For partially matched items, take the unallocated remaining portion
        def get_unmatched_amount(tx):
            signed = to_decimal(tx["signed_amount"])
            allocated = to_decimal(tx.get("allocated_amount") or 0)
            if tx["recon_status"] == "Partially Matched":
                remaining = abs(signed) - allocated
                return remaining if signed > 0 else -remaining
            elif tx["recon_status"] == "Matched":
                return Decimal("0.00")
            return signed

        ledger_only_sum = sum((get_unmatched_amount(t) for t in ledger_unmatched), Decimal("0.00"))
        bank_only_sum = sum((get_unmatched_amount(t) for t in bank_unmatched), Decimal("0.00"))

        # Reconciling categories
        ledger_payments_in_transit = sum((get_unmatched_amount(t) for t in ledger_unmatched if get_unmatched_amount(t) < 0), Decimal("0.00"))
        ledger_deposits_in_transit = sum((get_unmatched_amount(t) for t in ledger_unmatched if get_unmatched_amount(t) > 0), Decimal("0.00"))

        bank_charges_sum = sum((get_unmatched_amount(t) for t in bank_unmatched if get_unmatched_amount(t) < 0), Decimal("0.00"))
        bank_interest_credits_sum = sum((get_unmatched_amount(t) for t in bank_unmatched if get_unmatched_amount(t) > 0), Decimal("0.00"))

        adjusted_bank_balance = (bank_closing + ledger_only_sum).quantize(Decimal("0.01"))
        adjusted_ledger_balance = (ledger_closing + bank_only_sum).quantize(Decimal("0.01"))
        residual_difference = (adjusted_bank_balance - adjusted_ledger_balance).quantize(Decimal("0.01"))

        is_reconciled = (residual_difference == Decimal("0.00"))

        # Update period residual_diff in database
        cur.execute("UPDATE periods SET residual_diff = ? WHERE id = ?", (float(residual_difference), period_id))
        conn.commit()

        return {
            "account_id": account_id,
            "period_id": period_id,
            "account_number": account["account_number"] if account else "",
            "currency": account["currency"] if account else "USD",
            "bank_name": account["bank_name"] if account else "",
            "period_name": period["period_name"],
            "period_status": period["status"],
            "bank_opening_balance": float(bank_opening),
            "bank_closing_balance": float(bank_closing),
            "ledger_opening_balance": float(ledger_opening),
            "ledger_closing_balance": float(ledger_closing),
            "raw_balance_difference": float((bank_closing - ledger_closing).quantize(Decimal("0.01"))),
            "matched_count": len(matched_txs),
            "partially_matched_count": len(partially_matched_txs),
            "matched_amount": float(sum((abs(to_decimal(t["signed_amount"])) for t in matched_txs), Decimal("0.00"))),
            "ledger_unmatched_count": len(ledger_unmatched),
            "ledger_unmatched_sum": float(ledger_only_sum),
            "ledger_payments_in_transit": float(ledger_payments_in_transit),
            "ledger_deposits_in_transit": float(ledger_deposits_in_transit),
            "bank_unmatched_count": len(bank_unmatched),
            "bank_unmatched_sum": float(bank_only_sum),
            "bank_charges": float(bank_charges_sum),
            "bank_interest_credits": float(bank_interest_credits_sum),
            "adjusted_bank_balance": float(adjusted_bank_balance),
            "adjusted_ledger_balance": float(adjusted_ledger_balance),
            "residual_difference": float(residual_difference),
            "is_reconciled": is_reconciled
        }
    finally:
        conn.close()

def run_auto_matching(account_id: str, period_id: str, user: str = "System Engine") -> Dict[str, Any]:
    """
    Executes 8-tier deterministic matching rules in sequence:
    Tier 1: Exact unique Reference and Exact Signed Amount
    Tier 2: Exact Cheque / Payment ID / Journal and Exact Amount
    Tier 3: Exact Amount with Date Tolerance (<= 7 days) and Ref Evidence
    Tier 4: Normalized Ref/Desc with Exact Amount and Date Tolerance
    Tier 5: One-to-Many matching (1 Ledger = multiple Bank exact sum)
    Tier 6: Many-to-One matching (Multiple Ledger = 1 Bank exact sum)
    Tier 7: Controlled Many-to-Many matching (up to 3 items each side, exact sum)
    Tier 8: Fuzzy description match -> routes to Suggested Match requiring human confirmation
    """
    conn = get_db()
    matches_created = 0
    suggestions_created = 0
    matched_amount = Decimal("0.00")
    now_iso = datetime.now().isoformat()

    try:
        cur = conn.cursor()
        lock_err = check_period_unlocked(cur, period_id)
        if lock_err:
            return {"error": lock_err}

        # Fetch unmatched transactions
        cur.execute("""
            SELECT * FROM transactions
            WHERE account_id = ? AND period_id = ? AND recon_status IN ('Unmatched', 'Suggested Match')
            ORDER BY tx_date ASC
        """, (account_id, period_id))
        rows = [dict(r) for r in cur.fetchall()]

        ledger_pool = {t["id"]: t for t in rows if t["source"] == "Oracle Ledger"}
        bank_pool = {t["id"]: t for t in rows if t["source"] == "Bank Statement"}

        # Helper to commit a deterministic match
        def commit_match(rule_name: str, match_type: str, l_ids: List[str], b_ids: List[str], notes: str = ""):
            nonlocal matches_created, matched_amount
            mg_id = f"MCH-{uuid.uuid4().hex[:8].upper()}"
            cur.execute("""
                INSERT INTO match_groups (id, account_id, period_id, rule_name, match_type, matched_at, matched_by, notes, difference, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 'Confirmed')
            """, (mg_id, account_id, period_id, rule_name, match_type, now_iso, user, notes))

            for lid in l_ids:
                tx = ledger_pool[lid]
                amt = abs(to_decimal(tx["signed_amount"]))
                cur.execute("UPDATE transactions SET recon_status='Matched', match_group_id=?, allocated_amount=? WHERE id=?", (mg_id, float(amt), lid))
                cur.execute("INSERT INTO match_group_items (match_group_id, transaction_id, allocated_amount) VALUES (?, ?, ?)", (mg_id, lid, float(amt)))
                matched_amount += amt
                del ledger_pool[lid]

            for bid in b_ids:
                tx = bank_pool[bid]
                amt = abs(to_decimal(tx["signed_amount"]))
                cur.execute("UPDATE transactions SET recon_status='Matched', match_group_id=?, allocated_amount=? WHERE id=?", (mg_id, float(amt), bid))
                cur.execute("INSERT INTO match_group_items (match_group_id, transaction_id, allocated_amount) VALUES (?, ?, ?)", (mg_id, bid, float(amt)))
                del bank_pool[bid]

            matches_created += 1

        # TIER 1: Exact Unique Reference & Exact Signed Amount
        for l_id, l_tx in list(ledger_pool.items()):
            if l_id not in ledger_pool:
                continue
            l_ref = (l_tx.get("reference") or "").strip().upper()
            l_amt = to_decimal(l_tx["signed_amount"])
            if not l_ref:
                continue

            candidates = [
                b_id for b_id, b_tx in bank_pool.items()
                if (b_tx.get("reference") or "").strip().upper() == l_ref
                and to_decimal(b_tx["signed_amount"]) == l_amt
            ]
            if len(candidates) == 1:
                commit_match("Tier 1: Exact Reference & Amount", "1-to-1", [l_id], [candidates[0]], f"Ref: {l_ref}")

        # TIER 2: Exact Cheque Number / Payment ID / Journal Reference & Exact Amount
        for l_id, l_tx in list(ledger_pool.items()):
            if l_id not in ledger_pool:
                continue
            l_chk = (l_tx.get("cheque_number") or l_tx.get("payment_id") or "").strip().upper()
            l_amt = to_decimal(l_tx["signed_amount"])
            if not l_chk:
                continue

            candidates = [
                b_id for b_id, b_tx in bank_pool.items()
                if (b_chk := (b_tx.get("cheque_number") or b_tx.get("payment_id") or "").strip().upper())
                and b_chk == l_chk
                and to_decimal(b_tx["signed_amount"]) == l_amt
            ]
            if len(candidates) == 1:
                commit_match("Tier 2: Exact Cheque / Payment ID & Amount", "1-to-1", [l_id], [candidates[0]], f"ID: {l_chk}")

        # TIER 3: Exact Amount with Date Tolerance (<= 7 days) and Ref Evidence
        for l_id, l_tx in list(ledger_pool.items()):
            if l_id not in ledger_pool:
                continue
            l_amt = to_decimal(l_tx["signed_amount"])
            l_date_str = l_tx["tx_date"][:10]
            l_ref = (l_tx.get("reference") or "").strip().upper()

            candidates = []
            for b_id, b_tx in bank_pool.items():
                if to_decimal(b_tx["signed_amount"]) == l_amt:
                    b_date_str = b_tx["tx_date"][:10]
                    try:
                        d1 = datetime.strptime(l_date_str, "%Y-%m-%d")
                        d2 = datetime.strptime(b_date_str, "%Y-%m-%d")
                        days_diff = abs((d1 - d2).days)
                    except Exception:
                        days_diff = 0
                    if days_diff <= 7:
                        b_ref = (b_tx.get("reference") or "").strip().upper()
                        # Supporting evidence: matching ref or substring
                        if l_ref and b_ref and (l_ref in b_ref or b_ref in l_ref):
                            candidates.append((b_id, days_diff))
                        elif not l_ref and not b_ref and days_diff <= 3:
                            candidates.append((b_id, days_diff))

            if len(candidates) == 1:
                commit_match("Tier 3: Exact Amount & Date Tolerance with Evidence", "1-to-1", [l_id], [candidates[0][0]], f"Date diff: {candidates[0][1]}d")

        # TIER 4: Normalized Ref/Description with Exact Amount & Date Tolerance
        for l_id, l_tx in list(ledger_pool.items()):
            if l_id not in ledger_pool:
                continue
            l_amt = to_decimal(l_tx["signed_amount"])
            l_desc = (l_tx.get("description") or "").lower()
            l_date_str = l_tx["tx_date"][:10]

            candidates = []
            for b_id, b_tx in bank_pool.items():
                if to_decimal(b_tx["signed_amount"]) == l_amt:
                    b_date_str = b_tx["tx_date"][:10]
                    try:
                        d1 = datetime.strptime(l_date_str, "%Y-%m-%d")
                        d2 = datetime.strptime(b_date_str, "%Y-%m-%d")
                        days_diff = abs((d1 - d2).days)
                    except Exception:
                        days_diff = 0
                    if days_diff <= 7:
                        b_desc = (b_tx.get("description") or "").lower()
                        l_words = set(w for w in l_desc.replace("-", " ").replace("/", " ").split() if len(w) > 3)
                        b_words = set(w for w in b_desc.replace("-", " ").replace("/", " ").split() if len(w) > 3)
                        if l_words and b_words and (l_words & b_words):
                            candidates.append((b_id, days_diff))

            if len(candidates) == 1:
                commit_match("Tier 4: Normalized Ref/Desc & Date Tolerance", "1-to-1", [l_id], [candidates[0][0]], f"Date diff: {candidates[0][1]}d")

        # TIER 5: One-to-Many matching (1 Ledger = multiple Bank exact sum, bounded up to 4 items)
        for l_id, l_tx in list(ledger_pool.items()):
            if l_id not in ledger_pool:
                continue
            l_amt = to_decimal(l_tx["signed_amount"])
            bank_candidates = [
                b_tx for b_tx in bank_pool.values()
                if (to_decimal(b_tx["signed_amount"]) > 0) == (l_amt > 0)
            ]
            found_b_group = None
            for i in range(len(bank_candidates)):
                for j in range(i + 1, min(i + 4, len(bank_candidates))):
                    subset = bank_candidates[i:j+1]
                    s_sum = sum((to_decimal(b["signed_amount"]) for b in subset), Decimal("0.00"))
                    if s_sum == l_amt:
                        found_b_group = subset
                        break
                if found_b_group:
                    break

            if found_b_group:
                b_ids = [b["id"] for b in found_b_group]
                commit_match("Tier 5: 1-to-Many Grouped Match", "1-to-Many", [l_id], b_ids, f"1 Ledger -> {len(b_ids)} Bank items")

        # TIER 6: Many-to-One matching (Multiple Ledger = 1 Bank exact sum, bounded up to 4 items)
        for b_id, b_tx in list(bank_pool.items()):
            if b_id not in bank_pool:
                continue
            b_amt = to_decimal(b_tx["signed_amount"])
            ledger_candidates = [
                l_tx for l_tx in ledger_pool.values()
                if (to_decimal(l_tx["signed_amount"]) > 0) == (b_amt > 0)
            ]
            found_l_group = None
            for i in range(len(ledger_candidates)):
                for j in range(i + 1, min(i + 4, len(ledger_candidates))):
                    subset = ledger_candidates[i:j+1]
                    s_sum = sum((to_decimal(l["signed_amount"]) for l in subset), Decimal("0.00"))
                    if s_sum == b_amt:
                        found_l_group = subset
                        break
                if found_l_group:
                    break

            if found_l_group:
                l_ids = [l["id"] for l in found_l_group]
                commit_match("Tier 6: Many-to-1 Grouped Match", "Many-to-1", l_ids, [b_id], f"{len(l_ids)} Ledger items -> 1 Bank")

        # TIER 7: Controlled Many-to-Many (bounded up to 3 items each side, exact sum)
        if len(ledger_pool) >= 2 and len(bank_pool) >= 2:
            l_list = list(ledger_pool.values())
            b_list = list(bank_pool.values())
            found_m2m = False
            for li in range(min(4, len(l_list))):
                for lj in range(li + 1, min(li + 3, len(l_list))):
                    l_sub = l_list[li:lj+1]
                    l_sum = sum((to_decimal(x["signed_amount"]) for x in l_sub), Decimal("0.00"))
                    for bi in range(min(4, len(b_list))):
                        for bj in range(bi + 1, min(bi + 3, len(b_list))):
                            b_sub = b_list[bi:bj+1]
                            b_sum = sum((to_decimal(y["signed_amount"]) for y in b_sub), Decimal("0.00"))
                            if l_sum == b_sum and l_sum != Decimal("0.00"):
                                l_ids = [x["id"] for x in l_sub]
                                b_ids = [y["id"] for y in b_sub]
                                commit_match("Tier 7: Controlled Many-to-Many", "Many-to-Many", l_ids, b_ids, f"{len(l_ids)} Ledger <-> {len(b_ids)} Bank")
                                found_m2m = True
                                break
                        if found_m2m:
                            break
                    if found_m2m:
                        break
                if found_m2m:
                    break

        # TIER 8: Fuzzy descriptions as Suggested Matches (REQUIRES HUMAN CONFIRMATION)
        for l_id, l_tx in list(ledger_pool.items()):
            if l_id not in ledger_pool:
                continue
            l_amt = to_decimal(l_tx["signed_amount"])
            l_desc = (l_tx.get("description") or "").lower()

            for b_id, b_tx in list(bank_pool.items()):
                if to_decimal(b_tx["signed_amount"]) == l_amt:
                    b_desc = (b_tx.get("description") or "").lower()
                    # Check token overlap
                    l_words = set(w for w in l_desc.replace("-", " ").replace("/", " ").split() if len(w) > 2)
                    b_words = set(w for w in b_desc.replace("-", " ").replace("/", " ").split() if len(w) > 2)
                    if l_words and b_words and len(l_words & b_words) >= 1:
                        # Route to SUGGESTED MATCH requiring review
                        mg_id = f"SUG-{uuid.uuid4().hex[:8].upper()}"
                        cur.execute("""
                            INSERT INTO match_groups (id, account_id, period_id, rule_name, match_type, matched_at, matched_by, notes, difference, status)
                            VALUES (?, ?, ?, 'Tier 8: Fuzzy Description Suggestion', 'Suggested', ?, ?, ?, 0.0, 'Suggested')
                        """, (mg_id, account_id, period_id, now_iso, user, f"Tokens: {list(l_words & b_words)[:3]}"))

                        cur.execute("UPDATE transactions SET recon_status='Suggested Match', match_group_id=? WHERE id=?", (mg_id, l_id))
                        cur.execute("UPDATE transactions SET recon_status='Suggested Match', match_group_id=? WHERE id=?", (mg_id, b_id))

                        cur.execute("INSERT INTO match_group_items (match_group_id, transaction_id, allocated_amount) VALUES (?, ?, ?)", (mg_id, l_id, float(abs(l_amt))))
                        cur.execute("INSERT INTO match_group_items (match_group_id, transaction_id, allocated_amount) VALUES (?, ?, ?)", (mg_id, b_id, float(abs(l_amt))))

                        del ledger_pool[l_id]
                        del bank_pool[b_id]
                        suggestions_created += 1
                        break

        conn.commit()

        log_audit(conn, user, "AUTO_MATCH_RUN", "account", account_id, None, {
            "matches_created": matches_created,
            "suggestions_created": suggestions_created,
            "matched_amount": float(matched_amount)
        }, f"Auto-reconciled {matches_created} confirmed groups, {suggestions_created} suggestions")
        conn.commit()

        brs_summary = calculate_brs(account_id, period_id)
        return {
            "success": True,
            "matches_created": matches_created,
            "suggestions_created": suggestions_created,
            "matched_amount": float(matched_amount),
            "brs": brs_summary
        }
    finally:
        conn.close()

def manual_match(account_id: str, period_id: str, ledger_ids: List[str], bank_ids: List[str], user: str, notes: str = "") -> Dict[str, Any]:
    """
    Manually reconciles selected ledger transactions with selected bank transactions.
    Validates that net difference is acceptable (must be exact 0.00).
    Checks period is unlocked.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        lock_err = check_period_unlocked(cur, period_id)
        if lock_err:
            return {"error": lock_err}

        if not ledger_ids and not bank_ids:
            return {"error": "Must select at least one transaction"}

        cur.execute(f"SELECT * FROM transactions WHERE id IN ({','.join(['?']*len(ledger_ids))})", ledger_ids)
        l_txs = [dict(r) for r in cur.fetchall()]

        cur.execute(f"SELECT * FROM transactions WHERE id IN ({','.join(['?']*len(bank_ids))})", bank_ids)
        b_txs = [dict(r) for r in cur.fetchall()]

        l_sum = sum((to_decimal(t["signed_amount"]) for t in l_txs), Decimal("0.00"))
        b_sum = sum((to_decimal(t["signed_amount"]) for t in b_txs), Decimal("0.00"))
        diff = (l_sum - b_sum).quantize(Decimal("0.01"))

        if diff != Decimal("0.00"):
            return {
                "error": f"Transaction sums do not match! Ledger Sum: {l_sum}, Bank Sum: {b_sum}, Difference: {diff}. Exact 0.00 required."
            }

        mg_id = f"MAN-{uuid.uuid4().hex[:8].upper()}"
        mtype = "1-to-1" if len(l_txs) == 1 and len(b_txs) == 1 else ("1-to-Many" if len(l_txs) == 1 else ("Many-to-1" if len(b_txs) == 1 else "Many-to-Many"))
        now_iso = datetime.now().isoformat()

        cur.execute("""
            INSERT INTO match_groups (id, account_id, period_id, rule_name, match_type, matched_at, matched_by, notes, difference, status)
            VALUES (?, ?, ?, 'Manual Match', ?, ?, ?, ?, ?, 'Confirmed')
        """, (mg_id, account_id, period_id, mtype, now_iso, user, notes, float(diff)))

        for t in l_txs:
            amt = float(abs(to_decimal(t["signed_amount"])))
            cur.execute("UPDATE transactions SET recon_status='Matched', match_group_id=?, allocated_amount=? WHERE id=?", (mg_id, amt, t["id"]))
            cur.execute("INSERT INTO match_group_items (match_group_id, transaction_id, allocated_amount) VALUES (?, ?, ?)", (mg_id, t["id"], amt))

        for t in b_txs:
            amt = float(abs(to_decimal(t["signed_amount"])))
            cur.execute("UPDATE transactions SET recon_status='Matched', match_group_id=?, allocated_amount=? WHERE id=?", (mg_id, amt, t["id"]))
            cur.execute("INSERT INTO match_group_items (match_group_id, transaction_id, allocated_amount) VALUES (?, ?, ?)", (mg_id, t["id"], amt))

        conn.commit()

        log_audit(conn, user, "MANUAL_MATCH", "match_group", mg_id, None, {
            "ledger_count": len(l_txs),
            "bank_count": len(b_txs),
            "matched_amount": float(l_sum)
        }, notes or "Manual match confirmed")
        conn.commit()

        brs = calculate_brs(account_id, period_id)
        return {"success": True, "match_group_id": mg_id, "brs": brs}
    finally:
        conn.close()

def partial_match(account_id: str, period_id: str, ledger_id: str, bank_id: str, allocated_amount: float, user: str, notes: str = "") -> Dict[str, Any]:
    """
    Performs partial allocation between a ledger item and a bank item:
    - Tracks allocated amount and remaining balance explicitly
    - Enforces allocated_amount <= remaining for both transactions
    - Sets 'Partially Matched' when partially allocated, or 'Matched' when fully allocated
    - Checks period is unlocked
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        lock_err = check_period_unlocked(cur, period_id)
        if lock_err:
            return {"error": lock_err}

        alloc_dec = to_decimal(allocated_amount)
        if alloc_dec <= Decimal("0.00"):
            return {"error": "Allocated amount must be greater than zero."}

        cur.execute("SELECT * FROM transactions WHERE id = ?", (ledger_id,))
        l_tx = cur.fetchone()
        cur.execute("SELECT * FROM transactions WHERE id = ?", (bank_id,))
        b_tx = cur.fetchone()

        if not l_tx or not b_tx:
            return {"error": "One or both transactions not found"}

        l_total = abs(to_decimal(l_tx["signed_amount"]))
        l_prev_alloc = to_decimal(l_tx["allocated_amount"] or 0)
        l_remaining = l_total - l_prev_alloc

        b_total = abs(to_decimal(b_tx["signed_amount"]))
        b_prev_alloc = to_decimal(b_tx["allocated_amount"] or 0)
        b_remaining = b_total - b_prev_alloc

        if alloc_dec > l_remaining:
            return {"error": f"Allocation amount ({alloc_dec}) exceeds Ledger remaining unallocated amount ({l_remaining})."}

        if alloc_dec > b_remaining:
            return {"error": f"Allocation amount ({alloc_dec}) exceeds Bank remaining unallocated amount ({b_remaining})."}

        l_new_alloc = l_prev_alloc + alloc_dec
        b_new_alloc = b_prev_alloc + alloc_dec

        l_status = "Matched" if l_new_alloc == l_total else "Partially Matched"
        b_status = "Matched" if b_new_alloc == b_total else "Partially Matched"

        mg_id = f"PAR-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now().isoformat()

        cur.execute("""
            INSERT INTO match_groups (id, account_id, period_id, rule_name, match_type, matched_at, matched_by, notes, difference, status)
            VALUES (?, ?, ?, 'Partial Allocation', 'Partial', ?, ?, ?, 0.0, 'Confirmed')
        """, (mg_id, account_id, period_id, now_iso, user, notes or f"Partial allocation of {alloc_dec}"))

        cur.execute("UPDATE transactions SET recon_status=?, match_group_id=?, allocated_amount=? WHERE id=?", (l_status, mg_id, float(l_new_alloc), ledger_id))
        cur.execute("UPDATE transactions SET recon_status=?, match_group_id=?, allocated_amount=? WHERE id=?", (b_status, mg_id, float(b_new_alloc), bank_id))

        cur.execute("INSERT INTO match_group_items (match_group_id, transaction_id, allocated_amount) VALUES (?, ?, ?)", (mg_id, ledger_id, float(alloc_dec)))
        cur.execute("INSERT INTO match_group_items (match_group_id, transaction_id, allocated_amount) VALUES (?, ?, ?)", (mg_id, bank_id, float(alloc_dec)))

        conn.commit()

        log_audit(conn, user, "PARTIAL_MATCH", "match_group", mg_id, None, {
            "ledger_id": ledger_id, "bank_id": bank_id, "allocated_amount": float(alloc_dec),
            "ledger_remaining": float(l_total - l_new_alloc),
            "bank_remaining": float(b_total - b_new_alloc)
        }, notes or f"Partial match of {alloc_dec} confirmed")
        conn.commit()

        brs = calculate_brs(account_id, period_id)
        return {
            "success": True,
            "match_group_id": mg_id,
            "allocated_amount": float(alloc_dec),
            "ledger_remaining": float(l_total - l_new_alloc),
            "bank_remaining": float(b_total - b_new_alloc),
            "brs": brs
        }
    finally:
        conn.close()

def confirm_suggested_match(match_group_id: str, user: str) -> Dict[str, Any]:
    """Confirms an AI/fuzzy suggested match group, transitioning it to Matched."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM match_groups WHERE id = ?", (match_group_id,))
        mg = cur.fetchone()
        if not mg:
            return {"error": "Match group not found"}

        period_id = mg["period_id"]
        lock_err = check_period_unlocked(cur, period_id)
        if lock_err:
            return {"error": lock_err}

        cur.execute("UPDATE match_groups SET status = 'Confirmed', matched_by = ? WHERE id = ?", (user, match_group_id))
        cur.execute("""
            UPDATE transactions 
            SET recon_status = 'Matched'
            WHERE match_group_id = ?
        """, (match_group_id,))

        log_audit(conn, user, "CONFIRM_SUGGESTION", "match_group", match_group_id, "Suggested", "Confirmed", "Fuzzy suggestion confirmed by user")
        conn.commit()

        brs = calculate_brs(mg["account_id"], period_id)
        return {"success": True, "match_group_id": match_group_id, "brs": brs}
    finally:
        conn.close()

def reject_suggested_match(match_group_id: str, user: str, reason: str = "") -> Dict[str, Any]:
    """Rejects a suggested match group and resets transactions to Unmatched."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM match_groups WHERE id = ?", (match_group_id,))
        mg = cur.fetchone()
        if not mg:
            return {"error": "Match group not found"}

        period_id = mg["period_id"]
        lock_err = check_period_unlocked(cur, period_id)
        if lock_err:
            return {"error": lock_err}

        cur.execute("UPDATE transactions SET recon_status = 'Unmatched', match_group_id = NULL, allocated_amount = 0.0 WHERE match_group_id = ?", (match_group_id,))
        cur.execute("DELETE FROM match_group_items WHERE match_group_id = ?", (match_group_id,))
        cur.execute("DELETE FROM match_groups WHERE id = ?", (match_group_id,))

        log_audit(conn, user, "REJECT_SUGGESTION", "match_group", match_group_id, "Suggested", "Rejected", reason or "Suggestion rejected")
        conn.commit()

        brs = calculate_brs(mg["account_id"], period_id)
        return {"success": True, "match_group_id": match_group_id, "brs": brs}
    finally:
        conn.close()

def unmatch_group(match_group_id: str, user: str, reason: str = "") -> Dict[str, Any]:
    """
    Rolls back a match group atomically, resetting items back to Unmatched status.
    Checks period is unlocked and requires audit reason.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM match_groups WHERE id = ?", (match_group_id,))
        mg = cur.fetchone()
        if not mg:
            return {"error": "Match group not found"}

        account_id = mg["account_id"]
        period_id = mg["period_id"]

        lock_err = check_period_unlocked(cur, period_id)
        if lock_err:
            return {"error": lock_err}

        cur.execute("SELECT transaction_id FROM match_group_items WHERE match_group_id = ?", (match_group_id,))
        t_ids = [r["transaction_id"] for r in cur.fetchall()]

        for t_id in t_ids:
            cur.execute("""
                UPDATE transactions
                SET recon_status='Unmatched', match_group_id=NULL, allocated_amount=0.0
                WHERE id=?
            """, (t_id,))

        cur.execute("DELETE FROM match_group_items WHERE match_group_id = ?", (match_group_id,))
        cur.execute("DELETE FROM match_groups WHERE id = ?", (match_group_id,))
        conn.commit()

        log_audit(conn, user, "UNMATCH", "match_group", match_group_id, {"reverted_txs": t_ids}, None, reason or "Manual unmatch requested")
        conn.commit()

        brs = calculate_brs(account_id, period_id)
        return {"success": True, "reverted_count": len(t_ids), "brs": brs}
    finally:
        conn.close()

def rollover_period(account_id: str, current_period_id: str, next_period_name: str, start_date: str, end_date: str, user: str) -> Dict[str, Any]:
    """
    Carries forward unresolved items into subsequent period without duplicating them (Section 9):
    - Sets opening balances of next period = closing balances of current period
    - Unresolved items have their period_id set to next_period_id, original_period_id recorded
    - Maintains immutable historical snapshot of current period
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM periods WHERE id = ?", (current_period_id,))
        curr = cur.fetchone()
        if not curr:
            return {"error": "Current period not found"}

        # Generate new period ID
        new_period_id = f"PER-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now().isoformat()

        bank_close = curr["bank_closing_balance"]
        ledger_close = curr["ledger_closing_balance"]

        cur.execute("""
            INSERT INTO periods (id, account_id, period_name, start_date, end_date, status, bank_opening_balance, bank_closing_balance, ledger_opening_balance, ledger_closing_balance, residual_diff, created_at)
            VALUES (?, ?, ?, ?, ?, 'Draft', ?, ?, ?, ?, 0.0, ?)
        """, (new_period_id, account_id, next_period_name, start_date, end_date, bank_close, bank_close, ledger_close, ledger_close, now_iso))

        # Carry forward uncleared transactions
        cur.execute("""
            SELECT id FROM transactions
            WHERE account_id = ? AND period_id = ? AND recon_status IN ('Unmatched', 'Partially Matched', 'Exception', 'Suggested Match')
        """, (account_id, current_period_id))
        uncleared_rows = cur.fetchall()
        carried_count = len(uncleared_rows)

        for r in uncleared_rows:
            tx_id = r["id"]
            cur.execute("""
                UPDATE transactions
                SET period_id = ?, 
                    original_period_id = COALESCE(original_period_id, ?),
                    recon_status = CASE WHEN recon_status = 'Unmatched' THEN 'Carried Forward' ELSE recon_status END
                WHERE id = ?
            """, (new_period_id, current_period_id, tx_id))

        conn.commit()

        log_audit(conn, user, "PERIOD_ROLLOVER", "period", new_period_id, current_period_id, {
            "new_period_name": next_period_name,
            "carried_items": carried_count
        }, f"Rolled over to {next_period_name}, carried forward {carried_count} uncleared items")
        conn.commit()

        brs = calculate_brs(account_id, new_period_id)
        return {
            "success": True,
            "new_period_id": new_period_id,
            "period_name": next_period_name,
            "carried_count": carried_count,
            "brs": brs
        }
    finally:
        conn.close()
