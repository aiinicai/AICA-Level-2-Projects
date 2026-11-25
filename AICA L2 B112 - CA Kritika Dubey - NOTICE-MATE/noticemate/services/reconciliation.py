"""Module 7 — bank statement, bank book, cash book, ledger and financial-statement
analysis. Deterministic, local, with full workings.

Conventions
* Every row is normalised to {date, narration, ref, inflow, outflow, party}.
* perspective="bank_statement": Credit/Deposit = inflow, Debit/Withdrawal = outflow.
  perspective="books" (bank book / cash book from the assessee's ledger): Dr = inflow, Cr = outflow.
  Columns named Receipt(s)/Payment(s) are unambiguous in either perspective.
* Results distinguish: RECORDED (in books), SUPPORTED (by a document) and
  ESTABLISHED (source & genuineness) — reconciliation only ever proves the first
  two at best; it never establishes genuineness (QC rule 4).
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date

from ..core import audit
from ..core.db import dumps, ro, row_to_dict, tx, utcnow
from ..core.errors import ValidationError
from . import cases, documents
from .notice_parser import parse_date

S269ST_LIMIT = 200000
S269SS_LIMIT = 20000

_COLS = {
    "date": ["date", "txn date", "transaction date", "value date", "tran date", "voucher date"],
    "narration": ["narration", "particulars", "description", "details", "remarks", "nature"],
    "ref": ["ref", "reference", "ref no", "chq", "cheque", "utr", "instrument", "voucher no", "txn id"],
    "party": ["party", "customer", "name", "ledger", "partner", "lender", "source"],
    "receipt": ["receipt", "receipts", "received", "deposit", "deposits", "cash in"],
    "payment": ["payment", "payments", "paid", "withdrawal", "withdrawals", "cash out"],
    "debit": ["debit", "dr", "debit amount", "dr amount"],
    "credit": ["credit", "cr", "credit amount", "cr amount"],
    "amount": ["amount", "amt", "value"],
    "balance": ["balance", "closing balance", "running balance"],
}


def parse_amount(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("₹", "").replace("Rs.", "").replace("Rs", "").replace("INR", "").replace(",", "").strip()
    if s in ("", "-", "--", "nil", "Nil", "NIL"):
        return 0.0
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    s = re.sub(r"\s*(dr|cr)\.?$", "", s, flags=re.I)
    try:
        val = float(s)
    except ValueError:
        return 0.0
    return -val if neg else val


def _match_col(cell: str) -> str | None:
    c = re.sub(r"[^a-z ]", " ", str(cell).lower()).strip()
    c = re.sub(r"\s+", " ", c)
    if not c:
        return None
    for key, syns in _COLS.items():
        if c in syns:
            return key
    for key, syns in _COLS.items():
        if any(c.startswith(s + " ") or c.endswith(" " + s) for s in syns if len(s) > 2):
            return key
    return None


def normalise(rows: list[list], perspective: str) -> tuple[list[dict], list[str]]:
    if perspective not in ("bank_statement", "books"):
        raise ValidationError("perspective must be bank_statement or books.")
    notes: list[str] = []
    header_idx, mapping = None, {}
    for i, r in enumerate(rows[:15]):
        m = {}
        for j, cell in enumerate(r):
            k = _match_col(cell)
            if k and k not in m.values():
                m[j] = k
        if "date" in m.values() and len(m) >= 2:
            header_idx, mapping = i, m
            break
    if header_idx is None:
        raise ValidationError("Could not identify a header row with a Date column and amount columns.")
    out = []
    for r in rows[header_idx + 1:]:
        rec = {"date": None, "narration": "", "ref": "", "party": "", "inflow": 0.0, "outflow": 0.0}
        raw = {mapping[j]: (r[j] if j < len(r) else "") for j in mapping}
        d = parse_date(str(raw.get("date", "")))
        if not d:
            label = " ".join(str(x) for x in r).lower()
            if any(w in label for w in ("total", "opening", "closing", "balance b/f", "balance c/f")):
                continue
            if any(str(x).strip() for x in r):
                notes.append(f"Row skipped (no valid date): {' | '.join(str(x) for x in r)[:80]}")
            continue
        rec["date"] = d.isoformat()
        rec["narration"] = str(raw.get("narration", "")).strip()
        rec["ref"] = str(raw.get("ref", "")).strip()
        rec["party"] = str(raw.get("party", "")).strip()
        inflow = parse_amount(raw.get("receipt")) if "receipt" in raw else 0.0
        outflow = parse_amount(raw.get("payment")) if "payment" in raw else 0.0
        dr, cr = parse_amount(raw.get("debit")), parse_amount(raw.get("credit"))
        if perspective == "bank_statement":
            inflow += cr
            outflow += dr
        else:
            inflow += dr
            outflow += cr
        if "amount" in raw and not (inflow or outflow):
            a = parse_amount(raw["amount"])
            if a >= 0:
                inflow = a
            else:
                outflow = -a
            msg = "Single 'Amount' column — sign used to infer direction; verify."
            if msg not in notes:
                notes.append(msg)
        rec["inflow"], rec["outflow"] = round(inflow, 2), round(outflow, 2)
        out.append(rec)
    return out, notes


def _rows_from_doc(user: dict, document_id: int, table_index: int = 0) -> list[list]:
    t = documents.get_text(user, document_id)
    if not t["tables"]:
        raise ValidationError(f"Document {document_id} has no extracted tables.")
    if table_index >= len(t["tables"]):
        raise ValidationError(f"Document {document_id} has only {len(t['tables'])} table(s).")
    return t["tables"][table_index]["rows"]


_CASH_WORDS = re.compile(r"(?i)\b(cash|by cash|cash dep|csh dep|self)\b")


def classify_credit(narr: str) -> str:
    n = narr.lower()
    if _CASH_WORDS.search(n):
        return "CASH_DEPOSIT"
    for k, v in (("upi", "UPI"), ("neft", "NEFT"), ("rtgs", "RTGS"), ("imps", "IMPS"), ("clg", "CHEQUE"), ("chq", "CHEQUE"),
                 ("int", "INTEREST")):
        if k in n:
            return v
    return "OTHER"


# ---------------- analyses ----------------

def bank_vs_book(statement: list[dict], book: list[dict]) -> dict:
    """Match bank-statement credits to bank-book receipts by reference, then by (date, amount)."""
    st = [dict(r, idx=i) for i, r in enumerate(statement) if r["inflow"] > 0]
    bk = [dict(r, idx=i) for i, r in enumerate(book) if r["inflow"] > 0]
    used_bk: set[int] = set()
    matched, unmatched_st = [], []
    for s in st:
        cand = None
        if s["ref"]:
            cand = next((b for b in bk if b["idx"] not in used_bk and b["ref"] and b["ref"] == s["ref"] and abs(b["inflow"] - s["inflow"]) < 0.5), None)
        if cand is None:
            cand = next((b for b in bk if b["idx"] not in used_bk and b["date"] == s["date"] and abs(b["inflow"] - s["inflow"]) < 0.5), None)
        if cand:
            used_bk.add(cand["idx"])
            matched.append({"date": s["date"], "ref": s["ref"], "amount": s["inflow"], "matched_on": "ref" if s["ref"] and cand["ref"] == s["ref"] else "date+amount"})
        else:
            unmatched_st.append(s)
    unmatched_bk = [b for b in bk if b["idx"] not in used_bk]
    # duplicate detection: an unmatched book entry identical (ref/date+amount) to a matched one
    matched_keys = Counter((m["ref"] or m["date"], m["amount"]) for m in matched)
    duplicates, other_unmatched_bk = [], []
    for b in unmatched_bk:
        key = (b["ref"] or b["date"], b["inflow"])
        if matched_keys.get(key):
            duplicates.append(b)
        else:
            other_unmatched_bk.append(b)
    tot_st = round(sum(s["inflow"] for s in st), 2)
    tot_bk = round(sum(b["inflow"] for b in bk), 2)
    dup_total = round(sum(d["inflow"] for d in duplicates), 2)
    return {
        "statement_credits_total": tot_st, "book_receipts_total": tot_bk,
        "difference_book_minus_statement": round(tot_bk - tot_st, 2),
        "probable_duplicate_book_postings": [{k: d[k] for k in ("date", "ref", "narration", "inflow")} for d in duplicates],
        "duplicate_total": dup_total, "corrected_book_total": round(tot_bk - dup_total, 2),
        "matched": matched,
        "in_statement_not_in_book": [{k: s[k] for k in ("date", "ref", "narration", "inflow")} for s in unmatched_st],
        "in_book_not_in_statement": [{k: b[k] for k in ("date", "ref", "narration", "inflow")} for b in other_unmatched_bk],
        "interpretation": ("A probable duplicate is a book-recording error, not an additional bank credit; it must not be treated as "
                           "another unexplained receipt. Unmatched items require transaction-level review."),
    }


def credit_classification(statement: list[dict]) -> dict:
    groups: dict[str, list] = defaultdict(list)
    for r in statement:
        if r["inflow"] > 0:
            groups[classify_credit(r["narration"])].append(r)
    return {"by_mode": {k: {"count": len(v), "total": round(sum(x["inflow"] for x in v), 2)} for k, v in groups.items()},
            "cash_deposits": [{"date": r["date"], "amount": r["inflow"], "narration": r["narration"]} for r in groups.get("CASH_DEPOSIT", [])],
            "total_credits": round(sum(r["inflow"] for r in statement if r["inflow"] > 0), 2),
            "note": "Mode is inferred from narration keywords and REQUIRES VERIFICATION. Mode is not nature: a NEFT credit may be a sale, loan or advance."}


def cash_chronology(cash_book: list[dict], deposits: list[dict], source_mapping: list[dict] | None = None,
                    opening_balance: float = 0.0) -> dict:
    """Test (1) cash-book balance before each deposit ≥ deposit, (2) each mapped
    source receipt is dated on/before its deposit, (3) mapped sources sum to deposit.
    deposits: [{date, amount}] ; source_mapping: [{deposit_date, receipt_date, amount, description}]"""
    events = sorted(cash_book, key=lambda r: (r["date"], -r["inflow"]))
    results = []
    for dep in sorted(deposits, key=lambda d: d["date"]):
        bal = opening_balance + sum(r["inflow"] - r["outflow"] for r in events if r["date"] < dep["date"])
        # same-day receipts count, same-day outflows other than the deposit itself are excluded conservatively
        same_day_in = sum(r["inflow"] for r in events if r["date"] == dep["date"])
        available = round(bal + same_day_in, 2)
        res = {"deposit_date": dep["date"], "deposit_amount": dep["amount"], "cash_available_per_cash_book": available,
               "balance_test": "PASS" if available + 0.5 >= dep["amount"] else "FAIL"}
        if source_mapping is not None:
            srcs = [s for s in source_mapping if s["deposit_date"] == dep["date"]]
            late = [s for s in srcs if s["receipt_date"] > dep["date"]]
            tot = round(sum(float(s["amount"]) for s in srcs), 2)
            res.update({"mapped_sources_total": tot, "mapping_sum_test": "PASS" if abs(tot - dep["amount"]) < 0.5 else "FAIL",
                        "chronology_test": "PASS" if not late else "FAIL",
                        "sources_after_deposit": late, "sources": srcs})
        results.append(res)
    fails = [r for r in results if "FAIL" in (r.get("balance_test"), r.get("mapping_sum_test"), r.get("chronology_test"))]
    return {"deposits_tested": len(results), "failures": len(fails), "results": results,
            "opening_balance_used": opening_balance,
            "interpretation": ("PASS means the books are internally consistent for that deposit. It does NOT prove that the underlying "
                               "receipts occurred or that the cash deposited came from them; supporting documents remain necessary.")}


def ledger_compare(a: list[dict], b: list[dict], label_a: str, label_b: str, side: str = "inflow") -> dict:
    """Compare two records date-wise (e.g. cash book cash sales vs sales ledger)."""
    da, db = defaultdict(float), defaultdict(float)
    for r in a:
        da[r["date"]] += r[side]
    for r in b:
        db[r["date"]] += r[side]
    diffs = []
    for d in sorted(set(da) | set(db)):
        if abs(da[d] - db[d]) >= 0.5:
            diffs.append({"date": d, label_a: round(da[d], 2), label_b: round(db[d], 2), "difference": round(da[d] - db[d], 2)})
    ta, tb = round(sum(da.values()), 2), round(sum(db.values()), 2)
    return {"total_" + label_a: ta, "total_" + label_b: tb, "difference": round(ta - tb, 2), "date_wise_differences": diffs,
            "interpretation": "Differences require explanation and evidence (e.g., invoices). A management explanation such as 'posting error' is not established without support."}


def cash_mode_flags(cash_book: list[dict]) -> dict:
    flags = []
    for r in cash_book:
        n = (r["narration"] + " " + r["party"]).lower()
        if r["inflow"] >= S269ST_LIMIT and not re.search(r"(?i)bank|withdraw", n):
            flags.append({"date": r["date"], "amount": r["inflow"], "narration": r["narration"],
                          "flag": "Single cash receipt ≥ ₹2,00,000 — examine s.269ST / s.271DA exposure (per person/day/transaction/event)."})
        if r["inflow"] >= S269SS_LIMIT and re.search(r"(?i)loan|deposit from|capital|advance", n):
            flags.append({"date": r["date"], "amount": r["inflow"], "narration": r["narration"],
                          "flag": "Cash loan/deposit/capital/advance ≥ ₹20,000 — examine s.269SS / s.269ST applicability (CA judgement)."})
    return {"flags": flags, "note": "Flags are prompts for CA review, not findings of contravention."}


def fs_tie_out(figures: list[dict]) -> dict:
    """figures: [{label, per_financial_statements, per_books, per_return(optional)}]"""
    rows = []
    for f in figures:
        fs = parse_amount(f.get("per_financial_statements"))
        bk = parse_amount(f.get("per_books"))
        rt = f.get("per_return")
        rtv = parse_amount(rt) if rt not in (None, "") else None
        rows.append({"label": f["label"], "fs": fs, "books": bk, "return": rtv, "fs_minus_books": round(fs - bk, 2),
                     "fs_minus_return": round(fs - rtv, 2) if rtv is not None else "NOT PROVIDED",
                     "status": "RECONCILED" if abs(fs - bk) < 0.5 and (rtv is None or abs(fs - rtv) < 0.5) else "DIFFERENCE"})
    return {"rows": rows, "note": "Figures as entered/extracted; verify against signed financial statements and filed return."}


# ---------------- orchestrators (persist + audit) ----------------

def _save(user: dict, case_id: int, rtype: str, inputs: dict, result: dict) -> dict:
    with tx() as conn:
        cur = conn.execute("INSERT INTO recon_runs(case_id,recon_type,inputs_json,result_json,created_by,created_at) VALUES (?,?,?,?,?,?)",
                           (case_id, rtype, dumps(inputs), dumps(result), user["id"], utcnow()))
        result["run_id"] = cur.lastrowid
        audit.log_event(conn, "RECONCILIATION_RUN", user_id=user["id"], case_id=case_id, meta={"type": rtype, "run_id": cur.lastrowid})
    return result


def run_bank_vs_book(user: dict, case_id: int, statement_doc: int, book_doc: int) -> dict:
    cases.check_access(user, case_id)
    st, n1 = normalise(_rows_from_doc(user, statement_doc), "bank_statement")
    bk, n2 = normalise(_rows_from_doc(user, book_doc), "books")
    res = bank_vs_book(st, bk)
    res["credit_classification"] = credit_classification(st)
    res["parse_notes"] = n1 + n2
    return _save(user, case_id, "BANK_VS_BOOK", {"statement_doc": statement_doc, "book_doc": book_doc}, res)


def run_cash_chronology(user: dict, case_id: int, cash_book_doc: int, statement_doc: int, opening_balance: float = 0.0,
                        source_mapping: list[dict] | None = None) -> dict:
    cases.check_access(user, case_id)
    cb, n1 = normalise(_rows_from_doc(user, cash_book_doc), "books")
    st, n2 = normalise(_rows_from_doc(user, statement_doc), "bank_statement")
    deposits = [{"date": r["date"], "amount": r["inflow"]} for r in st if r["inflow"] > 0 and classify_credit(r["narration"]) == "CASH_DEPOSIT"]
    if source_mapping:
        for s in source_mapping:
            for k in ("deposit_date", "receipt_date"):
                d = parse_date(str(s.get(k, ""))) or (date.fromisoformat(s[k]) if re.match(r"^\d{4}-\d{2}-\d{2}$", str(s.get(k, ""))) else None)
                if not d:
                    raise ValidationError(f"Invalid {k} in source mapping: {s.get(k)}")
                s[k] = d.isoformat()
    # exclude the cash book's own "cash deposited into bank" outflows from same-day availability is handled in cash_chronology
    res = cash_chronology(cb, deposits, source_mapping, opening_balance)
    res["cash_mode_flags"] = cash_mode_flags(cb)
    res["parse_notes"] = n1 + n2
    return _save(user, case_id, "CASH_CHRONOLOGY", {"cash_book_doc": cash_book_doc, "statement_doc": statement_doc,
                                                    "opening_balance": opening_balance, "mapping_rows": len(source_mapping or [])}, res)


def run_ledger_compare(user: dict, case_id: int, doc_a: int, doc_b: int, label_a: str, label_b: str,
                       filter_a: str | None = None, filter_b: str | None = None, table_a: int = 0, table_b: int = 0) -> dict:
    cases.check_access(user, case_id)
    a, n1 = normalise(_rows_from_doc(user, doc_a, table_a), "books")
    b, n2 = normalise(_rows_from_doc(user, doc_b, table_b), "books")
    if filter_a:
        a = [r for r in a if re.search(filter_a, r["narration"] + " " + r["party"], re.I)]
    if filter_b:
        b = [r for r in b if re.search(filter_b, r["narration"] + " " + r["party"], re.I)]
    # sales ledger records sales as Cr (income); use whichever side carries values
    side_b = "inflow" if sum(r["inflow"] for r in b) else "outflow"
    if side_b == "outflow":
        b = [dict(r, inflow=r["outflow"]) for r in b]
    res = ledger_compare(a, b, re.sub(r"\W+", "_", label_a.lower()), re.sub(r"\W+", "_", label_b.lower()))
    res["parse_notes"] = n1 + n2
    return _save(user, case_id, "LEDGER_COMPARE", {"doc_a": doc_a, "doc_b": doc_b, "filter_a": filter_a, "filter_b": filter_b}, res)


def run_fs_tie_out(user: dict, case_id: int, figures: list[dict]) -> dict:
    cases.check_access(user, case_id)
    if not figures:
        raise ValidationError("Provide at least one figure.")
    return _save(user, case_id, "FS_TIE_OUT", {"n": len(figures)}, fs_tie_out(figures))


def list_runs(user: dict, case_id: int) -> list[dict]:
    cases.check_access(user, case_id)
    with ro() as conn:
        rows = conn.execute("SELECT * FROM recon_runs WHERE case_id=? ORDER BY id DESC", (case_id,)).fetchall()
    return [row_to_dict(r, ("inputs_json", "result_json")) for r in rows]
