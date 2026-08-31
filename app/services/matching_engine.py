from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Iterable, Tuple
from sqlalchemy.orm import Session
from app.models.card_qr_rec import CardQrReconciliation
from app.models.bank_transaction import BankTransaction
from app.models.reconciliation_match import ReconciliationMatch
from app.services.audit_service import log_action
from app.core.config import settings


def _unmatched_credits(db: Session) -> List[BankTransaction]:
    return db.query(BankTransaction).filter(
        BankTransaction.is_matched == False,
        BankTransaction.credit_amount > 0
    ).order_by(BankTransaction.tx_date.asc(), BankTransaction.id.asc()).all()


def _pending_recs(db: Session) -> List[CardQrReconciliation]:
    return db.query(CardQrReconciliation).filter(
        CardQrReconciliation.status.in_(["PENDING", "DIFFERENCE"])
    ).order_by(CardQrReconciliation.sale_date.asc(), CardQrReconciliation.id.asc()).all()


def _settlement_score(sales: float, received: float, lag_days: int, max_lag: int) -> Optional[float]:
    """Score a sale vs a later bank credit. Received is usually 0–5% lower (MDR / PG charges)."""
    if sales <= 0 or received <= 0 or lag_days < 0 or lag_days > max_lag:
        return None
    ratio = received / sales
    if ratio < 0.90 or ratio > 1.002:
        return None
    charge_pct = max(0.0, (sales - received) / sales)
    if charge_pct <= 0.025:
        amount_score = 1.0
    elif charge_pct <= 0.05:
        amount_score = 0.78
    else:
        amount_score = 0.5
    date_weights = {0: 0.86, 1: 1.0, 2: 0.93, 3: 0.78}
    date_score = date_weights.get(lag_days, 0.65)
    return round(amount_score * date_score, 4)


def _link_rec_to_txs(
    db: Session,
    rec: CardQrReconciliation,
    txs: List[BankTransaction],
    method: str,
    confidence: float,
    user=None,
    reason: str = ""
) -> None:
    total = round(sum(float(t.credit_amount or 0) for t in txs), 2)
    rec.received_amount = total
    rec.settlement_date = max(t.tx_date for t in txs)
    labels = []
    for t in txs:
        labels.append(t.reference_no or t.bank_account or f"Tx {t.id}")
    rec.bank_reference = " + ".join(labels)[:100]
    rec.bank_account = (txs[0].bank_account or "")[:50]
    rec.bank_transaction_id = txs[0].id
    rec.difference = round((rec.card_qr_sales_amount or 0) - rec.received_amount, 2)
    rec.status = "MATCHED"
    rec.match_method = method
    charge_note = f"Bank / PG charges {rec.difference:,.2f}." if abs(rec.difference) >= 0.01 else "Exact settlement."
    rec.remarks = (reason or f"Auto matched via {method}. {charge_note}").strip()

    for t in txs:
        t.is_matched = True
        t.matched_type = "CARD_QR"
        db.add(ReconciliationMatch(
            match_type="CARD_QR",
            source_entity="card_qr_reconciliations",
            source_id=rec.id,
            target_entity="bank_transactions",
            target_id=t.id,
            match_method=method,
            confidence_score=confidence,
            matched_by=user.full_name if user else "SYSTEM",
            reason=rec.remarks
        ))


def _best_subset(sales: float, txs: List[BankTransaction], lag_days: int, max_lag: int) -> Tuple[Optional[List[BankTransaction]], float]:
    if not txs:
        return None, 0.0
    ordered = sorted(txs, key=lambda t: float(t.credit_amount or 0), reverse=True)
    picked: List[BankTransaction] = []
    running = 0.0
    ceiling = sales * 1.002
    for t in ordered:
        amt = float(t.credit_amount or 0)
        if running + amt <= ceiling:
            picked.append(t)
            running += amt
    score = _settlement_score(sales, running, lag_days, max_lag) if picked else None
    if score:
        return picked, score
    all_total = sum(float(t.credit_amount or 0) for t in txs)
    all_score = _settlement_score(sales, all_total, lag_days, max_lag)
    if all_score:
        return list(txs), all_score
    return None, 0.0


def _ai_suggest_matches(
    recs: List[CardQrReconciliation],
    txs: List[BankTransaction],
    max_lag: int
) -> List[Dict[str, Any]]:
    if not recs or not txs:
        return []
    try:
        from app.services.ai_vision_ocr import (
            get_gemini_api_key, _gemini_headers, _pick_gemini_models, _extract_json
        )
        import httpx
    except Exception:
        return []

    api_key = get_gemini_api_key()
    if not api_key:
        return []

    sales_payload = [
        {
            "rec_id": r.id,
            "branch": r.branch.name if r.branch else "",
            "sale_date": r.sale_date.strftime("%Y-%m-%d"),
            "amount": round(float(r.card_qr_sales_amount or 0), 2),
        }
        for r in recs
    ]
    credit_payload = [
        {
            "tx_id": t.id,
            "tx_date": t.tx_date.strftime("%Y-%m-%d"),
            "bank": t.bank_account,
            "amount": round(float(t.credit_amount or 0), 2),
            "description": (t.description or "")[:80],
        }
        for t in txs
    ]
    prompt = (
        "You reconcile Indian restaurant Card/QR day-book sales to bank settlement credits.\n"
        f"Credits usually arrive 1 to {max_lag} days AFTER the sale date.\n"
        "Received amount is usually 0-5% lower than sales because of bank / payment-gateway MDR.\n"
        "Ignore Sales and Service Charge journal ideas — only the bank credits listed here exist.\n"
        "One credit can be used only once. One sale may be settled by several same-day credits.\n"
        "Return JSON only: {\"matches\":[{\"rec_id\":1,\"tx_ids\":[10,11],\"reason\":\"...\"}]}\n"
        "Only high-confidence matches. Leave doubtful items unmatched.\n\n"
        f"SALES: {sales_payload}\n\nCREDITS: {credit_payload}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(25.0, connect=10.0)) as client:
            models = _pick_gemini_models(client, api_key)
            for model in models[:3]:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                res = client.post(url, headers=_gemini_headers(api_key), json=payload)
                if res.status_code >= 400:
                    continue
                parts = (((res.json().get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
                text = "".join(p.get("text") or "" for p in parts)
                if not text:
                    continue
                data = _extract_json(text)
                matches = data.get("matches") if isinstance(data, dict) else None
                if isinstance(matches, list):
                    return matches
    except Exception:
        return []
    return []


def run_card_qr_auto_matching(db: Session, date_tolerance_days: int = 3, user=None) -> Dict[str, int]:
    max_lag = date_tolerance_days or getattr(settings, "DEFAULT_DATE_TOLERANCE_DAYS", 3) or 3
    pending_recs = [r for r in _pending_recs(db) if (r.card_qr_sales_amount or 0) > 0 and (r.received_amount or 0) <= 0]
    unused = {t.id: t for t in _unmatched_credits(db)}
    matched_count = 0
    used_rec_ids = set()

    def take_txs(tx_list: Iterable[BankTransaction]) -> List[BankTransaction]:
        chosen = []
        for t in tx_list:
            live = unused.pop(t.id, None)
            if live is not None:
                chosen.append(live)
        return chosen

    # PASS 1: exact reference
    for rec in pending_recs:
        if rec.id in used_rec_ids or not rec.bank_reference:
            continue
        hit = next((t for t in unused.values() if t.reference_no == rec.bank_reference), None)
        if not hit:
            continue
        chosen = take_txs([hit])
        if chosen:
            _link_rec_to_txs(db, rec, chosen, "EXACT_REF", 1.0, user)
            used_rec_ids.add(rec.id)
            matched_count += 1

    # PASS 2: exact amount + same date
    for rec in pending_recs:
        if rec.id in used_rec_ids:
            continue
        sales = round(float(rec.card_qr_sales_amount or 0), 2)
        hit = next((
            t for t in unused.values()
            if t.tx_date == rec.sale_date and round(float(t.credit_amount or 0), 2) == sales
        ), None)
        if not hit:
            continue
        chosen = take_txs([hit])
        if chosen:
            _link_rec_to_txs(db, rec, chosen, "EXACT_AMOUNT_DATE", 0.95, user)
            used_rec_ids.add(rec.id)
            matched_count += 1

    # PASS 3: exact amount + 0–N day lag
    for rec in pending_recs:
        if rec.id in used_rec_ids:
            continue
        sales = round(float(rec.card_qr_sales_amount or 0), 2)
        window_end = rec.sale_date + timedelta(days=max_lag)
        hit = next((
            t for t in unused.values()
            if rec.sale_date <= t.tx_date <= window_end and round(float(t.credit_amount or 0), 2) == sales
        ), None)
        if not hit:
            continue
        chosen = take_txs([hit])
        if chosen:
            _link_rec_to_txs(db, rec, chosen, "DATE_TOLERANCE", 0.85, user)
            used_rec_ids.add(rec.id)
            matched_count += 1

    # PASS 4: charge-aware single credit (received slightly less than sales)
    candidates: List[Tuple[float, CardQrReconciliation, BankTransaction]] = []
    for rec in pending_recs:
        if rec.id in used_rec_ids:
            continue
        sales = float(rec.card_qr_sales_amount or 0)
        for t in unused.values():
            lag = (t.tx_date - rec.sale_date).days
            score = _settlement_score(sales, float(t.credit_amount or 0), lag, max_lag)
            if score:
                candidates.append((score, rec, t))
    candidates.sort(key=lambda item: item[0], reverse=True)
    for score, rec, tx in candidates:
        if rec.id in used_rec_ids or tx.id not in unused:
            continue
        chosen = take_txs([tx])
        if chosen:
            _link_rec_to_txs(db, rec, chosen, "CHARGES_WINDOW", score, user,
                             f"AI reconcile: bank credit {lag_label(rec, chosen)} with MDR/charges.")
            used_rec_ids.add(rec.id)
            matched_count += 1

    # PASS 5: same-day credit combinations (Kotak + Axis etc.)
    for rec in pending_recs:
        if rec.id in used_rec_ids:
            continue
        sales = float(rec.card_qr_sales_amount or 0)
        best_txs, best_score = None, 0.0
        for lag in range(0, max_lag + 1):
            day = rec.sale_date + timedelta(days=lag)
            day_txs = [t for t in unused.values() if t.tx_date == day]
            picked, score = _best_subset(sales, day_txs, lag, max_lag)
            if picked and score > best_score:
                best_txs, best_score = picked, score
        if best_txs:
            chosen = take_txs(best_txs)
            if chosen:
                _link_rec_to_txs(db, rec, chosen, "CHARGES_COMBO", best_score, user,
                                 f"AI reconcile: combined bank credits {lag_label(rec, chosen)}.")
                used_rec_ids.add(rec.id)
                matched_count += 1

    # PASS 6: Gemini assignment for leftovers when a key is configured
    leftover_recs = [r for r in pending_recs if r.id not in used_rec_ids]
    leftover_txs = list(unused.values())
    suggestions = _ai_suggest_matches(leftover_recs, leftover_txs, max_lag)
    rec_by_id = {r.id: r for r in leftover_recs}
    for item in suggestions:
        try:
            rec_id = int(item.get("rec_id"))
            tx_ids = [int(x) for x in (item.get("tx_ids") or [])]
        except (TypeError, ValueError):
            continue
        rec = rec_by_id.get(rec_id)
        if not rec or rec.id in used_rec_ids:
            continue
        chosen_src = [unused[i] for i in tx_ids if i in unused]
        if not chosen_src:
            continue
        sales = float(rec.card_qr_sales_amount or 0)
        received = sum(float(t.credit_amount or 0) for t in chosen_src)
        lag = min((t.tx_date - rec.sale_date).days for t in chosen_src)
        if _settlement_score(sales, received, lag, max_lag) is None and not (0 <= lag <= max_lag and 0.90 <= received / sales <= 1.002):
            continue
        chosen = take_txs(chosen_src)
        if chosen:
            _link_rec_to_txs(db, rec, chosen, "AI_GEMINI", 0.8, user,
                             item.get("reason") or "Gemini suggested this Card/QR settlement.")
            used_rec_ids.add(rec.id)
            matched_count += 1

    db.commit()
    log_action(db, "AUTO_MATCH_CARD_QR", "CardQrReconciliation", None, None, {"matched_count": matched_count}, user=user)
    return {"matched_count": matched_count}


def lag_label(rec: CardQrReconciliation, txs: List[BankTransaction]) -> str:
    dates = sorted({t.tx_date.strftime("%d-%b") for t in txs})
    return f"{rec.sale_date.strftime('%d-%b')} → {', '.join(dates)}"


def manual_match_card_qr(
    db: Session,
    card_qr_rec_id: int,
    bank_tx_id: int,
    reason: str,
    user=None
) -> CardQrReconciliation:
    rec = db.query(CardQrReconciliation).filter(CardQrReconciliation.id == card_qr_rec_id).first()
    bank_tx = db.query(BankTransaction).filter(BankTransaction.id == bank_tx_id).first()

    if not rec or not bank_tx:
        raise ValueError("Record or Bank Transaction not found")

    _link_rec_to_txs(db, rec, [bank_tx], "MANUAL", 1.0, user, f"Manually matched: {reason}")
    rec.status = "MANUALLY_MATCHED"
    rec.match_method = "MANUAL"
    db.commit()
    db.refresh(rec)

    log_action(db, "MANUAL_MATCH", "CardQrReconciliation", rec.id, None, {"bank_tx_id": bank_tx.id, "reason": reason}, user=user)
    return rec
