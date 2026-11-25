"""One consolidated end-to-end run over the fictional PQR Traders case, plus
security checks. Uses the services layer directly (same code the API calls)."""
import csv

import pytest

from noticemate.core import audit
from noticemate.core.db import ro, tx
from noticemate.core.errors import AuthError, PermissionDenied, PrivacyBlocked, ValidationError, Conflict
from noticemate.services import (ai_gateway, auth, cases, documents, drafting, evidence, info_request, issues, notices,
                                 reconciliation, review, taxcalc, taxlaw)

from .conftest import ROOT, sample


@pytest.fixture(scope="module")
def ctx(users):
    ca, staff = users["ca"], users["staff"]
    case = cases.create_case(ca, case_ref="PQR-2026-27", assessee_name="PQR Traders", assessee_category="FIRM",
                             pan="AAAFP1234Z", assessment_year="2026-27",
                             party_names=["Rahul Sharma", "Neeraj Gupta", "Amit Verma"])
    cases.add_member(ca, case["id"], staff["id"])
    up = {}
    for name in ("notice_143_2_PQR.docx", "notice_143_2_PQR_scanned.pdf", "bank_statement_PQR.xlsx", "bank_book_PQR.xlsx",
                 "cash_book_PQR.xlsx", "sales_ledger_PQR.xlsx"):
        up[name] = documents.upload(staff, case["id"], name, sample(name))
    return {"case": case, "docs": up, **users}


def test_upload_classification_and_ocr(ctx):
    d = ctx["docs"]
    assert d["notice_143_2_PQR.docx"]["doc_type"] == "NOTICE"
    assert d["bank_statement_PQR.xlsx"]["doc_type"] == "BANK_STATEMENT"
    assert d["cash_book_PQR.xlsx"]["doc_type"] == "CASH_BOOK"
    scanned = d["notice_143_2_PQR_scanned.pdf"]
    assert scanned["extraction_status"] in ("OCR", "PARTIAL")
    txt = documents.get_text(ctx["staff"], scanned["id"])["text"]
    assert "143(2)" in txt or "cash deposits" in txt.lower()
    with pytest.raises(Conflict):
        documents.upload(ctx["staff"], ctx["case"]["id"], "again.xlsx", sample("cash_book_PQR.xlsx"))


def test_access_control(ctx):
    with pytest.raises(PermissionDenied):
        cases.get_case(ctx["outsider"], ctx["case"]["id"])
    with pytest.raises(PermissionDenied):
        documents.get_text(ctx["outsider"], ctx["docs"]["notice_143_2_PQR.docx"]["id"])
    assert "pan" not in cases.get_case(ctx["staff"], ctx["case"]["id"])


def test_full_workflow(ctx):
    ca, staff, cid, d = ctx["ca"], ctx["staff"], ctx["case"]["id"], ctx["docs"]

    # Module 4 — notice particulars
    n = notices.create_from_document(staff, d["notice_143_2_PQR.docx"]["id"])
    p = n["particulars_json"]
    assert p["section"]["value"] == "143(2)"
    assert p["assessment_year"]["value"] == "2026-27"
    assert p["compliance_deadline"]["value"] == "2026-11-25" and p["compliance_deadline"]["needs_verification"]
    assert p["din"]["value"].startswith("ITBA/AST/S/143(2)")
    assert p["scrutiny_scope"]["value"] == "LIMITED"
    assert n["applicable_law_json"]["substantive_law"] == "Income-tax Act, 1961"
    assert not n["deadline_verified"]

    # Module 5 — issues
    iss = issues.generate_from_notice(staff, n["id"])
    assert len(iss) == 5
    cats = [i["category"] for i in iss]
    assert cats[0] == "CASH_DEPOSITS" and cats[1] == "UNSECURED_LOAN" and cats[4] == "CAPITAL_CONTRIBUTION"
    assert iss[0]["amount"] == 1800000

    # Module 6 — evidence auto-map never marks SUFFICIENT
    mat = evidence.matrix(staff, cid)
    assert mat and all(m["status"] in ("REQUIRES_VERIFICATION", "NOT_PROVIDED") for m in mat)
    bank_ev = next(m for m in mat if m["issue_id"] == iss[0]["id"] and m["requirement"] == "bank_statement")
    with pytest.raises(ValidationError):  # must explain why
        evidence.assess(staff, bank_ev["id"], status="SUFFICIENT")
    evidence.assess(staff, bank_ev["id"], status="SUFFICIENT", establishes="Five cash deposits totalling ₹18,00,000 credited.",
                    does_not_establish="Source of the cash deposited.")

    # Module 7 — reconciliation
    bb = reconciliation.run_bank_vs_book(staff, cid, d["bank_statement_PQR.xlsx"]["id"], d["bank_book_PQR.xlsx"]["id"])
    assert bb["statement_credits_total"] == 2800000
    assert bb["book_receipts_total"] == 3000000
    assert bb["duplicate_total"] == 200000 and bb["corrected_book_total"] == 2800000
    assert bb["probable_duplicate_book_postings"][0]["ref"] == "NEFT25071502"
    assert bb["credit_classification"]["by_mode"]["CASH_DEPOSIT"]["total"] == 1800000

    with open(ROOT / "sample_data" / "source_mapping_PQR.csv", encoding="utf-8") as fh:
        mapping = [dict(r, amount=float(r["amount"])) for r in csv.DictReader(fh)]
    ch = reconciliation.run_cash_chronology(staff, cid, d["cash_book_PQR.xlsx"]["id"], d["bank_statement_PQR.xlsx"]["id"], 0.0, mapping)
    assert ch["deposits_tested"] == 5 and ch["failures"] == 0
    flags = ch["cash_mode_flags"]["flags"]
    assert any(f["amount"] == 225000 for f in flags)          # s.269ST prompt
    assert any("Partner" in f["narration"] for f in flags)     # capital in cash prompt

    lc = reconciliation.run_ledger_compare(staff, cid, d["cash_book_PQR.xlsx"]["id"], d["sales_ledger_PQR.xlsx"]["id"],
                                           "cash_book", "sales_ledger", "cash sale", "cash sale")
    assert lc["total_cash_book"] == 1100000 and lc["total_sales_ledger"] == 950000 and lc["difference"] == 150000
    assert {x["date"] for x in lc["date_wise_differences"]} == {"2025-11-14", "2026-02-18"}

    # Module 8 — tax simulation (illustrative)
    sim = taxcalc.simulate(staff, cid, assessment_year="2026-27", assessee_category="FIRM", returned_income=None,
                           additions=[{"label": "Cash-sales difference (illustrative)", "amount": 150000, "issue_id": iss[3]["id"]}])
    b = next(s for s in sim["scenarios"] if s["key"] == "B")
    c = next(s for s in sim["scenarios"] if s["key"] == "C")
    assert b["incremental_tax"] == 46800          # 1.5L × 30% × 1.04
    assert c["incremental_tax"] == 117000         # 1.5L × 60% × 1.25 × 1.04
    assert "NOT A TAX DEMAND" in sim["label"] and sim["exclusions"] and sim["assumptions"]
    with pytest.raises(ValidationError):  # double counting guard
        taxcalc.simulate(staff, cid, assessment_year="2026-27", assessee_category="FIRM", returned_income=0,
                         additions=[{"label": "a", "amount": 1, "issue_id": 1}, {"label": "b", "amount": 1, "issue_id": 1}])

    # Module 9 — client request excludes SUFFICIENT items
    for i in iss:
        issues.update_analysis(ca, i["id"], {"concern_position": "NEED_CLIENT_INFO"})
    req = info_request.generate(staff, cid)
    q1 = next(s for s in req["sections"] if s["issue_seq"] == 1)
    assert all(r["evidence_id"] != bank_ev["id"] for r in q1["requests"])
    assert "Please" in info_request.as_text(req)

    # Module 10 — draft: no annexure claimed until marked; unverified law → placeholder
    for i in iss:
        issues.set_strategy(staff, i["id"], "DISPUTE_FACTUAL", "Evidence available; respond factually subject to CA review.")
    drafting.select_legal_refs(staff, iss[0]["id"], ["IT1961_S68"])
    dr = drafting.build(staff, cid, n["id"])
    text = drafting.render_text(dr["content_json"], approved=False)
    assert "Annexure" not in text.split("Index of Annexures")[0]
    assert "REQUIRES CA VERIFICATION" in text
    assert "DRAFT – NOT APPROVED" in text
    assert "AAAFP1234Z" not in review.preview(staff, dr["id"])
    documents.set_annexure(staff, d["bank_statement_PQR.xlsx"]["id"], True, "A")
    dr = drafting.build(staff, cid, n["id"])
    assert "enclosed as Annexure A" in drafting.render_text(dr["content_json"], approved=False)

    # Module 11 — approval gates
    with pytest.raises(PermissionDenied):
        review.approve(staff, dr["id"], declaration_accepted=True)
    with pytest.raises(PermissionDenied):
        review.export(ca, cid)
    for k, _ in review.CHECKLIST:
        review.tick(ca, dr["id"], k, True)
    with pytest.raises(ValidationError) as e:
        review.approve(ca, dr["id"], declaration_accepted=True)
    assert "placeholders" in e.value.message.lower()

    # CA resolves placeholders, verifies law & deadline
    taxlaw.verify_ref(ca, "IT1961_S68", "https://incometaxindia.gov.in")
    c = dr["content_json"]
    edits = {"background": "The assessee is a partnership firm engaged in trading (fictional test).",
             "issues": {str(b["issue_id"]): ["Response settled by CA (fictional test)."] for b in c["issues"]},
             "to_from": {"to": "National Faceless Assessment Centre"},
             "reference": "Notice No./DIN: ITBA/AST/S/143(2)/2026-27/1000000001(1); dated 2026-11-10.",
             "subject": "Submission in response to notice under section 143(2) of the Income-tax Act, 1961 for AY 2026-27",
             "signature": {"name": "Authorised Partner", "designation": "Partner", "date": "24-11-2026", "place": "Test City"}}
    dr2 = drafting.edit(ctx["admin"], dr["id"], edits)
    assert dr2["version"] == dr["version"] + 1 and not dr2["unresolved_placeholders"], dr2["unresolved_placeholders"]
    for k, _ in review.CHECKLIST:
        review.tick(ca, dr2["id"], k, True)
    with pytest.raises(ValidationError):  # deadline not verified
        review.approve(ca, dr2["id"], declaration_accepted=True)
    notices.verify_deadline(ca, n["id"], "2026-11-25", "e-proceedings portal (fictional test)")
    with pytest.raises(ValidationError):
        review.approve(ca, dr2["id"], declaration_accepted=False)
    st = review.approve(ca, dr2["id"], declaration_accepted=True)
    assert st["approved"]
    name, data = review.export(ca, cid)
    assert name.endswith(".docx") and data[:2] == b"PK"
    import docx, io
    full = "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs)
    assert "DRAFT – NOT APPROVED" not in full and "AAAFP1234Z" in full

    # editing after approval invalidates it
    drafting.edit(ctx["admin"], dr2["id"], {"prayer": dr2["content_json"]["prayer"] + " "})
    assert not review.approval_status(ca, cid)["approved"]
    with pytest.raises(PermissionDenied):
        review.export(ca, cid)


def test_ai_gateway_privacy(ctx):
    staff, cid = ctx["staff"], ctx["case"]["id"]
    sub = ai_gateway.prepare(staff, cid, "ISSUE_ANALYSIS",
                             "PQR Traders (PAN AAAFP1234Z) received Rs. 1,50,000 from Amit Verma, phone 9876543210.")
    assert sub["status"] == "PENDING_APPROVAL"
    payload = str(sub["exact_payload_preview"])
    for leak in ("AAAFP1234Z", "Amit Verma", "PQR Traders", "9876543210"):
        assert leak not in payload
    assert "1,50,000" in payload
    with pytest.raises(PrivacyBlocked):
        ai_gateway.approve_and_send(staff, sub["id"], sub["payload_hash"], confirm=False)
    with pytest.raises(PrivacyBlocked):
        ai_gateway.approve_and_send(staff, sub["id"], "0" * 64, confirm=True)
    with pytest.raises(PermissionDenied):
        ai_gateway.approve_and_send(ctx["outsider"], sub["id"], sub["payload_hash"], confirm=True)
    sent = ai_gateway.approve_and_send(staff, sub["id"], sub["payload_hash"], confirm=True)
    assert sent["status"] == "SENT" and sent["exact_payload_preview"] is None  # payload wiped
    assert "NOT A PROFESSIONAL OPINION" in sent["response_label"]
    with pytest.raises(PrivacyBlocked):  # cannot resend
        ai_gateway.approve_and_send(staff, sub["id"], sub["payload_hash"], confirm=True)

    # residual PII → BLOCKED: a name added to redaction terms after prepare is caught at send time
    sub2 = ai_gateway.prepare(staff, cid, "SUMMARISE_NOTICE", "Payment from Mr Kapoor received.")
    cases.update_party_names(ctx["ca"], cid, ["Rahul Sharma", "Neeraj Gupta", "Amit Verma", "Kapoor"])
    with pytest.raises(PrivacyBlocked):
        ai_gateway.approve_and_send(staff, sub2["id"], sub2["payload_hash"], confirm=True)
    assert ai_gateway.get_submission(staff, sub2["id"])["status"] == "BLOCKED"

    # audit log holds no content
    with ro() as conn:
        rows = [r["meta_json"] for r in conn.execute("SELECT meta_json FROM audit_log")]
    blob = " ".join(rows)
    for leak in ("AAAFP1234Z", "9876543210", "Amit Verma received"):
        assert leak not in blob


def test_ai_disabled_for_real_provider(ctx, monkeypatch):
    from noticemate.core.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "ai_provider", "anthropic")
    monkeypatch.setattr(s, "ai_enabled", False)
    sub = ai_gateway.prepare(ctx["staff"], ctx["case"]["id"], "SUMMARISE_NOTICE", "Notice text without identifiers.")
    with pytest.raises(PermissionDenied) as e:
        ai_gateway.approve_and_send(ctx["staff"], sub["id"], sub["payload_hash"], confirm=True)
    assert "does NOT include" in e.value.message


def test_auth_lockout_and_audit_chain(ctx):
    auth.create_user("lockme", "Lock Me", "STAFF", "Lock!Me12345", actor_id=ctx["admin"]["id"])
    for _ in range(5):
        with pytest.raises(AuthError):
            auth.login("lockme", "wrong")
    with pytest.raises(AuthError) as e:
        auth.login("lockme", "Lock!Me12345")
    assert "locked" in e.value.message.lower()
    tok = auth.login("staff1", "Staff!Pass123")["token"]
    assert auth.authenticate(tok)["username"] == "staff1"
    auth.logout(tok)
    with pytest.raises(AuthError):
        auth.authenticate(tok)
    assert audit.verify_chain()["valid"]
    with pytest.raises(Exception):
        with tx() as conn:
            conn.execute("UPDATE audit_log SET event='X' WHERE id=1")
