"""Module 10 — draft reply and annexure index.

Rules enforced in code:
* Facts not on record are inserted as visible placeholders: [TO BE CONFIRMED: …].
* Annexure references are generated only for uploaded annexures or records the
  CA has explicitly marked as available for the issue; the CA attaches those
  records to the final submission outside this workbench.
* Legal references render only if VERIFIED in the registry; otherwise a
  [… REQUIRES CA VERIFICATION] placeholder is inserted.
* No case law is generated. Precedents appear only if a CA has added and
  verified them in the registry and selected them for an issue.
* Internal notes (gaps, risks) are kept separate and are never exported.
* Every edit creates a new version with a new content hash.
"""
from __future__ import annotations

import io
import json
import re

from ..core import audit
from ..core.db import dumps, ro, row_to_dict, tx, utcnow
from ..core.errors import NotFound, ValidationError
from ..core.pii import mask_pan
from ..core.security import sha256_text
from .auth import require_role
from . import authorities, cases, evidence, issues, notices, taxlaw
from .notice_parser import NP

PLACEHOLDER_RX = re.compile(r"\[(?:TO BE CONFIRMED|TO BE INSERTED|[^\]]*REQUIRES CA VERIFICATION|CA TO COMPLETE|CA TO CONFIRM|CA REVIEW)[^\]]*\]", re.I)
SECTION_ORDER = ["to_from", "subject", "reference", "background", "preliminary", "issues", "legal", "annexures", "prayer", "signature"]


def _v(p: dict, k: str) -> str:
    val = (p.get(k) or {}).get("value")
    return val if val and val != NP else f"[TO BE CONFIRMED: {k.replace('_', ' ')}]"


def _next_annexure_label(used: set[str]) -> str:
    n = 0
    while True:
        n, label = n + 1, ""
        value = n
        while value:
            value, rem = divmod(value - 1, 26)
            label = chr(65 + rem) + label
        if label not in used:
            used.add(label)
            return label


def _issue_paragraph(i: dict, ev: list[dict], ann: dict[int, str], props: list[dict] | None = None,
                     record_annexures: dict[str, str] | None = None) -> dict:
    """Build one issue block. Also returns `basis_map`, which separates facts
    supported by documents from explanations awaiting client confirmation."""
    strat = i.get("strategy")
    a = i["analysis_json"]
    amount = f" — Rs. {i['amount']:,.0f}" if i.get("amount") is not None else ""
    head = f"Query No. {i['seq']}: {i['category'].replace('_', ' ').title()}{amount}"
    if i.get("category") == "UNSECURED_LOAN":
        lender_match = re.search(r"\b(?:loan|credit)\s+from\s+(?:(?:Mr|Mrs|Ms)\.?\s+)?([A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+){0,2})", i.get("query_text", ""))
        if lender_match:
            head = f"Query No. {i['seq']}: Unsecured loan from {lender_match.group(1).strip()}{amount}"
    paras: list[str] = []
    basis_map: list[dict] = []
    expl = (a.get("client_explanation") or "").strip()
    expl_ok = bool(a.get("client_explanation_confirmed"))
    position = a.get("concern_position")
    available = set(a.get("available_records") or [])
    requirement_rows = {}
    for item in ev:
        requirement_rows.setdefault(item["requirement"], item)
    available_labels = [requirement_rows[k]["requirement_label"] for k in sorted(available) if k in requirement_rows]
    factual_basis = (a.get("concern_position_basis") or "").strip()
    if i.get("category") == "UNSECURED_LOAN" and position in ("TRUE", "PARTLY_TRUE", "FALSE"):
        lender_match = re.search(r"\b(?:loan|credit)\s+from\s+(?:(?:Mr|Mrs|Ms)\.?\s+)?([A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+){0,2})", i.get("query_text", ""))
        lender = lender_match.group(1).strip() if lender_match else "the lender"
        amount_text = f"Rs. {i['amount']:,.0f}" if i.get("amount") is not None else "the amount stated in the notice"
        paras.append(f"With reference to Query No. {i['seq']}, we respectfully submit the following in respect of the unsecured loan of {amount_text} received from {lender}.")
        if position == "FALSE":
            paras.append("We respectfully submit that the concern, to the extent it treats this credit as unexplained, is not borne out by the records set out below.")
        elif position == "PARTLY_TRUE":
            paras.append("We accept the factual aspect recorded in the notice to the extent stated and respectfully submit that the supporting records explain the nature and source of the credit.")
        subheading_no = 0
        if "lender_confirmation" in available:
            subheading_no += 1
            label = record_annexures.get("lender_confirmation") if record_annexures else None
            paras += [f"{subheading_no}. Identity of the lender", "The lender's signed confirmation, containing the lender's name, address, PAN, amount advanced and date of transaction, is furnished for consideration" + (f" as Annexure {label}." if label else ".")]
        if "lender_itr" in available or "lender_bank" in available:
            subheading_no += 1
            paras.append(f"{subheading_no}. Creditworthiness and source of funds")
            details = []
            if "lender_itr" in available:
                label = record_annexures.get("lender_itr") if record_annexures else None
                details.append("The lender's ITR, computation and financial records supporting the stated financial capacity are furnished" + (f" as Annexure {label}" if label else ""))
            if "lender_bank" in available:
                label = record_annexures.get("lender_bank") if record_annexures else None
                details.append("The lender's bank statement evidencing the transfer, together with the available source-of-funds records, is furnished" + (f" as Annexure {label}" if label else ""))
            paras.append(". ".join(details).rstrip(". ") + ".")
        if "borrower_bank" in available or "borrower_ledger" in available:
            subheading_no += 1
            paras.append(f"{subheading_no}. Receipt and recording of the loan")
            if "borrower_bank" in available:
                label = record_annexures.get("borrower_bank") if record_annexures else None
                paras.append("Our bank statement records receipt of the loan through banking channels" + (f" and is enclosed as Annexure {label}." if label else "."))
            if "borrower_ledger" in available:
                label = record_annexures.get("borrower_ledger") if record_annexures else None
                paras.append("The corresponding unsecured-loan ledger in our books records the credit" + (f" and is enclosed as Annexure {label}." if label else "."))
        if "loan_agreement" in available:
            subheading_no += 1
            label = record_annexures.get("loan_agreement") if record_annexures else None
            paras += [f"{subheading_no}. Terms of the loan and interest", "The available record of the loan terms, repayment and interest particulars is furnished for consideration" + (f" as Annexure {label}." if label else ".")]
        if available:
            paras.append("Taken together, the records identified above support our explanation regarding the identity of the lender, the source and movement of funds, and the recording of the loan, to the extent applicable.")
        if not available:
            paras.append("[CA TO CONFIRM: add the factual explanation and the records being furnished for this issue].")
    elif position == "TRUE":
        paras.append("We respectfully submit the following in response to the concern raised, with reference to the records identified below." if available_labels else "We respectfully submit the following in response to the concern raised. [CA TO CONFIRM: factual explanation and records relied upon].")
    elif position == "PARTLY_TRUE":
        paras.append("We accept the matter only to the extent borne out by the facts and respectfully submit the following explanation for consideration." if available_labels else "We accept the matter only to the extent borne out by the facts. [CA TO CONFIRM: accepted portion and explanation for the balance].")
    elif position == "FALSE":
        paras.append("We respectfully submit that the concern, as framed, does not reflect the complete factual position. The relevant facts and records are set out below." if available_labels else "We respectfully submit that the concern, as framed, does not reflect the complete factual position. [CA TO CONFIRM: factual basis and records relied upon].")
    elif position == "NEED_CLIENT_INFO":
        if expl and not expl_ok:
            paras.append(f"[TO BE CONFIRMED BY CLIENT: {expl}]")
        elif expl and expl_ok:
            paras.append(f"We respectfully submit as follows: {expl}")
        else:
            paras.append("We are collecting the information needed to respond to this query. [TO BE CONFIRMED: final response after records are reviewed].")
    elif strat in (None, "OBTAIN_CLIENT_INFO", "ESCALATE_CA"):
        paras.append("[TO BE CONFIRMED: response to this query — strategy not yet finalised by CA]")
    elif strat == "REQUEST_TIME":
        paras.append("We are in the process of collating the information and documents called for in respect of this query "
                     "from its records and from third parties. It is respectfully requested that a reasonable time of "
                     "[TO BE CONFIRMED: number of days] days may kindly be granted to furnish the same.")
    elif strat == "SEEK_CLARIFICATION":
        paras.append("With respect, we seek clarification on the precise information sought under this query, namely "
                     "[TO BE CONFIRMED: specific point requiring clarification], so that a complete response may be furnished.")
    else:
        if expl and expl_ok:
            paras.append(f"In response to this query, we respectfully submit as under: {expl}")
        elif expl:
            paras.append(f"[TO BE CONFIRMED BY CLIENT: {expl}]")
        else:
            paras.append("In response to this query, we respectfully submit as under: [TO BE CONFIRMED: factual explanation "
                         "based only on verified records].")
    if factual_basis and position in ("TRUE", "PARTLY_TRUE", "FALSE") and i.get("category") != "UNSECURED_LOAN":
        paras.append(f"The factual position is that {factual_basis.rstrip('.')}.")
    if position in ("TRUE", "PARTLY_TRUE", "FALSE") and expl and expl_ok:
        paras.append(f"We further submit that {expl.rstrip('.')}.")
    if position in ("TRUE", "PARTLY_TRUE", "FALSE") and available_labels and i.get("category") != "UNSECURED_LOAN":
        paras.append("We rely on the following records, which support our explanation and the nature and source of the entries: "
                     + "; ".join(available_labels) + ".")
    for e in ev:
        if e["status"] in ("SUFFICIENT", "PARTIALLY_SUFFICIENT") and e["document_id"] in ann and e["requirement"] not in available:
            paras.append(f"A copy of the {e['requirement_label'][0].lower() + e['requirement_label'][1:]} is enclosed as Annexure {ann[e['document_id']]}." )
    for e in ev:
        if e["status"] == "SUFFICIENT":
            basis_map.append({"basis": "ESTABLISHED_BY_DOCUMENT", "statement": e.get("establishes") or e["requirement_label"],
                              "source": e.get("document_name") or "", "annexure": ann.get(e["document_id"])})
        elif e["status"] == "PARTIALLY_SUFFICIENT":
            basis_map.append({"basis": "PARTLY_SUPPORTED", "statement": e.get("establishes") or e["requirement_label"],
                              "not_established": e.get("does_not_establish"), "source": e.get("document_name") or "",
                              "annexure": ann.get(e["document_id"])})
    for e in ev:
        if e["status"] in ("SUFFICIENT", "PARTIALLY_SUFFICIENT") and e["document_id"] and e["document_id"] not in ann:
            basis_map.append({"basis": "DOCUMENT_NOT_MARKED_AS_ANNEXURE", "statement": e["requirement_label"],
                              "source": e.get("document_name") or ""})
    if expl:
        basis_map.append({"basis": "CLIENT_CONFIRMED" if expl_ok else "AWAITING_CLIENT_CONFIRMATION", "statement": expl})
    for label in available_labels:
        basis_map.append({"basis": "AVAILABLE_WITH_CA", "statement": label, "source": "CA confirmation"})
    legal_keys = a.get("legal_refs_selected") or []
    if legal_keys:
        refs = ", ".join(taxlaw.render_ref(k) for k in legal_keys)
        paras.append(f"Reference in this regard is invited to {refs}.")
    internal = []
    for pv in props or []:
        if pv["effective_status"] == "VERIFIED":
            cites = []
            for src in pv["sources"]:
                if src["stance"] == "SUPPORTS" and src["source_class"] == "PRIMARY" and src["effective_status"] == "VERIFIED":
                    pin = src.get("link_pinpoint") or src.get("pinpoint")
                    cites.append((src.get("citation") or src["title"]) + (f", {pin}" if pin else ""))
            paras.append(f"{pv['text'].rstrip('.')}. Reference in this regard is invited to {'; '.join(cites)}.")
        elif pv["effective_status"] != "REJECTED":
            internal.append(f"Proposition #{pv['id']} not included in reply — status {pv['effective_status']}: {pv['text'][:160]}")
    for e in ev:
        if e["status"] not in ("SUFFICIENT",):
            internal.append(f"{e['requirement_label']}: {e['status']}" + (f" — {e['inconsistency']}" if e.get("inconsistency") else ""))
    if i.get("strategy_reason"):
        internal.append(f"Strategy reason: {i['strategy_reason']}")
    if position:
        internal.append(f"CA factual assessment: {position}" + (f" — {a['concern_position_basis']}" if a.get("concern_position_basis") else ""))
    return {"issue_id": i["id"], "heading": head, "paragraphs": paras, "internal_notes": internal, "basis_map": basis_map}


def _ca_inputs(i: dict, ev: list[dict], ann: dict[int, str]) -> dict:
    """What the CA or client recorded for an issue (all optional): explanation, factual basis, strategy,
    selected provisions. Used on top of the record-based reply, or instead of it when no record matches."""
    a = i["analysis_json"] or {}
    expl = (a.get("client_explanation") or "").strip()
    expl_ok = bool(a.get("client_explanation_confirmed"))
    basis = (a.get("concern_position_basis") or "").strip()
    has_input = bool(expl or basis or a.get("concern_position") or i.get("strategy") in ("REQUEST_TIME", "SEEK_CLARIFICATION"))
    extra = []
    if basis:
        extra.append(f"The factual position is that {basis[0].lower() + basis[1:].rstrip('.')}.")
    if expl:
        extra.append(f"We further submit that {expl[0].lower() + expl[1:].rstrip('.')}." if expl_ok
                     else f"[TO BE CONFIRMED BY CLIENT: {expl}]")
    if i.get("strategy") == "REQUEST_TIME":
        extra.append("We are collating the remaining information called for under this query and respectfully request a "
                     "reasonable time of [TO BE CONFIRMED: number of days] days to furnish the same.")
    if i.get("strategy") == "SEEK_CLARIFICATION":
        extra.append("With respect, we seek clarification on [TO BE CONFIRMED: specific point requiring clarification], so that a "
                     "complete response may be furnished.")
    if a.get("legal_refs_selected"):
        extra.append("Reference in this regard is invited to " + ", ".join(taxlaw.render_ref(k) for k in a["legal_refs_selected"]) + ".")
    old = _issue_paragraph(i, ev, ann, None, {})
    paras = [p for p in old["paragraphs"] if not p.startswith("Reference in this regard")]
    return {"has_input": has_input, "extra": extra, "basis_map": old["basis_map"],
            "internal_notes": [n for n in old["internal_notes"]],
            "paragraphs": paras + [e for e in extra if e not in paras and not e.startswith("We further submit")]}


def _issue_prop_ids(issue_id: int) -> list[int]:
    with ro() as conn:
        return [r["id"] for r in conn.execute("SELECT id FROM propositions WHERE issue_id=? ORDER BY id", (issue_id,))]


def cited_propositions(content: dict) -> list[dict]:
    return [c for b in content.get("issues", []) for c in b.get("propositions_cited", [])]


def _doc_title(d: dict) -> str:
    first = next((ln.strip() for ln in (d.get("text") or "").splitlines() if len(ln.strip()) > 3), "") or d["original_name"]
    first = re.sub(r"(?i)^fictional\s+", "", first).strip()
    return first[:1].upper() + first[1:90]


def _signatory_from_notice(text: str) -> str | None:
    m = re.search(r"(?im)^\s*(?:proprietor|partner|director|managing partner|karta)\s*[|:]\s*([^|(\n]+)", text or "")
    return m.group(1).strip() if m else None


DEFAULT_OPTIONS = {"include_record_references": True, "include_legal_suggestions": False}


def build(user: dict, case_id: int, notice_id: int | None = None, *, reflect_reconciliation: bool = False,
          reconciliation_run_ids: list[int] | None = None, options: dict | None = None,
          ai_rows: dict[int, dict] | None = None, drafting_info: dict | None = None) -> dict:
    """Write a complete, point-wise reply from the notice's queries and the records mapped to them.

    Never blocked by a missing record or an unassessed issue: gaps are stated in one sentence and
    conflicts are marked for the CA. The single gate is the final CA review before export."""
    from . import mapping, reply_writer

    opts = {**DEFAULT_OPTIONS, **(options or {})}
    case = cases.get_case(user, case_id, include_pan=True)
    ns = notices.list_notices(user, case_id)
    n = next((x for x in ns if x["id"] == notice_id), None) if notice_id else (ns[-1] if ns else None)
    if notice_id and n is None:
        raise NotFound("Notice not found in this case.")
    p = n["particulars_json"] if n else {}
    law = (n or {}).get("applicable_law_json") or {}
    with ro() as conn:
        docs = {r["id"]: row_to_dict(r) for r in conn.execute(
            "SELECT d.id, d.original_name, d.annexure_label, d.is_annexure, d.doc_type, t.text FROM documents d "
            "LEFT JOIN doc_text t ON t.document_id=d.id WHERE d.case_id=?", (case_id,))}
    adocs = sorted([d for d in docs.values() if d["is_annexure"] and d["annexure_label"]], key=lambda d: str(d["annexure_label"]))
    notice_text = docs.get((n or {}).get("document_id"), {}).get("text") if n else ""
    reconciliation = []
    selected_runs = list(dict.fromkeys(reconciliation_run_ids or [])) if reflect_reconciliation else []
    if selected_runs:
        require_role(user, "ADMIN", "CA")
        with ro() as conn:
            sql_marks = ",".join("?" for _ in selected_runs)
            recon_rows = conn.execute(f"SELECT id,recon_type,result_json FROM recon_runs WHERE case_id=? AND id IN ({sql_marks})",
                                      [case_id, *selected_runs]).fetchall()
        if len(recon_rows) != len(selected_runs):
            raise ValidationError("Every selected reconciliation must belong to this case.")
        recon_names = {"BANK_VS_BOOK": "bank statement and bank book", "BANK_BOOK_VS_LEDGER": "bank book and ledger",
                       "SALES_VS_BANK": "sales records and bank credits", "AIS_VS_BOOKS": "AIS/26AS and books",
                       "DEBTORS_VS_RECEIPTS": "debtors and receipts", "CASH_CHRONOLOGY": "cash receipts and bank deposits",
                       "FS_TIE_OUT": "financial statements tie-out", "TRANSACTION_MATCH": "transaction records"}
        for row in recon_rows:
            result = json.loads(row["result_json"] or "{}")
            status = str(result.get("status") or "reviewed").replace("_", " ").lower()
            if result.get("matched_count") is not None:
                matched = result["matched_count"]
                unmatched = sum(len(v) for k, v in result.items() if k.startswith("unmatched_in_") and isinstance(v, list))
                status = f"{matched} matching entries and {unmatched} unmatched entries"
            elif result.get("failures") is not None:
                status = f"{result['failures']} of {result.get('deposits_tested', 0)} deposits did not pass the recorded consistency checks"
            label = recon_names.get(row["recon_type"], row["recon_type"].replace("_", " ").lower())
            reconciliation.append({"run_id": row["id"], "paragraph": f"The reconciliation of the {label} recorded {status}. "
                                  "The comparison is relied upon only to show consistency among the records for the items tested; "
                                  "the nature and source of each item are explained separately with the supporting records."})
    iss = issues.list_issues(user, case_id)
    if not iss:
        raise ValidationError("No issues yet — generate the issues from the notice first.")
    mapping.map_case(user, case_id)
    contra = mapping.contradictions(user, case_id)
    fy = mapping._fy_start(case.get("assessment_year") or (p.get("assessment_year") or {}).get("value"))
    issue_blocks = []
    evidence_rows = evidence.matrix(user, case_id)
    ann = {d["id"]: d["annexure_label"] for d in adocs}
    ai_rows = ai_rows or {}
    for i in iss:
        links = mapping.links_for_issue(user, i["id"])
        recs = mapping.record_status(i, links, [c for c in contra if c.get("issue_id") == i["id"]])
        blk = reply_writer.write_issue(i, links, docs, fy, opts, contra, recs)
        ca_blk = _ca_inputs(i, [dict(e, requirement_label=e.get("requirement_label") or e["requirement"])
                                for e in evidence_rows if e["issue_id"] == i["id"]], ann)
        ai = ai_rows.get(i["id"])
        if ai:
            blk["paragraphs"] = list(ai["paragraphs"])
            blk["drafted_by"] = "AI"
            blk["ai"] = {"id": ai["id"], "provider": ai["provider"], "model": ai["model"], "sources": ai["sources"],
                         "checks": ai["checks"]}
            blk["review_points"] = blk["review_points"] + [c["message"] for c in ai["checks"]]
        else:
            if blk["documents_used"]:
                blk["paragraphs"] = blk["paragraphs"] + [e for e in ca_blk["extra"]]
            else:
                blk["paragraphs"] = reply_writer.template_opening(i, ca_blk)
                blk["drafted_by"] = "TEMPLATE"
            blk["paragraphs"] += blk["availability"]
        # documents the CA selected for enclosure that relate to this query (by content match or evidence link)
        related = {l["document_id"] for l in links if l["status"] != "REJECTED"} | \
                  {e["document_id"] for e in evidence_rows if e["issue_id"] == i["id"] and e.get("document_id")}
        body_txt = " ".join(blk["paragraphs"])
        for did in sorted(related):
            dd = docs.get(did)
            if dd and dd["is_annexure"] and dd["annexure_label"] and f"Annexure {dd['annexure_label']}" not in body_txt:
                t = _doc_title(dd)
                t = t[0].lower() + t[1:] if len(t) > 1 and t[1].islower() else t
                blk["paragraphs"].append(f"A copy of our {t} is enclosed as Annexure {dd['annexure_label']}.")
        blk["records"] = recs
        blk["basis_map"] = ca_blk["basis_map"]
        blk["internal_notes"] = blk["internal_notes"] + ca_blk["internal_notes"]
        if opts["include_record_references"] and blk["documents_used"]:
            names = [_doc_title(docs[d]) + (f" (Annexure {docs[d]['annexure_label']})" if docs[d]["is_annexure"] and docs[d]["annexure_label"] else "")
                     for d in blk["documents_used"] if d in docs]
            blk["paragraphs"].append("Records relied on for this query: " + "; ".join(names) + ".")
        props = [authorities.proposition_view(user, pid) for pid in _issue_prop_ids(i["id"])]
        for pv in props:  # only CA-verified legal points go into the reply as submissions
            if pv["effective_status"] == "VERIFIED":
                cites = [(src.get("citation") or src["title"]) + (f", {src.get('link_pinpoint') or src.get('pinpoint')}"
                                                                  if (src.get("link_pinpoint") or src.get("pinpoint")) else "")
                         for src in pv["sources"] if src["stance"] == "SUPPORTS" and src["source_class"] == "PRIMARY"
                         and src["effective_status"] == "VERIFIED"]
                blk["paragraphs"].append(f"{pv['text'].rstrip('.')}. Reference in this regard is invited to {'; '.join(cites)}.")
        if opts["include_legal_suggestions"]:
            cand = (i.get("analysis_json") or {}).get("candidate_provisions_to_examine") or []
            if cand:
                labels = ", ".join(taxlaw.render_ref(k) for k in cand)
                blk["paragraphs"].append(f"[CA REVIEW: suggested legal points to consider — {labels}. Keep, edit or delete "
                                         "after reading the source; nothing here has been verified.]")
        blk["propositions_cited"] = [{"id": pv["id"], "verified_hash": pv["verified_hash"]} for pv in props
                                     if pv["effective_status"] == "VERIFIED"]
        issue_blocks.append(blk)
    act = law.get("substantive_law")
    if not act:
        year = case.get("assessment_year") or p.get("assessment_year", {}).get("value")
        if year and year != NP:
            try:
                act = taxlaw.determine_applicable_law(year, "AY", p.get("date_of_issue", {}).get("value"))[
                    "substantive_law"]
            except ValidationError:
                act = None
    act = act or "[TO BE CONFIRMED: applicable Act]"
    sec = _v(p, "section")
    ay = case.get("assessment_year") or _v(p, "assessment_year")
    issued = _v(p, "date_of_issue")
    try:
        from datetime import date as _date

        _d = _date.fromisoformat(issued)
        issued = f"{_d.day} {_d.strftime('%B %Y')}"
    except (TypeError, ValueError):
        pass
    nno = (p.get("notice_number") or {}).get("value")
    din = (p.get("din") or {}).get("value")
    signatory = _signatory_from_notice(notice_text or "")
    designation = "Proprietor" if re.search(r"(?i)proprietor", notice_text or "") else "Authorised Signatory"
    content = {
        "to_from": {"to": _v(p, "issuing_authority"),
                    "from": f"{case['assessee_name']} (PAN: {{{{PAN}}}})"},
        "subject": f"Submission in response to notice under section {sec} of the {act} for Assessment Year {ay}",
        "reference": "; ".join(x for x in [f"Notice No. {nno}" if nno and nno != NP else "",
                                            f"DIN {din}" if din and din != NP else "", f"dated {issued}"] if x) + ".",
        "background": (f"We refer to the notice under section {sec} dated {issued}, calling for information and records in "
                       f"connection with our assessment for Assessment Year {ay}. We have examined each of the matters raised "
                       "with reference to our books of account and supporting records, and respectfully submit our point-wise "
                       "reply below."),
        "preliminary": "Our submissions on each query are as follows:",
        "issues": issue_blocks,
        "legal": [],
        "reconciliation": reconciliation,
        "annexures": [{"label": d["annexure_label"], "description": _doc_title(d), "doc_type": d["doc_type"]} for d in adocs],
        "prayer": ("In view of the facts and records set out above, we respectfully request that the explanations furnished be "
                   "accepted and that the matters raised be treated as satisfactorily explained. We shall be glad to furnish any "
                   "further information or clarification that may be required, and request an opportunity of being heard before "
                   "any adverse view is taken."),
        "signature": {"for": case["assessee_name"], "name": signatory or "[TO BE CONFIRMED: authorised signatory / representative]",
                      "designation": designation, "pan": "{{PAN}}",
                      "date": "[TO BE CONFIRMED: date]", "place": "[TO BE CONFIRMED: place]"},
        "_meta": {"notice_id": n["id"] if n else None, "applicable_law_flags": law.get("flags", []),
                  "deadline_verified": bool(n and n["deadline_verified"]), "options": opts,
                  "reflect_reconciliation": bool(selected_runs), "reconciliation_run_ids": selected_runs,
                  "review_points": [{"issue": b["heading"], "point": r} for b in issue_blocks for r in b["review_points"]],
                  "contradictions": contra,
                  "drafting": {**(drafting_info or {"mode": "NO_AI", "label": "Written from your records without AI"}),
                               "by_issue": {str(b["issue_id"]): b["drafted_by"] for b in issue_blocks},
                               "basic_template_queries": [int(b["heading"].split()[2]) for b in issue_blocks
                                                          if b["drafted_by"] in ("TEMPLATE", "BASIC")]},
                  "label": "WORKING DRAFT — FOR CA REVIEW AND APPROVAL"},
    }
    if n and not n["deadline_verified"]:
        content["_meta"]["warnings"] = ["Compliance deadline not verified."]
    return _save_version(user, case_id, content, "DRAFT_GENERATED")


def _hash(content: dict) -> str:
    c = {k: v for k, v in content.items() if k != "_meta"}
    c["issues"] = [{k: v for k, v in b.items() if k != "basis_map"} for b in c.get("issues", [])]
    return sha256_text(dumps(c))


def _save_version(user: dict, case_id: int, content: dict, event: str) -> dict:
    h = _hash(content)
    with tx() as conn:
        ver = conn.execute("SELECT COALESCE(MAX(version),0)+1 FROM drafts WHERE case_id=?", (case_id,)).fetchone()[0]
        cur = conn.execute("INSERT INTO drafts(case_id,version,content_json,content_hash,created_by,created_at) VALUES (?,?,?,?,?,?)",
                           (case_id, ver, dumps(content), h, user["id"], utcnow()))
        did = cur.lastrowid
        cases.touch(conn, case_id)
        audit.log_event(conn, event, user_id=user["id"], case_id=case_id, meta={"draft_id": did, "version": ver, "content_hash": h})
    return get_draft(user, did)


def get_draft(user: dict, draft_id: int) -> dict:
    with ro() as conn:
        r = conn.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
    if not r:
        raise NotFound("Draft not found.")
    d = row_to_dict(r, ("content_json",))
    cases.check_access(user, d["case_id"])
    d["unresolved_placeholders"] = placeholders(d["content_json"])
    return d


def latest_draft(user: dict, case_id: int) -> dict | None:
    cases.check_access(user, case_id)
    with ro() as conn:
        r = conn.execute("SELECT id FROM drafts WHERE case_id=? ORDER BY version DESC LIMIT 1", (case_id,)).fetchone()
    return get_draft(user, r["id"]) if r else None


def list_drafts(user: dict, case_id: int) -> list[dict]:
    cases.check_access(user, case_id)
    with ro() as conn:
        rows = conn.execute("SELECT id, version, content_hash, created_by, created_at FROM drafts WHERE case_id=? ORDER BY version DESC",
                            (case_id,)).fetchall()
    return [dict(r) for r in rows]


_TEXT_SECTIONS = {"subject", "reference", "background", "preliminary", "prayer"}


def edit(user: dict, draft_id: int, updates: dict) -> dict:
    """updates: {"background": str, ..., "to_from": {...}, "signature": {...},
    "issues": {issue_id: [paragraphs]}, "legal": [paragraphs]}"""
    require_role(user, "ADMIN", "CA")
    d = get_draft(user, draft_id)
    c = d["content_json"]
    for k, v in updates.items():
        if k in _TEXT_SECTIONS:
            if not isinstance(v, str) or len(v) > 20000:
                raise ValidationError(f"{k} must be text ≤ 20000 chars.")
            c[k] = v
        elif k in ("to_from", "signature"):
            if not isinstance(v, dict):
                raise ValidationError(f"{k} must be an object.")
            c[k].update({kk: str(vv)[:500] for kk, vv in v.items() if kk in c[k]})
        elif k == "issues":
            for blk in c["issues"]:
                new = v.get(str(blk["issue_id"])) or v.get(blk["issue_id"])
                if new is not None:
                    if not isinstance(new, list) or not all(isinstance(x, str) for x in new):
                        raise ValidationError("Issue paragraphs must be a list of strings.")
                    blk["paragraphs"] = new
        elif k == "legal":
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                raise ValidationError("legal must be a list of strings.")
            c["legal"] = v
        else:
            raise ValidationError(f"Section {k} is not editable.")
    return _save_version(user, d["case_id"], c, "DRAFT_EDITED")


def placeholders(content: dict) -> list[str]:
    found: list[str] = []

    def walk(x, key=""):
        if key in ("_meta", "internal_notes", "basis_map", "records", "ai", "availability", "review_points", "query"):
            return
        if isinstance(x, str):
            found.extend(PLACEHOLDER_RX.findall(x))
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(v, k)
        elif isinstance(x, list):
            for v in x:
                walk(v, key)

    walk(content)
    return found


def _fill_pan(content: dict, pan_value: str) -> dict:
    import copy

    c = copy.deepcopy(content)
    c["to_from"]["from"] = c["to_from"]["from"].replace("{{PAN}}", pan_value)
    c["signature"]["pan"] = c["signature"].get("pan", "").replace("{{PAN}}", pan_value)
    return c


_SUB_RX = re.compile(r"^\(([a-z]{1,2}|[ivx]{1,4})\)\s")


def _sections_after_issues(content: dict) -> list[tuple[str, list[str]]]:
    out = []
    if content.get("reconciliation"):
        out.append(("Reconciliations considered", [r["paragraph"] for r in content["reconciliation"]]))
    if content.get("legal"):
        out.append(("Legal submissions", list(content["legal"])))
    out.append(("Prayer", [content["prayer"]]))
    return out


def render_text(content: dict, *, approved: bool, pan_value: str = "[masked]") -> str:
    content = _fill_pan(content, pan_value)
    out = []
    if not approved:
        out += ["*** DRAFT – NOT APPROVED – NOT FOR SUBMISSION ***", ""]
    out += ["To,", content["to_from"]["to"], "", "From,", content["to_from"]["from"], "",
            f"Subject: {content['subject']}", f"Reference: {content['reference']}", "", "Respected Sir/Madam,", "",
            content["background"], "", content["preliminary"], ""]
    for b in content["issues"]:
        out.append(b["heading"])
        if b.get("query"):
            out.append(f"Query: {b['query']}")
        out.append("Our reply:")
        out += [("      " if _SUB_RX.match(p) else "  ") + p for p in b["paragraphs"]]
        out.append("")
    for head, paras in _sections_after_issues(content):
        out.append(head)
        out += [f"  {p}" for p in paras]
        out.append("")
    if content["annexures"]:
        out.append("Index of Annexures")
        out += [f"  Annexure {a['label']}: {a['description']}" for a in content["annexures"]]
        out.append("")
    s = content["signature"]
    out += ["Yours faithfully,", "", f"For {s['for']}", "", s["name"], s["designation"], f"PAN: {s['pan']}",
            f"Date: {s['date']}", f"Place: {s['place']}"]
    if content["annexures"]:
        out += ["", "Enclosures: As per the index of annexures above."]
    return "\n".join(out)


def render_docx(content: dict, *, approved: bool, pan_value: str = "[masked]", include_draft_banner: bool = True) -> bytes:
    """An editable Word reply: A4, Times New Roman 12, justified, numbered queries with lettered sub-points."""
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt

    content = _fill_pan(content, pan_value)
    doc = docx.Document()
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.left_margin = sec.right_margin = Cm(2.5)
    sec.top_margin = sec.bottom_margin = Cm(2.2)
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(12)
    st.paragraph_format.space_after = Pt(6)

    def para(text: str = "", *, bold: bool = False, italic: bool = False, indent: float = 0.0, justify: bool = True,
             align_right: bool = False):
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.bold, r.italic = bold, italic
        if indent:
            p.paragraph_format.left_indent = Cm(indent)
        if align_right:
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        elif justify:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        return p

    if not approved and include_draft_banner:
        para("DRAFT – FOR CA REVIEW – NOT FOR SUBMISSION", bold=True, justify=False)
    para("To,", justify=False)
    for line in str(content["to_from"]["to"]).split("\n"):
        para(line, justify=False)
    para("")
    para("From,", justify=False)
    para(content["to_from"]["from"], justify=False)
    p = para(justify=False)
    p.add_run("Subject: ").bold = True
    p.add_run(content["subject"])
    p = para(justify=False)
    p.add_run("Reference: ").bold = True
    p.add_run(content["reference"])
    para("Respected Sir/Madam,", justify=False)
    para(content["background"])
    para(content["preliminary"])
    for b in content["issues"]:
        para(b["heading"], bold=True, justify=False)
        if b.get("query"):
            para(b["query"], italic=True, indent=0.6)
        para("Our reply:", bold=True, justify=False)
        for t in b["paragraphs"]:
            para(t, indent=1.2 if _SUB_RX.match(t) else 0.6)
    for head, paras in _sections_after_issues(content):
        para(head, bold=True, justify=False)
        for t in paras:
            para(t, indent=0.6)
    if content["annexures"]:
        para("Index of Annexures", bold=True, justify=False)
        t = doc.add_table(rows=1, cols=2)
        t.style = "Table Grid"
        t.rows[0].cells[0].text, t.rows[0].cells[1].text = "Annexure", "Description"
        for a in content["annexures"]:
            row = t.add_row().cells
            row[0].text, row[1].text = str(a["label"]), a["description"]
    s = content["signature"]
    para("")
    para("Yours faithfully,", justify=False)
    para(f"For {s['for']}", justify=False)
    para("")
    for line in (s["name"], s["designation"], f"PAN: {s['pan']}", f"Date: {s['date']}", f"Place: {s['place']}"):
        para(line, justify=False)
    if content["annexures"]:
        para("Enclosures: As per the index of annexures above.", justify=False)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def select_legal_refs(user: dict, issue_id: int, ref_keys: list[str]) -> dict:
    for k in ref_keys:
        taxlaw.get_ref(k)  # raises if missing
    i = issues.get_issue(user, issue_id)
    a = i["analysis_json"]
    a["legal_refs_selected"] = ref_keys
    with tx() as conn:
        conn.execute("UPDATE issues SET analysis_json=?, updated_at=? WHERE id=?", (dumps(a), utcnow(), issue_id))
        audit.log_event(conn, "LEGAL_REFS_SELECTED", user_id=user["id"], case_id=i["case_id"], meta={"issue_id": issue_id, "refs": ref_keys})
    return issues.get_issue(user, issue_id)


def _pdf_font():
    """Register a TTF font that has the ₹ glyph if one is available; else Helvetica (₹ → 'Rs.')."""
    from pathlib import Path

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/Nirmala.ttf", "C:/Windows/Fonts/arial.ttf",
                  "/Library/Fonts/Arial Unicode.ttf", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"]
    for c in candidates:
        if Path(c).exists():
            try:
                pdfmetrics.registerFont(TTFont("NMFont", c))
                return "NMFont", True
            except Exception:
                continue
    return "Helvetica", False


def render_pdf(content: dict, *, approved: bool, pan_value: str = "[masked]") -> bytes:
    from xml.sax.saxutils import escape

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font, rupee = _pdf_font()
    fix = (lambda t: t) if rupee else (lambda t: t.replace("₹", "Rs. "))
    st = ParagraphStyle("b", fontName=font, fontSize=11, leading=15, spaceAfter=6)
    h = ParagraphStyle("h", parent=st, fontSize=12, spaceBefore=8)
    c = _fill_pan(content, pan_value)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=22 * mm, rightMargin=22 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
    P = lambda t, s=st: Paragraph(escape(fix(t)).replace("\n", "<br/>"), s)
    flow = []
    if not approved:
        flow.append(P("DRAFT – NOT APPROVED – NOT FOR SUBMISSION", h))
    flow += [P("To,"), P(c["to_from"]["to"]), P("From,"), P(c["to_from"]["from"]), Spacer(1, 6),
             P("Subject: " + c["subject"], h), P("Reference: " + c["reference"]), P("Respected Sir/Madam,"),
             P("1. Background", h), P(c["background"]), P("2. Preliminary submission", h), P(c["preliminary"]),
             P("3. Issue-wise submissions", h)]
    for n, b in enumerate(c["issues"], 1):
        flow.append(P(f"3.{n} {b['heading']}", h))
        flow += [P(x) for x in b["paragraphs"]]
    if c.get("reconciliation"):
        flow.append(P("4. Reconciliation considered", h))
        flow += [P(item["paragraph"]) for item in c["reconciliation"]]
    if c.get("legal"):
        flow.append(P(f"{5 if c.get('reconciliation') else 4}. Legal submissions", h))
        flow += [P(x) for x in c["legal"]]
    prayer_no = 6 if c.get("reconciliation") and c.get("legal") else 5 if c.get("reconciliation") or c.get("legal") else 4
    flow += [P(f"{prayer_no}. Prayer", h), P(c["prayer"])]
    if c["annexures"]:
        flow.append(P("Index of Annexures", h))
        t = Table([["Annexure", "Description"]] + [[a["label"], fix(a["description"])] for a in c["annexures"]], colWidths=[30 * mm, 130 * mm])
        t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font), ("GRID", (0, 0), (-1, -1), 0.5, "#888888"),
                               ("BACKGROUND", (0, 0), (-1, 0), "#E8ECF2")]))
        flow.append(t)
    s_ = c["signature"]
    flow += [Spacer(1, 12), P("Yours faithfully,"), P(f"For {s_['for']}"), Spacer(1, 18), P(s_["name"]), P(s_["designation"]),
             P(f"Date: {s_['date']}"), P(f"Place: {s_['place']}")]
    doc.build(flow)
    return buf.getvalue()


def diff_versions(user: dict, draft_a: int, draft_b: int) -> dict:
    import difflib

    a, b = get_draft(user, draft_a), get_draft(user, draft_b)
    if a["case_id"] != b["case_id"]:
        raise ValidationError("Drafts belong to different cases.")
    ta = render_text(a["content_json"], approved=False).splitlines()
    tb = render_text(b["content_json"], approved=False).splitlines()
    lines = list(difflib.unified_diff(ta, tb, f"v{a['version']}", f"v{b['version']}", lineterm="", n=1))
    return {"from_version": a["version"], "to_version": b["version"], "diff": lines,
            "changed": bool(lines), "added": sum(1 for l in lines if l.startswith("+") and not l.startswith("+++")),
            "removed": sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))}


def annexure_index(user: dict, case_id: int) -> list[dict]:
    cases.check_access(user, case_id)
    with ro() as conn:
        docs = conn.execute("SELECT id, original_name, doc_type, sha256, annexure_label FROM documents WHERE case_id=? AND is_annexure=1 "
                            "ORDER BY annexure_label", (case_id,)).fetchall()
        links = conn.execute("SELECT e.document_id, i.seq, e.requirement, e.status FROM evidence_items e JOIN issues i ON i.id=e.issue_id "
                             "WHERE e.case_id=? AND e.document_id IS NOT NULL", (case_id,)).fetchall()
    out = []
    for d in docs:
        rel = [l for l in links if l["document_id"] == d["id"]]
        out.append({"label": d["annexure_label"], "description": d["original_name"], "doc_type": d["doc_type"],
                    "sha256_prefix": d["sha256"][:12],
                    "relevant_queries": sorted({f"Q{l['seq']}" for l in rel}),
                    "evidence_status": sorted({l["status"] for l in rel}) or ["NOT LINKED TO ANY QUERY"]})
    return out
