"""Module 5 — issue-wise notice analysis.

Each notice query becomes a separate issue with the structured analysis fields
required by the Project Instructions §4 and §6. The rule-based analysis gives
orientation (category, evidence needed, candidate provisions, both-side
perspectives). It never states a legal conclusion: candidate provisions are
listed as 'to be examined', and the CA records the conclusion."""
from __future__ import annotations

import json
import re

from ..core import audit
from ..core.config import STATIC_DATA_DIR
from ..core.db import dumps, ro, row_to_dict, tx, utcnow
from ..core.errors import NotFound, ValidationError
from .auth import require_role
from . import cases
from .notice_parser import parse_amount, split_queries

STRATEGIES = {
    "ACCEPT_EXPLAIN": "Accept and explain",
    "ACCEPT_WITH_DOCS": "Accept with supporting documents",
    "DISPUTE_FACTUAL": "Dispute with factual evidence",
    "DISPUTE_LEGAL": "Dispute with legal reasoning",
    "SEEK_CLARIFICATION": "Seek clarification",
    "REQUEST_TIME": "Request additional time (where legally and procedurally appropriate)",
    "OBTAIN_CLIENT_INFO": "Obtain further information from the client",
    "ESCALATE_CA": "Escalate for detailed CA review",
}

CANDIDATE_REFS = {
    "CASH_DEPOSITS": ["IT1961_S68", "IT1961_S69A", "IT1961_S115BBE", "IT1961_S269ST"],
    "CASH_SALES": ["IT1961_S269ST"],
    "DEBTOR_COLLECTIONS": ["IT1961_S68"],
    "CAPITAL_CONTRIBUTION": ["IT1961_S68", "IT1961_S269SS"],
    "UNSECURED_LOAN": ["IT1961_S68", "IT1961_S269SS", "IT1961_S115BBE"],
    "CUSTOMER_ADVANCE": ["IT1961_S68"],
    "BANK_CREDITS": ["IT1961_S68", "IT1961_S69A"],
    "TDS_MISMATCH": [],
    "BUSINESS_EXPENSES": ["IT1961_S69C", "IT1961_S40A3"],
    "PROPERTY_TRANSACTION": ["IT1961_S69"],
    "SALES_GST_RECONCILIATION": ["IT1961_S69A"],
    "TRADE_CREDITORS": ["IT1961_S41_1", "IT1961_S68"],
    "PURCHASES": ["IT1961_S69C"],
    "FIXED_ASSETS": ["IT1961_S32"],
    "GENERAL": [],
}

PERSPECTIVES = {
    "CASH_DEPOSITS": {
        "assessee": "Deposits may be explained by receipts recorded in the books (cash sales, debtor collections, capital) where the receipts precede the deposits and the cash book shows sufficient balance.",
        "revenue": "The nature and source of each deposit must be satisfactorily explained; recorded sales or collections may be questioned if invoices, stock movement or counter-party confirmation are lacking, or if chronology/cash balance does not support the deposit.",
        "balanced": "Outcome depends on deposit-wise chronology, cash-balance availability, and documentary support for each underlying receipt. Do not apply s.68 vs s.69A until the actual books and entries are examined.",
    },
    "UNSECURED_LOAN": {
        "assessee": "Identity, creditworthiness and genuineness may be supported by confirmation, PAN, ITR and banking-channel receipt.",
        "revenue": "Documentary formalities alone may not establish creditworthiness/genuineness; the lender's own source (e.g., cash deposited just before the transfer) may be examined, especially where the proviso on source of source applies.",
        "balanced": "Assess the lender's capacity and fund trail. A cash deposit in the lender's account is a risk factor, not automatically an addition in the assessee's hands.",
    },
    "CAPITAL_CONTRIBUTION": {
        "assessee": "Contributions are recorded in capital accounts; partners can explain their own sources.",
        "revenue": "Cash contributions without partner source evidence may be questioned as credits not satisfactorily explained.",
        "balanced": "Analyse the partner's source evidence and the applicable law separately for each partner; also consider cash-mode restrictions.",
    },
    "CUSTOMER_ADVANCE": {
        "assessee": "Advances are trade receipts against orders and are adjusted against subsequent sales.",
        "revenue": "Advances without confirmation, order or subsequent adjustment may be questioned as unexplained credits.",
        "balanced": "Treat each advance on its own evidence; adjusted advances with confirmation stand on a different footing from open, unconfirmed balances.",
    },
}
PERSPECTIVES.update({
    "SALES_GST_RECONCILIATION": {
        "assessee": "Book sales and returned outward supplies agree in total; any subtotal difference is a classification (taxable vs exempt/nil-rated), not unrecorded turnover.",
        "revenue": "A difference between book sales and return figures may indicate unreported or misclassified turnover.",
        "balanced": "Reconcile totals first, then classification. A classification question is a GST matter and does not by itself mean income escaped tax.",
    },
    "TRADE_CREDITORS": {
        "assessee": "Balances arise from recorded purchases, are confirmed by the suppliers and were settled through banking channels after the year end.",
        "revenue": "Unconfirmed or long-outstanding balances may be questioned as non-genuine liabilities or ceased liabilities.",
        "balanced": "Confirmation plus subsequent settlement through banking channels is strong evidence; unpaid, unconfirmed balances need separate attention.",
    },
    "PURCHASES": {
        "assessee": "Purchases are supported by invoices, goods receipt, stock entries, delivery evidence and payment through banking channels.",
        "revenue": "Purchases may be questioned as non-genuine where delivery, stock movement or the supplier's existence is not established.",
        "balanced": "Test each selected purchase across invoice, receipt of goods, stock and payment trail; inconsistent dates need explanation.",
    },
    "FIXED_ASSETS": {
        "assessee": "Additions are supported by invoices, payments and records of the date first put to use; depreciation follows the prescribed rates.",
        "revenue": "Depreciation may be restricted where ownership, use or the date first put to use is not established, or the rate is incorrect.",
        "balanced": "Confirm cost, payment, ownership and date of first use; the date decides whether half-rate depreciation applies.",
    },
})
DEFAULT_PERSPECTIVE = {
    "assessee": "[CA to complete — arguments supporting the assessee, with verified sources]",
    "revenue": "[CA to complete — possible arguments supporting the Department]",
    "balanced": "[CA to complete — strengths, weaknesses and unresolved issues]",
}


def _requirements() -> dict:
    return json.loads((STATIC_DATA_DIR / "evidence_requirements.json").read_text(encoding="utf-8"))["categories"]


def categorise(text: str, title: str | None = None) -> str:
    """Classify from the query's own heading first (weighted), then from its full wording.

    The heading is what the Department chose to call the matter ("Trade creditors of ₹9,80,000"),
    so a keyword there outweighs incidental words in the body (e.g. "loan" in a list of records)."""
    t = (text or "").lower()
    h = (title or "").lower()
    if not h:  # no separate heading: treat the first clause as the heading
        h = re.split(r"[.:;]", t, maxsplit=1)[0][:120]
    best, score = "GENERAL", 0
    for cat, spec in _requirements().items():
        kws = spec.get("keywords", [])
        s = 6 * sum(1 for k in kws if k in h) + sum(t.count(k) for k in kws)
        if s > score:
            best, score = cat, s
    return best


def build_analysis(query: str, category: str) -> dict:
    reqs = _requirements()[category]["requirements"]
    amt = parse_amount(query)
    persp = PERSPECTIVES.get(category, DEFAULT_PERSPECTIVE)
    return {
        "department_question": query,
        "relevant_transaction": "[To be identified from records]",
        "amount_mentioned": amt if amt is not None else "NOT PROVIDED",
        "information_available": [],
        "information_required": [r["label"] for r in reqs],
        "evidence_required": [r["key"] for r in reqs],
        "potential_issue": f"Category: {category.replace('_', ' ').title()} — characterisation and evidence to be examined.",
        "candidate_provisions_to_examine": CANDIDATE_REFS.get(category, []),
        "candidate_provisions_note": "Listed for examination only. Applicability depends on the factual character of the transaction and verified statutory conditions; do not apply mechanically.",
        "perspectives": persp,
        "possible_consequences": "Possible addition/disallowance and consequential penalty proceedings if not satisfactorily explained — exposure depends on facts and CA assessment.",
        "recommended_next_action": "Map evidence; obtain missing documents from the client; CA to decide strategy.",
        "ca_conclusion": None,
        "status_labels": {"facts": "UNVERIFIED", "explanation": "CLIENT EXPLANATION – NOT YET VERIFIED"},
    }


def generate_from_notice(user: dict, notice_id: int, *, replace: bool = False) -> list[dict]:
    from .notices import get_notice
    from .documents import get_text

    n = get_notice(user, notice_id)
    text = get_text(user, n["document_id"])["text"] if n["document_id"] else ""
    queries = split_queries(text)
    if not queries:
        raise ValidationError("No numbered queries detected in the notice. Add issues manually.")
    now = utcnow()
    with tx() as conn:
        if replace:
            conn.execute("DELETE FROM issues WHERE notice_id=?", (notice_id,))
        start = conn.execute("SELECT COALESCE(MAX(seq),0) FROM issues WHERE case_id=?", (n["case_id"],)).fetchone()[0]
        for i, q in enumerate(queries, 1):
            title = q.get("title")
            cat = categorise(q["text"], title)
            amount = parse_amount(title or "") or parse_amount(q["text"])
            conn.execute(
                "INSERT INTO issues(case_id,notice_id,seq,query_text,category,amount,analysis_json,created_at,updated_at,title) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (n["case_id"], notice_id, start + i, q["text"], cat, amount, dumps(build_analysis(q["text"], cat)), now, now, title))
        cases.touch(conn, n["case_id"])
        audit.log_event(conn, "ISSUES_GENERATED", user_id=user["id"], case_id=n["case_id"],
                        meta={"notice_id": notice_id, "n_issues": len(queries)})
    from .authorities import seed_issue_propositions
    from .evidence import auto_map

    auto_map(user, n["case_id"])
    out = list_issues(user, n["case_id"])
    for i in out:  # V3: every issue starts with a traceable, unverified starting-point proposition
        seed_issue_propositions(user, i["id"])
    from .mapping import map_case

    map_case(user, n["case_id"])  # read the uploaded records against the new issues
    return list_issues(user, n["case_id"])


def add_issue(user: dict, case_id: int, query_text: str, category: str | None = None, amount: float | None = None) -> dict:
    cases.check_access(user, case_id)
    if not query_text or len(query_text) > 5000:
        raise ValidationError("Query text required (max 5000 chars).")
    cat = category or categorise(query_text)
    if cat not in _requirements():
        raise ValidationError(f"Unknown category {cat}.")
    now = utcnow()
    with tx() as conn:
        seq = conn.execute("SELECT COALESCE(MAX(seq),0)+1 FROM issues WHERE case_id=?", (case_id,)).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO issues(case_id,seq,query_text,category,amount,analysis_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (case_id, seq, query_text, cat, amount if amount is not None else parse_amount(query_text),
             dumps(build_analysis(query_text, cat)), now, now))
        iid = cur.lastrowid
        audit.log_event(conn, "ISSUE_ADDED", user_id=user["id"], case_id=case_id, meta={"issue_id": iid, "category": cat})
    from .authorities import seed_issue_propositions
    from .evidence import auto_map

    auto_map(user, case_id)
    seed_issue_propositions(user, iid)
    return get_issue(user, iid)


def merge_issues(user: dict, target_id: int, source_ids: list[int], query_text: str) -> dict:
    """Combine parser-split issue rows while retaining a CA-auditable history.

    The chosen target keeps its category and amount. Source analyses and
    evidence assessments are copied into target.analysis_json before rows are
    removed; evidence and propositions are reassigned to the target.
    """
    require_role(user, "ADMIN", "CA")
    target = get_issue(user, target_id)
    query_text = (query_text or "").strip()
    if len(query_text) < 10 or len(query_text) > 8000:
        raise ValidationError("Enter the corrected combined notice question (10–8000 characters).")
    ids = list(dict.fromkeys(int(x) for x in (source_ids or []) if int(x) != target_id))
    if not ids or len(ids) > 30:
        raise ValidationError("Select at least one other issue to merge into the main issue.")
    all_ids = [target_id, *ids]
    now = utcnow()
    with tx() as conn:
        rows = conn.execute(
            "SELECT * FROM issues WHERE id IN (" + ",".join("?" for _ in all_ids) + ") ORDER BY seq",
            all_ids).fetchall()
        if len(rows) != len(all_ids):
            raise ValidationError("One or more selected issues were not found.")
        if any(r["case_id"] != target["case_id"] for r in rows):
            raise ValidationError("All issues must belong to the same case.")
        if len({r["notice_id"] for r in rows}) > 1:
            raise ValidationError("Issues from different notices cannot be merged.")
        if conn.execute("SELECT 1 FROM drafts WHERE case_id=? LIMIT 1", (target["case_id"],)).fetchone():
            raise ValidationError("This case already has a draft. Correct the issue list before generating a new draft version.")

        source_rows = [r for r in rows if r["id"] != target_id]
        history = []
        for row in source_rows:
            item = dict(row)
            item["analysis_json"] = json.loads(item["analysis_json"] or "{}")
            evidence_rows = conn.execute(
                "SELECT e.*, d.original_name AS document_name FROM evidence_items e "
                "LEFT JOIN documents d ON d.id=e.document_id WHERE e.issue_id=? ORDER BY e.id", (row["id"],)).fetchall()
            item["evidence_history"] = [dict(e) for e in evidence_rows]
            history.append(item)
            conn.execute("UPDATE evidence_items SET issue_id=? WHERE issue_id=?", (target_id, row["id"]))
            conn.execute("UPDATE propositions SET issue_id=? WHERE issue_id=?", (target_id, row["id"]))

        target_row = next(r for r in rows if r["id"] == target_id)
        analysis = json.loads(target_row["analysis_json"] or "{}")
        analysis.setdefault("merged_issue_history", []).extend(history)
        positions = [json.loads(r["analysis_json"] or "{}").get("concern_position") for r in rows]
        if len(set(positions)) > 1:
            # A consolidated concern needs one fresh CA conclusion when the
            # parser fragments had different or incomplete positions.
            analysis.pop("concern_position", None)
            analysis.pop("concern_position_by", None)
            analysis.pop("concern_position_at", None)
            analysis.pop("concern_position_basis", None)
        valid_keys = {r["key"] for r in _requirements().get(target_row["category"], {}).get("requirements", [])}
        available = set(analysis.get("available_records") or [])
        for row in source_rows:
            source_analysis = json.loads(row["analysis_json"] or "{}")
            if row["category"] == target_row["category"]:
                available.update(source_analysis.get("available_records") or [])
        analysis["available_records"] = sorted(available & valid_keys)
        amounts = {r["amount"] for r in rows}
        # Prefer an amount explicitly present in the corrected consolidated
        # question; never sum amounts from fragments automatically.
        merged_amount = parse_amount(query_text)
        if merged_amount is None and len(amounts) == 1:
            merged_amount = target_row["amount"]
        conn.execute("UPDATE issues SET query_text=?, amount=?, analysis_json=?, updated_at=? WHERE id=?",
                     (query_text, merged_amount, dumps(analysis), now, target_id))
        conn.execute("DELETE FROM issues WHERE id IN (" + ",".join("?" for _ in ids) + ")", ids)
        remaining = conn.execute("SELECT id FROM issues WHERE case_id=? ORDER BY seq,id", (target["case_id"],)).fetchall()
        for seq, row in enumerate(remaining, 1):
            conn.execute("UPDATE issues SET seq=? WHERE id=?", (seq, row["id"]))
        cases.touch(conn, target["case_id"])
        audit.log_event(conn, "ISSUES_MERGED", user_id=user["id"], case_id=target["case_id"],
                        meta={"target_issue_id": target_id, "merged_issue_ids": ids, "resulting_issue_count": len(remaining)})
    return get_issue(user, target_id)


def update_query_text(user: dict, issue_id: int, query_text: str) -> dict:
    """Let the CA trim OCR/footer noise from the notice question without
    changing its saved assessments or evidence history."""
    require_role(user, "ADMIN", "CA")
    i = get_issue(user, issue_id)
    query_text = (query_text or "").strip()
    if len(query_text) < 10 or len(query_text) > 8000:
        raise ValidationError("The corrected notice question must be 10–8000 characters.")
    amount = parse_amount(query_text)
    with tx() as conn:
        conn.execute("UPDATE issues SET query_text=?, amount=?, updated_at=? WHERE id=?",
                     (query_text, amount, utcnow(), issue_id))
        audit.log_event(conn, "ISSUE_QUERY_CORRECTED", user_id=user["id"], case_id=i["case_id"],
                        meta={"issue_id": issue_id, "amount_detected": amount is not None})
        cases.touch(conn, i["case_id"])
    from . import evidence
    evidence.auto_map(user, i["case_id"])
    return get_issue(user, issue_id)


def get_issue(user: dict, issue_id: int) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()
    if not r:
        raise NotFound("Issue not found.")
    d = row_to_dict(r, ("analysis_json",))
    cases.check_access(user, d["case_id"])
    return d


def list_issues(user: dict, case_id: int) -> list[dict]:
    cases.check_access(user, case_id)
    with ro() as conn:
        rows = conn.execute("SELECT * FROM issues WHERE case_id=? ORDER BY seq", (case_id,)).fetchall()
    return [row_to_dict(r, ("analysis_json",)) for r in rows]


_ANALYSIS_EDITABLE = {"client_explanation", "client_explanation_confirmed", "relevant_transaction", "information_available", "potential_issue", "possible_consequences",
                      "recommended_next_action", "ca_conclusion", "perspectives", "candidate_provisions_to_examine",
                      "concern_position", "concern_position_basis", "available_records",
                      "unavailable_records"}
_CONCERN_POSITIONS = {"TRUE", "PARTLY_TRUE", "FALSE", "NEED_CLIENT_INFO"}


def update_analysis(user: dict, issue_id: int, updates: dict) -> dict:
    bad = set(updates) - _ANALYSIS_EDITABLE
    if bad:
        raise ValidationError(f"Non-editable fields: {sorted(bad)}")
    if {"concern_position", "concern_position_basis"} & set(updates):
        require_role(user, "ADMIN", "CA")
    for fld in ("available_records", "unavailable_records"):
        if fld not in updates:
            continue
        require_role(user, "ADMIN", "CA")
        i = get_issue(user, issue_id)
        keys = updates[fld]
        if not isinstance(keys, list) or any(not isinstance(k, str) for k in keys):
            raise ValidationError(f"{fld} must be a list of evidence requirement keys.")
        valid = {r["key"] for r in _requirements().get(i["category"], {}).get("requirements", [])}
        if not set(keys).issubset(valid):
            raise ValidationError("One or more selected records do not belong to this issue.")
        updates[fld] = sorted(set(keys))
    if set(updates.get("available_records") or []) & set(updates.get("unavailable_records") or []):
        raise ValidationError("A record cannot be both available and not available.")
    if "concern_position" in updates and updates["concern_position"] not in _CONCERN_POSITIONS:
        raise ValidationError(f"concern_position must be one of {sorted(_CONCERN_POSITIONS)}.")
    if "concern_position_basis" in updates and len(str(updates["concern_position_basis"] or "")) > 2000:
        raise ValidationError("concern_position_basis must be at most 2000 characters.")
    if "ca_conclusion" in updates and updates["ca_conclusion"] and user["role"] != "CA":
        raise ValidationError("Only a CA can record a CA conclusion.")
    i = get_issue(user, issue_id)
    a = i["analysis_json"]
    a.update(updates)
    if "concern_position" in updates:
        a["concern_position_by"] = user["username"]
        a["concern_position_at"] = utcnow()
    if "ca_conclusion" in updates and updates["ca_conclusion"]:
        a["ca_conclusion_by"] = user["username"]
    with tx() as conn:
        conn.execute("UPDATE issues SET analysis_json=?, updated_at=? WHERE id=?", (dumps(a), utcnow(), issue_id))
        audit.log_event(conn, "ISSUE_ANALYSIS_UPDATED", user_id=user["id"], case_id=i["case_id"],
                        meta={"issue_id": issue_id, "fields": sorted(updates)})
    return get_issue(user, issue_id)


def set_strategy(user: dict, issue_id: int, strategy: str, reason: str) -> dict:
    if strategy not in STRATEGIES:
        raise ValidationError(f"Strategy must be one of {sorted(STRATEGIES)}.")
    if not reason or len(reason.strip()) < 10:
        raise ValidationError("Every strategy needs a reason (min 10 chars).")
    i = get_issue(user, issue_id)
    with tx() as conn:
        conn.execute("UPDATE issues SET strategy=?, strategy_reason=?, updated_at=? WHERE id=?", (strategy, reason.strip(), utcnow(), issue_id))
        audit.log_event(conn, "STRATEGY_SET", user_id=user["id"], case_id=i["case_id"], meta={"issue_id": issue_id, "strategy": strategy})
    return get_issue(user, issue_id)


def suggest_strategy(user: dict, issue_id: int) -> dict:
    """Rule-based suggestion from the evidence matrix; user must still set it."""
    from .evidence import list_for_issue

    items = list_for_issue(user, issue_id)
    statuses = [e["status"] for e in items]
    if not items:
        return {"strategy": "OBTAIN_CLIENT_INFO", "reason": "No evidence mapped yet."}
    if "CONTRADICTORY" in statuses:
        return {"strategy": "ESCALATE_CA", "reason": "Contradictory evidence exists; CA must resolve before any submission."}
    if all(s == "SUFFICIENT" for s in statuses):
        return {"strategy": "DISPUTE_FACTUAL", "reason": "All mapped requirements assessed SUFFICIENT; respond with factual evidence (CA to confirm)."}
    if any(s in ("NOT_PROVIDED", "INSUFFICIENT") for s in statuses):
        return {"strategy": "OBTAIN_CLIENT_INFO", "reason": "One or more requirements NOT PROVIDED or INSUFFICIENT; obtain from client before replying. Consider requesting time if the deadline is near."}
    return {"strategy": "ESCALATE_CA", "reason": "Evidence partially sufficient / requires verification; CA judgement needed."}
