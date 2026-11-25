"""V3.1 — read uploaded documents and map their contents to the notice's issues.

How it works (deterministic, runs on this computer, no AI needed):
* Every document is split into passages: paragraphs, and table rows rendered with their
  column headings ("Date: 15-May-2024; Narration: NEFT Rohan Iyer; Credit ₹: 350,000.00").
  Rows of two-column "particulars | details" tables inherit the table's party name.
* Each issue's own wording supplies anchors: party names, amounts, dates and references
  (invoice / UTR numbers), plus the issue's subject words.
* A passage is linked to an issue only when it shares concrete anchors with it. Each link
  carries a short reason ("Rohan Iyer; ₹3,50,000; 15-May-2024") and a certainty:
  STRONG (a party/reference plus an amount or date, or several amounts) or UNCERTAIN.
* A file type or a successful upload is never treated as support for anything.
* Records about the same item (same party/reference and amount) in different documents are
  compared; differing dates are raised as review points, never silently resolved.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date

from ..core import audit
from ..core.db import ro, row_to_dict, tx, utcnow
from ..core.errors import NotFound, ValidationError
from . import cases

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_MON = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_DATE_RXS = [
    re.compile(r"(?i)\b(\d{1,2})[\s\-/.]" + _MON + r"[\s\-/.,]*(\d{4})\b"),          # 15 May 2024 / 15-May-2024
    re.compile(r"(?i)\b" + _MON + r"\s+(\d{1,2}),?\s+(\d{4})\b"),                   # May 15, 2024
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),                                      # 2024-05-15
    re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b"),                            # 15/05/2024
    re.compile(r"(?i)\b(\d{1,2})[\s\-]" + _MON + r"\b(?![\s\-/.,]*\d{4})"),          # 10-Dec (no year)
]
# Amounts: ₹ / Rs prefixed, or comma-grouped (Indian 12,00,000 or western 1,200,000.00), or plain ≥ 5 digits.
_AMT_RX = re.compile(r"(?<![\w/\-])(?:₹\s?|rs\.?\s?|inr\s?)?\(?((?:\d{1,3}(?:,\d{2,3})+|\d{5,})(?:\.\d{1,2})?)\)?(?![\w\-/])", re.I)
_REF_RX = re.compile(r"\b(?=[A-Z0-9/\-]*\d)(?=[A-Z0-9/\-]*[A-Z])[A-Z0-9]{2,}(?:[/\-][A-Z0-9]{1,})+\b|\b(?=\w*\d)(?=\w*[A-Z])[A-Z]{2,}\d{5,}\b")
_NAME_RX = re.compile(r"\b([A-Z][a-z]+(?:\s+(?:&\s+)?[A-Z][a-z]+){1,3})\b")
_NAME_STOP = {
    "the", "income", "tax", "department", "assessment", "previous", "year", "notice", "section", "act", "furnish", "please",
    "national", "faceless", "centre", "unit", "new", "delhi", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december", "january", "february", "explain", "provide", "submit", "trade", "creditors", "selected",
    "purchases", "fixed", "assets", "cash", "deposits", "unsecured", "loans", "reconciliation", "bank", "sales", "books",
    "return", "filed", "goods", "information", "required", "submission", "instructions", "test", "fictional", "sample",
}
_STOPWORDS = set("""the and for with from that this which have been were are was into each their there these those other
such shall under above below during year previous amount amounts aggregating furnish please explain provide details record
records together corresponding relevant including include shown reflect reflects books including whether identify any
received receipt balance payment payments entries entry account accounts ledger bank confirmation confirmations stating
statement statements explanation parties party relied assessee supporting evidence copies documents copy dated total
amount through about where after before against subsequent outstanding identity address terms relevant both
source sources receipts funds fictional test sample january february march april june july august september october
november december immediately complete underlying""".split())


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def inr(n: float | int | None) -> str:
    """Indian digit grouping: 1240000 -> ₹12,40,000."""
    if n is None:
        return ""
    neg = n < 0
    n = abs(n)
    whole = int(round(n))
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        s = f"{head},{tail}"
    return ("-" if neg else "") + "₹" + s


def amounts_in(text: str) -> set[int]:
    out = set()
    for m in _AMT_RX.finditer(text or ""):
        raw = m.group(1).replace(",", "")
        try:
            v = float(raw)
        except ValueError:
            continue
        if v >= 1000 and not (1900 <= v <= 2100 and "," not in m.group(1)):
            out.add(int(round(v)))
    return out


def dates_in(text: str, fy_start: int | None = None) -> set[date]:
    out: set[date] = set()
    t = text or ""
    for i, rx in enumerate(_DATE_RXS):
        for m in rx.finditer(t):
            try:
                if i == 0:
                    d = date(int(m.group(3)), MONTHS[m.group(2)[:3].lower()], int(m.group(1)))
                elif i == 1:
                    d = date(int(m.group(3)), MONTHS[m.group(1)[:3].lower()], int(m.group(2)))
                elif i == 2:
                    d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                elif i == 3:
                    d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                else:
                    if not fy_start:
                        continue
                    mon = MONTHS[m.group(2)[:3].lower()]
                    d = date(fy_start if mon >= 4 else fy_start + 1, mon, int(m.group(1)))
            except (ValueError, KeyError):
                continue
            out.add(d)
    return out


def refs_in(text: str) -> set[str]:
    out = set()
    for m in _REF_RX.finditer(text or ""):
        tok = re.sub(r"[^A-Z0-9]", "", m.group(0).upper())
        if len(tok) >= 6 and re.search(r"\d", tok) and re.search(r"[A-Z]", tok):
            out.add(tok)
    return out


def names_in(text: str) -> set[str]:
    out = set()
    for m in _NAME_RX.finditer(text or ""):
        words = m.group(1).split()
        while words and words[0].lower() in _NAME_STOP:
            words = words[1:]
        while words and words[-1].lower() in _NAME_STOP:
            words = words[:-1]
        if len(words) >= 2 and not any(w.lower() in {"income", "tax", "assessment"} for w in words):
            out.add(" ".join(words))
    return out


def fmt_date(d: date) -> str:
    return d.strftime("%d-%b-%Y")


def _long(d: date) -> str:
    return f"{d.day} {d.strftime('%B %Y')}"


def _fy_start(assessment_year: str | None) -> int | None:
    m = re.match(r"^(\d{4})", assessment_year or "")
    return int(m.group(1)) - 1 if m else None


# ------------------------------------------------------------------ passages
@dataclass
class Passage:
    document_id: int
    kind: str  # PARAGRAPH | ROW | RECORD
    text: str
    keys: set[str] = field(default_factory=set)  # party names / references inherited from a record table
    table: int | None = None  # which table of the document the row came from
    table_rows: int = 0
    location: str = ""  # page / sheet / table row, when known


def _is_header(row: list[str]) -> bool:
    filled = [c for c in row if c.strip()]
    return bool(filled) and not any(amounts_in(c) or dates_in(c) for c in filled)


def _table_place(name: str, tno: int) -> str:
    m = re.match(r"page(\d+)_table(\d+)$", name or "")
    if m:
        return f"page {m.group(1)}, table {m.group(2)}"
    if re.match(r"table\d+$", name or ""):
        return f"table {tno + 1}"
    if name == "csv":
        return "CSV"
    return f"sheet '{name}'" if name else f"table {tno + 1}"


def passages_for(document_id: int, text: str, tables: list[dict]) -> list[Passage]:
    out: list[Passage] = []
    table_lines = set()
    for tno, t in enumerate(tables or []):
        place = _table_place(t.get("name") or "", tno)
        rows = [[_norm(c) for c in r] for r in t.get("rows") or [] if any(_norm(c) for c in r)]
        if not rows:
            continue
        for r in rows:
            table_lines.add(_norm(" | ".join(r)))
        header = rows[0] if _is_header(rows[0]) and len(rows) > 1 else None
        body = rows[1:] if header else rows
        two_col = all(len([c for c in r if c]) <= 2 for r in rows) and len(rows[0]) == 2
        if two_col:  # a particulars/details table describes ONE record: keep it whole, and each row with its party
            whole = "; ".join(f"{r[0]}: {r[1]}" if len(r) > 1 else r[0] for r in body)
            keys = names_in(whole) | refs_in(whole)
            out.append(Passage(document_id, "RECORD", whole, keys, tno, len(body), place))
            for rn, r in enumerate(body, 1):
                line = f"{r[0]}: {r[1]}" if len(r) > 1 else r[0]
                out.append(Passage(document_id, "ROW", line, set(keys), tno, len(body), f"{place}, row {rn}"))
            continue
        for rn, r in enumerate(body, 1):
            if header and len(header) == len(r):
                cells = [f"{h}: {v}" for h, v in zip(header, r) if v and v not in ("—", "-")]
            else:
                cells = [v for v in r if v]
            line = "; ".join(cells)
            if line:
                out.append(Passage(document_id, "ROW", line, set(), tno, len(body), f"{place}, row {rn}"))
    pages = (text or "").count("\f") > 0
    page = 1
    for raw in (text or "").replace("\r\n", "\n").split("\n"):
        page += raw.count("\f")
        raw = raw.replace("\f", "")
        line = _norm(raw)
        if len(line) < 25 or line in table_lines or " | " in line and _norm(line) in table_lines:
            continue
        if line.count(" | ") >= 2:  # a table line already covered above
            continue
        out.append(Passage(document_id, "PARAGRAPH", line, location=f"page {page}" if pages else "text"))
    return out


# ------------------------------------------------------------------ anchors
def issue_anchors(issue: dict, fy_start: int | None) -> dict:
    t = f"{issue.get('title') or ''}. {issue['query_text']}"
    words = {w for w in re.findall(r"[a-z][a-z\-]{4,}", t.lower()) if w not in _STOPWORDS}
    return {"amounts": amounts_in(t), "dates": dates_in(t, fy_start), "names": names_in(t), "refs": refs_in(t),
            "words": words}


def score_passage(p: Passage, a: dict, fy_start: int | None) -> tuple[float, list[str], str] | None:
    low = p.text.lower()
    names = sorted(n for n in a["names"] if n.lower() in low or n in p.keys)
    refs = sorted(r for r in a["refs"] if r in refs_in(p.text.upper()) or r in p.keys)
    amts = sorted(a["amounts"] & amounts_in(p.text))
    dts = sorted(a["dates"] & dates_in(p.text, fy_start))
    kws = sorted(w for w in a["words"] if w in low)
    if not (names or refs) and not kws:
        return None  # an amount or date on its own is coincidence, not support: it must also share the issue's subject
    score = 4 * len(names) + 4 * len(refs) + 3 * len(amts) + 2 * len(dts) + min(2.0, 0.5 * len(kws))
    if score < 3:
        return None
    own_txn = (names or refs) and p.kind == "ROW" and amounts_in(p.text) and dates_in(p.text, fy_start)  # a dated money entry of the party
    strong = (((names or refs) and (amts or dts)) or len(amts) >= 2 or (amts and dts)
              or (amts and len(kws) >= 2) or own_txn or score >= 9)
    reason = "; ".join([*names, *[f"ref {r}" for r in refs], *[inr(x) for x in amts], *[fmt_date(d) for d in dts]]
                       or [f"subject words: {', '.join(kws[:4])}"])
    return score, [reason], "STRONG" if strong else "UNCERTAIN"


# ------------------------------------------------------------------ main entry
def _case_docs(conn, case_id: int) -> list[dict]:
    return [row_to_dict(r) for r in conn.execute(
        "SELECT d.id, d.original_name, d.doc_type, d.is_annexure, d.annexure_label, t.text, t.tables_json "
        "FROM documents d LEFT JOIN doc_text t ON t.document_id=d.id WHERE d.case_id=? ORDER BY d.id", (case_id,))]


def _notice_doc_ids(conn, case_id: int) -> set[int]:
    return {r["document_id"] for r in conn.execute("SELECT document_id FROM notices WHERE case_id=? AND document_id IS NOT NULL",
                                                   (case_id,))}


def map_case(user: dict, case_id: int, *, max_per_doc: int = 14) -> dict:
    """(Re)build automatic links for every issue. Links the user accepted or rejected are kept."""
    case = cases.get_case(user, case_id)
    fy = _fy_start(case.get("assessment_year"))
    with ro() as conn:
        iss = [row_to_dict(r) for r in conn.execute("SELECT * FROM issues WHERE case_id=? ORDER BY seq", (case_id,))]
        docs = _case_docs(conn, case_id)
        skip = _notice_doc_ids(conn, case_id)
        kept = {(r["issue_id"], r["document_id"], r["passage"]): r["status"] for r in conn.execute(
            "SELECT issue_id, document_id, passage, status FROM doc_links WHERE case_id=? AND status<>'AUTO'", (case_id,))}
    rows = []
    for d in docs:
        if d["id"] in skip or not (d.get("text") or "").strip():
            continue
        ps = passages_for(d["id"], d["text"], json.loads(d.get("tables_json") or "[]"))
        for i in iss:
            a = issue_anchors(i, fy)
            hits = []
            for p in ps:
                r = score_passage(p, a, fy)
                if r:
                    hits.append((r[0], p, r[1][0], r[2]))
            strong_tables = {}
            for sc, p, reason, cert in hits:
                if cert == "STRONG" and p.table is not None and p.kind == "ROW":
                    strong_tables[p.table] = strong_tables.get(p.table, 0) + 1
            hit_texts = {h[1].text for h in hits}
            for p in ps:
                if p.text in hit_texts or p.kind != "ROW":
                    continue
                if p.table is not None and strong_tables.get(p.table, 0) >= 2 and p.table_rows <= 8:
                    hits.append((2.5, p, "same table as the matched rows", "STRONG"))  # complete a small reconciliation table
                elif hits and any(h[3] == "STRONG" for h in hits):
                    kws = [w for w in a["words"] if w in p.text.lower()]
                    if len(kws) >= 2:
                        hits.append((1.0, p, f"subject words: {', '.join(sorted(kws)[:4])}", "UNCERTAIN"))
            hits.sort(key=lambda h: -h[0])
            seen = set()
            for sc, p, reason, cert in hits[:max_per_doc]:
                if p.text in seen:
                    continue
                seen.add(p.text)
                if (i["id"], d["id"], p.text) in kept:
                    continue
                rows.append((case_id, i["id"], d["id"], p.text[:1500], p.kind, sc, reason, cert, p.location or None))
    now = utcnow()
    with tx() as conn:
        conn.execute("DELETE FROM doc_links WHERE case_id=? AND status='AUTO'", (case_id,))
        conn.executemany("INSERT INTO doc_links(case_id,issue_id,document_id,passage,passage_kind,score,reason,certainty,location,"
                         "status,created_at) VALUES (?,?,?,?,?,?,?,?,?,'AUTO',?)", [(*r, now) for r in rows])
        audit.log_event(conn, "DOCUMENTS_MAPPED", user_id=user["id"], case_id=case_id,
                        meta={"links": len(rows), "issues": len(iss), "documents": len(docs)})
    return summary(user, case_id)


def links_for_issue(user: dict, issue_id: int, *, include_rejected: bool = False) -> list[dict]:
    with ro() as conn:
        r = conn.execute("SELECT case_id FROM issues WHERE id=?", (issue_id,)).fetchone()
        if not r:
            raise NotFound("Issue not found.")
        cases.check_access(user, r["case_id"])
        sql = ("SELECT l.*, d.original_name AS document_name, d.is_annexure, d.annexure_label FROM doc_links l "
               "JOIN documents d ON d.id=l.document_id WHERE l.issue_id=?" + ("" if include_rejected else " AND l.status<>'REJECTED'")
               + " ORDER BY l.document_id, l.score DESC")
        return [row_to_dict(x) for x in conn.execute(sql, (issue_id,))]


def set_link_status(user: dict, link_id: int, status: str) -> dict:
    if status not in ("AUTO", "ACCEPTED", "REJECTED"):
        raise ValidationError("status must be AUTO, ACCEPTED or REJECTED.")
    with ro() as conn:
        r = conn.execute("SELECT * FROM doc_links WHERE id=?", (link_id,)).fetchone()
    if not r:
        raise NotFound("Link not found.")
    cases.check_access(user, r["case_id"])
    with tx() as conn:
        conn.execute("UPDATE doc_links SET status=? WHERE id=?", (status, link_id))
        audit.log_event(conn, "DOC_LINK_STATUS", user_id=user["id"], case_id=r["case_id"],
                        meta={"link_id": link_id, "issue_id": r["issue_id"], "status": status})
    return {"id": link_id, "status": status}


# ------------------------------------------------------------------ cross-document checks
def _records(case_id: int, fy: int | None, keys_universe: set[str]) -> list[dict]:
    """Dated money records mentioning a known party/reference, one per passage."""
    with ro() as conn:
        docs = _case_docs(conn, case_id)
        skip = _notice_doc_ids(conn, case_id)
    recs = []
    for d in docs:
        if d["id"] in skip or not d.get("text"):
            continue
        for p in passages_for(d["id"], d["text"], json.loads(d.get("tables_json") or "[]")):
            if p.kind == "RECORD":
                continue
            low = p.text.lower()
            keys = {k for k in keys_universe if (k.lower() in low if not k.isupper() else k in refs_in(p.text.upper()))} | (p.keys & keys_universe)
            amts, dts = amounts_in(p.text), dates_in(p.text, fy)
            if keys and amts and dts:
                first = next((ln.strip() for ln in (d.get("text") or "").splitlines() if len(ln.strip()) > 3), d["original_name"])
                title = re.sub(r"(?i)^fictional\s+", "", first)
                recs.append({"document_id": d["id"], "document": title[:1].upper() + title[1:80], "file": d["original_name"],
                             "keys": keys, "amounts": amts, "dates": dts, "text": p.text})
    return recs


def contradictions(user: dict, case_id: int) -> list[dict]:
    case = cases.get_case(user, case_id)
    fy = _fy_start(case.get("assessment_year"))
    with ro() as conn:
        iss = [row_to_dict(r) for r in conn.execute("SELECT * FROM issues WHERE case_id=? ORDER BY seq", (case_id,))]
        docs = _case_docs(conn, case_id)
    universe: set[str] = set()
    for i in iss:
        a = issue_anchors(i, fy)
        universe |= a["names"] | a["refs"]
    ref_docs: dict[str, set[int]] = {}
    shown: dict[str, str] = {}
    for d in docs:
        for m in _REF_RX.finditer((d.get("text") or "").upper()):
            shown.setdefault(re.sub(r"[^A-Z0-9]", "", m.group(0)), m.group(0))
        for r in refs_in((d.get("text") or "").upper()):
            ref_docs.setdefault(r, set()).add(d["id"])
    universe |= {r for r, ds in ref_docs.items() if len(ds) >= 2}
    recs = _records(case_id, fy, universe)
    out, seen = [], set()
    for x in range(len(recs)):
        for y in range(x + 1, len(recs)):
            a, b = recs[x], recs[y]
            if a["document_id"] == b["document_id"]:
                continue
            common_keys = a["keys"] & b["keys"]
            common_amt = a["amounts"] & b["amounts"]
            if not common_keys or not common_amt or a["dates"] & b["dates"]:
                continue
            key = (frozenset(common_keys), frozenset(common_amt), frozenset(a["dates"] | b["dates"]))
            if key in seen:
                continue
            seen.add(key)
            item = ", ".join(sorted(shown.get(k, k) for k in common_keys))
            issue = next((i for i in iss if any(k.lower() in f"{i.get('title') or ''} {i['query_text']}".lower() for k in common_keys)
                          or common_amt & amounts_in(f"{i.get('title') or ''} {i['query_text']}")), None)
            out.append({
                "issue_id": issue["id"] if issue else None, "issue_seq": issue["seq"] if issue else None,
                "item": item, "keys": sorted(common_keys), "amount": inr(max(common_amt)),
                "a_document": a["document"], "a_dates": [fmt_date(d) for d in sorted(a["dates"])],
                "b_document": b["document"], "b_dates": [fmt_date(d) for d in sorted(b["dates"])],
                "text": (f"{item} ({inr(max(common_amt))}): the dates do not agree — {a['document']}: "
                         f"{', '.join(_long(d) for d in sorted(a['dates']))}; {b['document']}: "
                         f"{', '.join(_long(d) for d in sorted(b['dates']))}. Confirm the correct date before relying on either record."),
            })
    return out


# ------------------------------------------------------------------ gaps
# Per requirement key (data/evidence_requirements.json): short wording for the reply, words in the notice that
# ask for it, and words in matched passages that show an uploaded record actually contains it.
SIGNALS: dict[str, dict[str, tuple[str, list[str], list[str]]]] = {
    "UNSECURED_LOAN": {
        "lender_confirmation": ("signed lender confirmations", ["confirmation"], ["confirm"]),
        "lender_itr": ("the lenders' income records", ["creditworth", "capacity", "income", "source of funds"], ["income for the year", "income summary", "return of income", "itr"]),
        "lender_bank": ("the lenders' bank entries and source of funds", ["source of funds", "bank entries", "both parties"], ["balance before", "source record", "bank extract"]),
        "loan_agreement": ("interest / repayment details", ["interest", "repayment", "terms"], ["interest", "repay"]),
        "borrower_bank": ("our bank statement showing receipt of the loans", ["bank entries", "both parties"], ["utr", "neft", "rtgs"]),
        "borrower_ledger": ("the loan ledger", ["ledger"], ["loan ledger", "ledger account"]),
    },
    "CASH_DEPOSITS": {
        "bank_statement": ("the bank statement showing the deposits", ["bank"], ["cash deposit"]),
        "cash_book": ("the cash book", ["cash book"], ["cash book", "opening cash", "cash movement"]),
        "source_mapping": ("deposit-wise source mapping", ["mapping"], ["before deposit", "mapping"]),
        "sales_records": ("the underlying receipts and cash-expense records", ["receipts", "cash-expense", "expense records"], ["voucher", "receipt no", "bill no"]),
        "itr_fs": ("the return of income and financial statements", ["financial statement", "return of income"], ["return of income", "balance sheet", "financial statement"]),
    },
    "CASH_SALES": {
        "sales_ledger": ("the sales ledger", ["sales ledger", "sales register"], ["sales register", "sales ledger"]),
        "invoices": ("sales invoices", ["invoice"], ["invoice"]),
        "cash_book": ("the cash book", ["cash book"], ["cash book", "opening cash"]),
        "gst_returns": ("GST returns", ["gst"], ["gstr"]),
        "stock_records": ("stock records", ["stock"], ["stock"]),
    },
    "DEBTOR_COLLECTIONS": {
        "debtor_ledger": ("the debtor ledger", ["ledger", "debtor"], ["debtor ledger", "ledger account"]),
        "prior_year_fs": ("previous-year financial statements", ["previous year", "opening"], ["previous year", "opening balance"]),
        "customer_confirmation": ("customer confirmations", ["confirmation"], ["confirm"]),
        "original_invoices": ("the original sales invoices", ["invoice"], ["invoice"]),
    },
    "CAPITAL_CONTRIBUTION": {
        "capital_account": ("the capital accounts", ["capital"], ["capital account"]),
        "partner_confirmation": ("the partners' confirmations", ["confirmation"], ["confirm"]),
        "partner_source": ("the partners' source of funds", ["source"], ["source record", "balance before"]),
        "partnership_deed": ("the partnership deed", ["deed"], ["deed"]),
    },
    "CUSTOMER_ADVANCE": {
        "customer_confirmation": ("customer confirmations", ["confirmation"], ["confirm"]),
        "order_agreement": ("the orders / agreements", ["order", "agreement"], ["purchase order", "agreement"]),
        "adjustment_invoice": ("the invoices against which the advances were adjusted", ["adjust"], ["adjusted"]),
    },
    "BANK_CREDITS": {
        "bank_statement": ("the bank statement", ["bank statement"], ["narration", "credit"]),
        "bank_book": ("the bank book", ["bank book"], ["bank book"]),
        "credit_classification": ("a classification of the credits", ["nature", "classif"], ["classif", "nature of credit"]),
        "sales_ledger": ("the sales ledger", ["sales"], ["sales register", "sales ledger"]),
    },
    "TDS_MISMATCH": {
        "ais_26as": ("Form 26AS / AIS", ["26as", "ais"], ["26as", "ais"]),
        "itr": ("the return of income", ["return"], ["return of income", "itr"]),
        "reconciliation": ("a reconciliation", ["reconcil"], ["reconcil"]),
    },
    "BUSINESS_EXPENSES": {
        "bills": ("bills and vouchers", ["bill", "voucher", "invoice"], ["bill no", "voucher", "invoice"]),
        "ledger": ("the expense ledger", ["ledger"], ["ledger"]),
        "payment_proof": ("payment evidence", ["payment"], ["paid", "payment"]),
    },
    "PROPERTY_TRANSACTION": {
        "deeds": ("the sale / purchase deed", ["deed"], ["deed"]),
        "payment_trail": ("the payment trail", ["payment"], ["paid", "payment"]),
        "valuation": ("the valuation / stamp-duty value", ["valuation", "stamp"], ["valuation", "stamp duty"]),
    },
    "SALES_GST_RECONCILIATION": {
        "sales_ledger": ("the sales ledger", ["sales ledger", "books"], ["sales register", "book amount"]),
        "gst_returns": ("filed return summaries", ["return summar", "filed return"], ["gstr"]),
        "gst_reconciliation": ("a reconciliation of the books to the returns", ["reconciliation"], ["gstr", "reconcil"]),
        "sample_invoices": ("invoice-wise classification and sample invoices", ["invoice"], ["invoice"]),
    },
    "TRADE_CREDITORS": {
        "creditor_confirmation": ("party-wise confirmations", ["confirmation"], ["confirm"]),
        "creditor_invoices": ("purchase invoices making up the balances", ["invoices"], ["invoice"]),
        "creditor_ledger": ("creditor ledger extracts", ["ledger"], ["ledger extract", "ledger account"]),
        "subsequent_settlement": ("subsequent settlement details and bank entries", ["settlement", "bank entries"], ["by bank", "settlement"]),
    },
    "PURCHASES": {
        "purchase_invoices": ("purchase invoices", ["invoice"], ["invoice"]),
        "goods_receipt": ("goods-received / inward-register entries and stock movement", ["goods-received", "goods received", "inward", "stock"], ["grn", "inward", "goods received"]),
        "delivery_evidence": ("transport / delivery evidence", ["transport", "delivery"], ["docket", "delivery", "transport"]),
        "purchase_payment": ("payment entries", ["payment"], ["payment", "paid"]),
        "purchase_ledger": ("the purchase-ledger accounts", ["purchase-ledger", "purchase ledger"], ["purchase ledger", "purchase-ledger"]),
    },
    "FIXED_ASSETS": {
        "asset_invoices": ("supplier invoices", ["invoice"], ["invoice"]),
        "asset_payment": ("payment evidence", ["payment"], ["paid", "payment", "bank ref"]),
        "put_to_use": ("delivery / installation records and dates first put to use", ["put to use", "installation", "commissioning"], ["commission", "first used", "put to use", "delivered"]),
        "asset_register": ("asset-register entries", ["asset-register", "asset register"], ["asset tag", "asset register"]),
        "depreciation_computation": ("the depreciation computation", ["depreciation computation", "computation"], ["depreciation"]),
    },
}

STATE_LABELS = {"READ": "Uploaded and read", "AVAILABLE_WITH_CA": "Available with the CA (not uploaded)",
                "NOT_AVAILABLE": "Not available", "CONFLICT": "Conflicting / unclear", "NOT_PROVIDED": "Not provided yet"}


def _requirements(category: str) -> list[dict]:
    from pathlib import Path

    data = json.loads((Path(__file__).resolve().parents[1] / "data" / "evidence_requirements.json").read_text(encoding="utf-8"))
    return (data["categories"].get(category) or data["categories"]["GENERAL"])["requirements"]


def record_status(issue: dict, links: list[dict], contradictions_for_issue: list[dict] | None = None) -> list[dict]:
    """One row per record type for this issue, in four distinct states:
    READ (an uploaded record contains it), AVAILABLE_WITH_CA (CA confirms it is held, not uploaded),
    NOT_AVAILABLE (CA says it is not held), CONFLICT (records disagree, or CA's mark contradicts what was read),
    NOT_PROVIDED (nothing known yet). `asked` = the notice's own wording asks for it."""
    a = issue.get("analysis_json") or {}
    if isinstance(a, str):
        a = json.loads(a or "{}")
    available = set(a.get("available_records") or [])
    unavailable = set(a.get("unavailable_records") or [])
    q = f"{issue.get('title') or ''} {issue['query_text']}".lower()
    strong_docs = {l["document_id"] for l in links if l["status"] != "REJECTED" and (l["certainty"] == "STRONG" or l["status"] == "ACCEPTED")}
    used = [l for l in links if l["status"] != "REJECTED" and l["document_id"] in strong_docs]  # documents that clearly relate
    found = " ".join(l["passage"].lower() for l in used)
    sig = SIGNALS.get(issue["category"], {})
    conflict_text = " ".join(c["text"].lower() for c in contradictions_for_issue or [])
    out = []
    for r in _requirements(issue["category"]):
        short, ask, have = sig.get(r["key"], (r["label"][0].lower() + r["label"][1:], [], []))
        asked = any(w in q for w in ask)
        read = bool(have) and any(w in found for w in have)
        docs = sorted({l["document_name"] for l in used if any(w in l["passage"].lower() for w in have)}) if read else []
        if read and r["key"] in unavailable:
            state, detail = "CONFLICT", "Marked not available, but an uploaded record appears to contain it."
        elif read and conflict_text and any(d.lower() in conflict_text for d in docs):
            state, detail = "CONFLICT", "Uploaded records disagree on this item."
        elif read:
            state, detail = "READ", ", ".join(docs)
        elif r["key"] in unavailable:
            state, detail = "NOT_AVAILABLE", ""
        elif r["key"] in available:
            state, detail = "AVAILABLE_WITH_CA", ""
        else:
            state, detail = "NOT_PROVIDED", ""
        out.append({"key": r["key"], "label": r["label"], "short": short, "asked": asked, "state": state,
                    "state_label": STATE_LABELS[state], "detail": detail})
    return out


def gaps_for_issue(issue: dict, links: list[dict]) -> list[str]:
    """Record types the notice asks for that no uploaded record contains."""
    return [r["short"] for r in record_status(issue, links) if r["asked"] and r["state"] != "READ"]


def summary(user: dict, case_id: int) -> dict:
    cases.check_access(user, case_id)
    with ro() as conn:
        iss = [row_to_dict(r) for r in conn.execute("SELECT * FROM issues WHERE case_id=? ORDER BY seq", (case_id,))]
    per = []
    contra = contradictions(user, case_id)
    for i in iss:
        ls = links_for_issue(user, i["id"])
        per.append({"issue_id": i["id"], "seq": i["seq"], "title": i.get("title"), "category": i["category"],
                    "documents": [{"document_id": did, "name": nm} for did, nm in
                                  sorted({(l["document_id"], l["document_name"]) for l in ls if l["certainty"] == "STRONG"
                                          or l["status"] == "ACCEPTED"}, key=lambda x: x[1])],
                    "strong": sum(1 for l in ls if l["certainty"] == "STRONG"),
                    "uncertain": sum(1 for l in ls if l["certainty"] == "UNCERTAIN" and l["status"] == "AUTO"),
                    "gaps": gaps_for_issue(i, ls),
                    "records": record_status(i, ls, [c for c in contra if c.get("issue_id") == i["id"]])})
    return {"case_id": case_id, "issues": per, "contradictions": contra}
