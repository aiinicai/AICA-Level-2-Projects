"""Phase 4 — lender / partner-capital / customer-advance register and
source-of-funds analysis.

For each party the user records the amount, date, mode and the status of each
evidence item (AVAILABLE / NOT_PROVIDED / REQUIRES_VERIFICATION / NOT_APPLICABLE).
The analysis maps evidence to the three aspects ordinarily examined for credits
— identity, creditworthiness/capacity, genuineness — and to the source of the
creditor's funds, and raises cash-mode prompts. It never concludes that a
credit is explained or unexplained; it shows what is and is not supported.
"""
from __future__ import annotations

from datetime import date

from ..core import audit
from ..core.db import dumps, ro, row_to_dict, tx, utcnow
from ..core.errors import NotFound, ValidationError
from . import cases

EV_STATUSES = ("AVAILABLE", "NOT_PROVIDED", "REQUIRES_VERIFICATION", "NOT_APPLICABLE")
MODES = ("BANK", "CASH", "CHEQUE", "ADJUSTMENT", "OTHER")

CHECKLISTS = {
    "LENDER": {
        "confirmation": ("Signed loan confirmation", ["identity", "genuineness"]),
        "pan": ("Lender PAN", ["identity"]),
        "itr": ("Lender ITR acknowledgement & computation", ["creditworthiness"]),
        "lender_bank_statement": ("Lender bank statement around loan date", ["creditworthiness", "genuineness", "source_of_source"]),
        "loan_agreement": ("Loan agreement / terms", ["genuineness"]),
        "interest_tds": ("Interest paid & TDS (if interest-bearing)", ["genuineness"]),
        "repayment_trail": ("Repayment / subsequent trail", ["genuineness"]),
        "source_explanation": ("Explanation of lender's source of funds", ["source_of_source"]),
    },
    "PARTNER_CAPITAL": {
        "partner_confirmation": ("Partner confirmation of contribution", ["identity", "genuineness"]),
        "pan": ("Partner PAN", ["identity"]),
        "partner_itr": ("Partner ITR", ["creditworthiness"]),
        "partner_bank_or_cashbook": ("Partner bank statement / personal cash book", ["creditworthiness", "source_of_source"]),
        "capital_account_entry": ("Entry in firm's capital account & cash/bank book", ["genuineness"]),
        "partnership_deed": ("Partnership deed (capital clause)", ["genuineness"]),
        "source_explanation": ("Partner's explanation of source", ["source_of_source"]),
    },
    "CUSTOMER_ADVANCE": {
        "customer_confirmation": ("Customer confirmation of advance", ["identity", "genuineness"]),
        "order_or_agreement": ("Purchase order / agreement", ["genuineness"]),
        "subsequent_invoice_or_refund": ("Subsequent invoice / adjustment or refund", ["genuineness"]),
        "customer_pan_gstin": ("Customer PAN / GSTIN", ["identity"]),
    },
}
ASPECTS = ("identity", "creditworthiness", "genuineness", "source_of_source")


def _validate(record_type, party_name, amount, txn_date, mode, ev):
    if record_type not in CHECKLISTS:
        raise ValidationError(f"record_type must be one of {sorted(CHECKLISTS)}.")
    if not party_name or len(party_name) > 200:
        raise ValidationError("party_name required (≤200 chars).")
    if amount is None or float(amount) <= 0:
        raise ValidationError("amount must be positive.")
    if txn_date:
        try:
            date.fromisoformat(txn_date)
        except ValueError:
            raise ValidationError("txn_date must be YYYY-MM-DD.")
    if mode and mode not in MODES:
        raise ValidationError(f"mode must be one of {MODES}.")
    for k, v in (ev or {}).items():
        if k in ("lender_cash_deposit_before",):
            continue
        if k not in CHECKLISTS[record_type]:
            raise ValidationError(f"Unknown evidence item '{k}' for {record_type}.")
        if v not in EV_STATUSES:
            raise ValidationError(f"Evidence status must be one of {EV_STATUSES}.")


def upsert(user: dict, case_id: int, *, record_type: str, party_name: str, amount: float, txn_date: str | None = None,
           mode: str | None = None, evidence: dict | None = None, observations: str = "", issue_id: int | None = None,
           record_id: int | None = None) -> dict:
    cases.check_access(user, case_id)
    _validate(record_type, party_name, amount, txn_date, mode, evidence)
    ev = {k: "NOT_PROVIDED" for k in CHECKLISTS[record_type]}
    ev.update(evidence or {})
    lcd = ev.get("lender_cash_deposit_before")
    if lcd is not None:
        if not isinstance(lcd, dict) or float(lcd.get("amount", 0)) <= 0:
            raise ValidationError("lender_cash_deposit_before must be {amount, date, explained}.")
    now = utcnow()
    with tx() as conn:
        if record_id:
            r = conn.execute("SELECT case_id FROM party_records WHERE id=?", (record_id,)).fetchone()
            if not r or r["case_id"] != case_id:
                raise NotFound("Record not found in this case.")
            conn.execute("UPDATE party_records SET record_type=?, party_name=?, amount=?, txn_date=?, mode=?, evidence_json=?, "
                         "observations=?, issue_id=?, updated_at=? WHERE id=?",
                         (record_type, party_name.strip(), float(amount), txn_date, mode, dumps(ev), (observations or "")[:2000],
                          issue_id, now, record_id))
            rid = record_id
        else:
            cur = conn.execute("INSERT INTO party_records(case_id,record_type,party_name,amount,txn_date,mode,evidence_json,observations,"
                               "issue_id,created_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                               (case_id, record_type, party_name.strip(), float(amount), txn_date, mode, dumps(ev),
                                (observations or "")[:2000], issue_id, user["id"], now, now))
            rid = cur.lastrowid
        audit.log_event(conn, "PARTY_RECORD_SAVED", user_id=user["id"], case_id=case_id,
                        meta={"record_id": rid, "record_type": record_type, "amount": float(amount)})
    return get(user, rid)


def get(user: dict, record_id: int) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT * FROM party_records WHERE id=?", (record_id,)).fetchone()
    if not r:
        raise NotFound("Record not found.")
    d = row_to_dict(r, ("evidence_json",))
    cases.check_access(user, d["case_id"])
    d["analysis"] = analyse(d)
    return d


def list_records(user: dict, case_id: int, record_type: str | None = None) -> list[dict]:
    cases.check_access(user, case_id)
    with ro() as conn:
        q = "SELECT id FROM party_records WHERE case_id=?" + (" AND record_type=?" if record_type else "") + " ORDER BY txn_date, id"
        ids = [r["id"] for r in conn.execute(q, (case_id, record_type) if record_type else (case_id,))]
    return [get(user, i) for i in ids]


def delete(user: dict, record_id: int) -> None:
    d = get(user, record_id)
    with tx() as conn:
        conn.execute("DELETE FROM party_records WHERE id=?", (record_id,))
        audit.log_event(conn, "PARTY_RECORD_DELETED", user_id=user["id"], case_id=d["case_id"], meta={"record_id": record_id})


def analyse(rec: dict) -> dict:
    cl = CHECKLISTS[rec["record_type"]]
    ev = rec["evidence_json"]
    aspects = {}
    for a in ASPECTS:
        items = [(k, lbl) for k, (lbl, asp) in cl.items() if a in asp]
        if not items:
            continue
        st = [ev.get(k, "NOT_PROVIDED") for k, _ in items]
        relevant = [s for s in st if s != "NOT_APPLICABLE"]
        if relevant and all(s == "AVAILABLE" for s in relevant):
            level = "SUPPORTED_BY_DOCUMENTS"
        elif any(s == "AVAILABLE" for s in relevant):
            level = "PARTLY_SUPPORTED"
        elif any(s == "REQUIRES_VERIFICATION" for s in relevant):
            level = "REQUIRES_VERIFICATION"
        else:
            level = "NOT_SUPPORTED" if relevant else "NOT_APPLICABLE"
        aspects[a] = {"status": level, "items": [{"key": k, "label": lbl, "status": ev.get(k, "NOT_PROVIDED")} for k, lbl in items]}
    flags = []
    amt, mode = rec["amount"], rec.get("mode")
    if mode == "CASH":
        if rec["record_type"] in ("LENDER", "PARTNER_CAPITAL", "CUSTOMER_ADVANCE") and amt >= 20000:
            flags.append("Cash receipt ≥ ₹20,000 — examine s.269SS (loan/deposit/specified sum) applicability; CA judgement required.")
        if amt >= 200000:
            flags.append("Cash receipt ≥ ₹2,00,000 — examine s.269ST.")
    lcd = ev.get("lender_cash_deposit_before")
    if isinstance(lcd, dict):
        txt = f"Creditor's account shows a cash deposit of ₹{float(lcd['amount']):,.0f}"
        if lcd.get("date"):
            txt += f" on {lcd['date']}"
            if rec.get("txn_date"):
                try:
                    gap = (date.fromisoformat(rec["txn_date"]) - date.fromisoformat(lcd["date"])).days
                    txt += f" ({gap} day(s) before the transfer)"
                except ValueError:
                    pass
        txt += (" — source " + ("explained by creditor" if lcd.get("explained") else "NOT explained") +
                ". This is a source-of-funds risk for the creditworthiness/genuineness assessment; it does not by itself establish "
                "an addition in the assessee's hands — analyse facts and the applicable proviso (verify).")
        flags.append(txt)
    if rec["record_type"] == "CUSTOMER_ADVANCE" and ev.get("subsequent_invoice_or_refund") == "NOT_PROVIDED":
        flags.append("Advance not shown as adjusted or refunded — outstanding advances without confirmation attract closer scrutiny.")
    gaps = [lbl for k, (lbl, _) in cl.items() if ev.get(k, "NOT_PROVIDED") in ("NOT_PROVIDED", "REQUIRES_VERIFICATION")]
    return {"aspects": aspects, "flags": flags, "evidence_gaps": gaps,
            "note": ("Documents such as PAN, ITR, confirmation and banking-channel receipt support identity and capacity but are not "
                     "conclusive proof of genuineness. Assessment of the overall explanation is a matter for CA judgement.")}


def summary(user: dict, case_id: int) -> dict:
    recs = list_records(user, case_id)
    tot = {}
    for r in recs:
        t = tot.setdefault(r["record_type"], {"count": 0, "amount": 0.0, "with_gaps": 0})
        t["count"] += 1
        t["amount"] += r["amount"]
        t["with_gaps"] += bool(r["analysis"]["evidence_gaps"])
    return {"totals": tot, "records": recs}
