"""Phase 4 — extended reconciliations (additive to services.reconciliation).

* Generic transaction-level matcher (reference → exact date+amount → date window,
  optional party-name match) with matched / unmatched / duplicate lists and status.
* Bank book vs ledger, sales vs bank credits (built on the matcher).
* AIS / 26AS vs books (party-wise).
* Debtor balances vs customer receipts (roll-forward check per customer).

Status vocabulary: RECONCILED | RECONCILED_WITH_DIFFERENCES | UNRECONCILED.
A match on amount/date/party shows the records agree. It NEVER establishes the
genuineness, nature or source of a transaction (QC rule 4).
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from ..core.errors import ValidationError
from . import cases
from .notice_parser import parse_date
from .reconciliation import _rows_from_doc, _save, normalise, parse_amount

NOT_PROOF = ("Matching shows that two records agree on amount/date/reference. It does not prove the genuineness, "
             "nature or source of any transaction; supporting evidence is still required.")
_SUFFIX = re.compile(r"\b(m/s|messrs|mr|mrs|ms|shri|smt|pvt|private|ltd|limited|llp|co|company|and|&|the|india)\b")


def norm_party(s: str) -> str:
    s = re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())
    s = _SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _party_tokens(r: dict) -> set[str]:
    return {t for t in norm_party(r.get("party", "") + " " + r.get("narration", "")).split() if len(t) >= 3}


def _status(diff: float, n_unmatched: int) -> str:
    if abs(diff) < 0.5 and n_unmatched == 0:
        return "RECONCILED"
    if abs(diff) < 0.5:
        return "RECONCILED_WITH_DIFFERENCES"
    return "UNRECONCILED"


def match_transactions(a: list[dict], b: list[dict], *, side_a: str = "inflow", side_b: str = "inflow",
                       date_window_days: int = 0, amount_tolerance: float = 0.5, require_party: bool = False,
                       label_a: str = "A", label_b: str = "B") -> dict:
    if date_window_days < 0 or date_window_days > 90:
        raise ValidationError("date_window_days must be 0–90.")
    A = [dict(r, _i=i, _amt=r[side_a]) for i, r in enumerate(a) if r[side_a] > 0]
    B = [dict(r, _i=i, _amt=r[side_b]) for i, r in enumerate(b) if r[side_b] > 0]
    used: set[int] = set()
    matched = []

    def close(x, y):
        return abs(x["_amt"] - y["_amt"]) <= amount_tolerance

    def party_ok(x, y):
        return (not require_party) or bool(_party_tokens(x) & _party_tokens(y))

    passes = [("REFERENCE", lambda x, y: x["ref"] and y["ref"] and x["ref"] == y["ref"] and close(x, y)),
              ("DATE_AMOUNT", lambda x, y: x["date"] == y["date"] and close(x, y) and party_ok(x, y))]
    if date_window_days:
        passes.append(("DATE_WINDOW", lambda x, y: abs((date.fromisoformat(x["date"]) - date.fromisoformat(y["date"])).days)
                       <= date_window_days and close(x, y) and party_ok(x, y)))
    remaining = list(A)
    for name, pred in passes:
        nxt = []
        for x in remaining:
            y = next((y for y in B if y["_i"] not in used and pred(x, y)), None)
            if y is None:
                nxt.append(x)
                continue
            used.add(y["_i"])
            matched.append({"match_type": name, f"{label_a}_date": x["date"], f"{label_b}_date": y["date"],
                            "ref": x["ref"] or y["ref"], f"{label_a}_amount": x["_amt"], f"{label_b}_amount": y["_amt"],
                            f"{label_a}_narration": x["narration"][:80], f"{label_b}_narration": y["narration"][:80],
                            "difference": round(x["_amt"] - y["_amt"], 2),
                            "days_apart": abs((date.fromisoformat(x["date"]) - date.fromisoformat(y["date"])).days)})
        remaining = nxt
    un_b = [y for y in B if y["_i"] not in used]
    # possible duplicates: unmatched B identical to a matched B (same ref or same date+amount)
    matched_b_keys = {(m["ref"] or m[f"{label_b}_date"], m[f"{label_b}_amount"]) for m in matched}
    dups = [y for y in un_b if (y["ref"] or y["date"], y["_amt"]) in matched_b_keys]
    un_b = [y for y in un_b if y not in dups]
    slim = lambda r: {"date": r["date"], "ref": r["ref"], "narration": r["narration"][:100], "party": r.get("party", ""), "amount": r["_amt"]}
    ta, tb = round(sum(x["_amt"] for x in A), 2), round(sum(y["_amt"] for y in B), 2)
    dup_total = round(sum(y["_amt"] for y in dups), 2)
    diff = round(ta - (tb - dup_total), 2)
    return {
        f"total_{label_a}": ta, f"total_{label_b}": tb, f"possible_duplicates_in_{label_b}": [slim(y) for y in dups],
        "duplicate_total": dup_total, "difference_after_duplicates": diff,
        "matched_count": len(matched), "matched_total": round(sum(m[f"{label_a}_amount"] for m in matched), 2),
        "matched": matched, f"unmatched_in_{label_a}": [slim(x) for x in remaining], f"unmatched_in_{label_b}": [slim(y) for y in un_b],
        "status": _status(diff, len(remaining) + len(un_b)),
        "parameters": {"date_window_days": date_window_days, "amount_tolerance": amount_tolerance, "require_party": require_party},
        "interpretation": NOT_PROOF,
    }


def run_match(user: dict, case_id: int, *, doc_a: int, doc_b: int, perspective_a: str, perspective_b: str,
              side_a: str = "inflow", side_b: str = "inflow", label_a: str = "A", label_b: str = "B",
              filter_a: str | None = None, filter_b: str | None = None, date_window_days: int = 0,
              require_party: bool = False, recon_type: str = "TRANSACTION_MATCH", table_a: int = 0, table_b: int = 0) -> dict:
    cases.check_access(user, case_id)
    for s in (side_a, side_b):
        if s not in ("inflow", "outflow"):
            raise ValidationError("side must be inflow or outflow.")
    a, n1 = normalise(_rows_from_doc(user, doc_a, table_a), perspective_a)
    b, n2 = normalise(_rows_from_doc(user, doc_b, table_b), perspective_b)
    try:
        if filter_a:
            a = [r for r in a if re.search(filter_a, r["narration"] + " " + r["party"], re.I)]
        if filter_b:
            b = [r for r in b if re.search(filter_b, r["narration"] + " " + r["party"], re.I)]
    except re.error:
        raise ValidationError("Invalid filter expression.")
    la, lb = re.sub(r"\W+", "_", label_a.lower())[:30], re.sub(r"\W+", "_", label_b.lower())[:30]
    res = match_transactions(a, b, side_a=side_a, side_b=side_b, date_window_days=date_window_days,
                             require_party=require_party, label_a=la, label_b=lb)
    res["parse_notes"] = n1 + n2
    return _save(user, case_id, recon_type, {"doc_a": doc_a, "doc_b": doc_b, "filter_a": filter_a, "filter_b": filter_b,
                                             "window": date_window_days}, res)


def run_bank_book_vs_ledger(user, case_id, bank_book_doc, ledger_doc, ledger_side="outflow", date_window_days=0, filter_ledger=None):
    """Receipts in the bank book vs the corresponding ledger (e.g. debtor ledger credits)."""
    return run_match(user, case_id, doc_a=bank_book_doc, doc_b=ledger_doc, perspective_a="books", perspective_b="books",
                     side_a="inflow", side_b=ledger_side, label_a="bank_book", label_b="ledger", filter_b=filter_ledger,
                     date_window_days=date_window_days, recon_type="BANK_BOOK_VS_LEDGER")


def run_sales_vs_bank(user, case_id, sales_doc, statement_doc, date_window_days=7, filter_sales=None, require_party=False):
    """Sales recorded (credit side of sales ledger) vs non-cash bank credits."""
    res = run_match(user, case_id, doc_a=sales_doc, doc_b=statement_doc, perspective_a="books", perspective_b="bank_statement",
                    side_a="outflow", side_b="inflow", label_a="sales", label_b="bank", filter_a=filter_sales,
                    filter_b=r"^(?!.*\b(cash|by cash|self)\b)", date_window_days=date_window_days,
                    require_party=require_party, recon_type="SALES_VS_BANK")
    res["note"] = ("Unmatched sales may be cash/credit sales or collected later; unmatched bank credits may be loans, advances, "
                   "capital or collections of earlier sales — classify each before drawing any inference.")
    return res


# ---------------- AIS / 26AS vs books ----------------
_AIS_COLS = {
    "party": ["information source", "source", "deductor", "party", "name of deductor", "payer", "name", "reported by", "deductor name"],
    "amount": ["amount", "amount paid/credited", "amount paid credited", "reported value", "value", "total amount", "gross amount"],
    "description": ["information description", "description", "information category", "nature", "section", "category", "information code"],
    "tds": ["tds", "tax deducted", "tds deposited", "tax deducted at source"],
}


def _find_header(rows: list[list], spec: dict, required: tuple[str, ...]) -> tuple[int, dict]:
    for i, r in enumerate(rows[:15]):
        m = {}
        for j, cell in enumerate(r):
            c = re.sub(r"\s+", " ", re.sub(r"[^a-z/ ]", " ", str(cell).lower())).strip()
            for k, syns in spec.items():
                if k not in m.values() and (c in syns or any(c.startswith(s) for s in syns if len(s) > 4)):
                    m[j] = k
                    break
        if all(k in m.values() for k in required):
            return i, m
    raise ValidationError(f"Could not find header with columns {required}.")


def ais_vs_books_rows(ais_rows: list[list], books: list[dict], books_side: str = "outflow") -> dict:
    hi, m = _find_header(ais_rows, _AIS_COLS, ("party", "amount"))
    ais = defaultdict(lambda: {"amount": 0.0, "tds": 0.0, "names": set(), "descriptions": set()})
    for r in ais_rows[hi + 1:]:
        raw = {m[j]: (r[j] if j < len(r) else "") for j in m}
        amt = parse_amount(raw.get("amount"))
        if not amt or not str(raw.get("party", "")).strip():
            continue
        k = norm_party(str(raw["party"]))
        ais[k]["amount"] += amt
        ais[k]["tds"] += parse_amount(raw.get("tds"))
        ais[k]["names"].add(str(raw["party"]).strip())
        if raw.get("description"):
            ais[k]["descriptions"].add(str(raw["description"]).strip()[:60])
    bk = defaultdict(float)
    for r in books:
        name = r.get("party") or r.get("narration", "")
        bk[norm_party(name)] += r[books_side]
    rows = []
    used_books = set()
    for k, v in ais.items():
        bkey = k if k in bk else next((b for b in bk if b and (k in b or b in k)), None)
        books_amt = bk.get(bkey, 0.0) if bkey else 0.0
        if bkey:
            used_books.add(bkey)
        diff = round(v["amount"] - books_amt, 2)
        rows.append({"party": " / ".join(sorted(v["names"])), "ais_amount": round(v["amount"], 2), "books_amount": round(books_amt, 2),
                     "difference": diff, "tds_per_ais": round(v["tds"], 2), "descriptions": sorted(v["descriptions"]),
                     "status": "MATCHED" if abs(diff) < 0.5 else ("NOT_IN_BOOKS" if not bkey else "DIFFERENCE")})
    only_books = [{"party": k, "books_amount": round(a, 2)} for k, a in bk.items() if k not in used_books and a > 0]
    t_ais = round(sum(r["ais_amount"] for r in rows), 2)
    t_bk = round(sum(r["books_amount"] for r in rows), 2)
    return {"rows": rows, "in_books_not_in_ais": only_books, "total_ais": t_ais, "total_books_matched_parties": t_bk,
            "status": _status(t_ais - t_bk, sum(r["status"] != "MATCHED" for r in rows)),
            "interpretation": ("AIS/26AS reflects information reported by third parties and may contain errors or duplicates. A difference "
                               "is not by itself undisclosed income: check timing, GST component, reversals and AIS feedback before concluding."),
            "party_matching": "Names normalised (case/punctuation/'Pvt Ltd' etc. removed) — verify each pairing."}


def run_ais_vs_books(user, case_id, ais_doc, books_doc, books_perspective="books", books_side="outflow", ais_table=0, books_table=0):
    cases.check_access(user, case_id)
    ais_rows = _rows_from_doc(user, ais_doc, ais_table)
    books, notes = normalise(_rows_from_doc(user, books_doc, books_table), books_perspective)
    res = ais_vs_books_rows(ais_rows, books, books_side)
    res["parse_notes"] = notes
    return _save(user, case_id, "AIS_VS_BOOKS", {"ais_doc": ais_doc, "books_doc": books_doc}, res)


# ---------------- debtors vs receipts ----------------
_DEBTOR_COLS = {
    "party": ["customer", "party", "debtor", "name", "ledger", "party name", "customer name"],
    "opening": ["opening", "opening balance", "op balance", "b/f", "balance b/f"],
    "debit": ["sales", "debit", "dr", "invoiced", "billed"],
    "credit": ["receipts", "credit", "cr", "collections", "received"],
    "closing": ["closing", "closing balance", "cl balance", "balance c/f", "c/f"],
}


def debtors_vs_receipts_rows(debtor_rows: list[list], receipts: list[dict] | None) -> dict:
    hi, m = _find_header(debtor_rows, _DEBTOR_COLS, ("party",))
    rec_by = defaultdict(float)
    for r in receipts or []:
        rec_by[norm_party(r.get("party") or r.get("narration", ""))] += r["inflow"]
    out = []
    for r in debtor_rows[hi + 1:]:
        raw = {m[j]: (r[j] if j < len(r) else "") for j in m}
        name = str(raw.get("party", "")).strip()
        if not name or name.lower().startswith("total"):
            continue
        op, dr, cr = parse_amount(raw.get("opening")), parse_amount(raw.get("debit")), parse_amount(raw.get("credit"))
        cl_stated = parse_amount(raw.get("closing")) if "closing" in raw else None
        cl_calc = round(op + dr - cr, 2)
        flags = []
        if cl_stated is not None and abs(cl_calc - cl_stated) >= 0.5:
            flags.append(f"Roll-forward mismatch: opening+sales−receipts = {cl_calc:,.0f} vs stated closing {cl_stated:,.0f}.")
        if cr > op + dr + 0.5:
            flags.append("Receipts exceed opening balance plus sales — excess collection needs explanation.")
        if op > 0 and dr == 0 and cr >= op:
            flags.append("Collection relates wholly to the opening balance — verify prior-year ledger, invoices and confirmation.")
        k = norm_party(name)
        rk = k if k in rec_by else next((x for x in rec_by if x and (k in x or x in k)), None)
        per_receipts = rec_by.get(rk) if rk else None
        if receipts is not None:
            if per_receipts is None:
                flags.append("No matching receipt found in the receipts record supplied.")
            elif abs(per_receipts - cr) >= 0.5:
                flags.append(f"Ledger receipts {cr:,.0f} differ from receipts record {per_receipts:,.0f}.")
        out.append({"customer": name, "opening": op, "sales": dr, "receipts_per_ledger": cr, "closing_calculated": cl_calc,
                    "closing_stated": cl_stated, "receipts_per_cash_bank": round(per_receipts, 2) if per_receipts is not None else None,
                    "flags": flags, "status": "CONSISTENT" if not flags else "REVIEW"})
    return {"customers": out, "n_review": sum(x["status"] == "REVIEW" for x in out),
            "status": "RECONCILED" if out and all(x["status"] == "CONSISTENT" for x in out) else "UNRECONCILED",
            "interpretation": ("A consistent roll-forward shows the ledger is arithmetically consistent. It does not establish that the "
                               "opening balance or collection is genuine — verify prior-year records and customer confirmations.")}


def run_debtors_vs_receipts(user, case_id, debtor_doc, receipts_doc=None, receipts_perspective="books", debtor_table=0):
    cases.check_access(user, case_id)
    rows = _rows_from_doc(user, debtor_doc, debtor_table)
    receipts, notes = (normalise(_rows_from_doc(user, receipts_doc), receipts_perspective) if receipts_doc else (None, []))
    res = debtors_vs_receipts_rows(rows, receipts)
    res["parse_notes"] = notes
    return _save(user, case_id, "DEBTORS_VS_RECEIPTS", {"debtor_doc": debtor_doc, "receipts_doc": receipts_doc}, res)
