"""v2 tests: migration safety, dashboard, structured analysis, extended reconciliation,
party register, research, review workflow, providers & error handling."""
import json
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from noticemate.core.errors import PermissionDenied, ValidationError
from noticemate.services import (ai_gateway, analysis, cases, dashboard, documents, drafting, evidence, issues, notices,
                                 parties, recon_extended, research, review, taxlaw)

from .conftest import ROOT, sample


# ---------------- migration from a v1 database ----------------
def test_migration_preserves_v1_data(tmp_path, monkeypatch):
    from noticemate.core import config, migrations
    from noticemate.core.security import hash_password

    db = tmp_path / "noticemate.db"
    conn = sqlite3.connect(db)
    conn.executescript((ROOT / "tests" / "fixtures" / "schema_v1.sql").read_text())
    conn.execute("INSERT INTO schema_version(version) VALUES (1)")
    conn.execute("INSERT INTO users(username,full_name,role,password_hash,created_at) VALUES ('admin','A','ADMIN',?, '2026-01-01')",
                 (hash_password("Adm1n!Passw0rd"),))
    conn.execute("INSERT INTO cases(case_ref,assessee_name,assessee_category,created_by,created_at,updated_at) "
                 "VALUES ('OLD-1','Old Co','FIRM',1,'x','x')")
    conn.execute("INSERT INTO legal_refs(ref_key,act,provision,title,summary,status,origin) VALUES ('K','a','p','t','s','VERIFIED','USER')")
    conn.commit()
    conn.close()
    res = migrations.apply_migrations(db, tmp_path / "backups", existed_before=True)
    assert res["from"] == 1 and res["to"] == migrations.LATEST and res["backup"]
    c = sqlite3.connect(db)
    assert c.execute("SELECT username FROM users").fetchone()[0] == "admin"
    assert c.execute("SELECT case_ref FROM cases").fetchone()[0] == "OLD-1"
    assert c.execute("SELECT status, ref_type FROM legal_refs").fetchone() == ("VERIFIED", "STATUTE")
    assert c.execute("SELECT COUNT(*) FROM ai_analyses").fetchone()[0] == 0
    b = sqlite3.connect(res["backup"])
    assert b.execute("SELECT version FROM schema_version").fetchone()[0] == 1  # backup is the pre-migration state
    # idempotent
    assert migrations.apply_migrations(db, tmp_path / "backups", existed_before=True)["backup"] is None


@pytest.fixture(scope="module")
def v2(users):
    ca, staff = users["ca"], users["staff"]
    case = cases.create_case(ca, case_ref="PQR-V2", assessee_name="PQR Traders", assessee_category="FIRM", pan="AAAFP1234Z",
                             assessment_year="2026-27", party_names=["Rahul Sharma", "Neeraj Gupta", "Amit Verma"])
    cases.add_member(ca, case["id"], staff["id"])
    d = {}
    for name in ("notice_143_2_PQR.docx", "bank_statement_PQR.xlsx", "bank_book_PQR.xlsx", "cash_book_PQR.xlsx",
                 "sales_ledger_PQR.xlsx", "ais_PQR.xlsx", "debtor_ledger_PQR.xlsx"):
        d[name] = documents.upload(staff, case["id"], f"v2_{name}", sample(name))
    n = notices.create_from_document(staff, d["notice_143_2_PQR.docx"]["id"])
    iss = issues.generate_from_notice(staff, n["id"])
    return {"case": case, "docs": d, "notice": n, "issues": iss, **users}


def test_notice_completeness(v2):
    comp = v2["notice"]["completeness"]
    assert "date_of_service" in comp["missing"]
    assert "compliance_deadline" in comp["needs_verification"]
    assert v2["notice"]["particulars_json"]["notice_type"]["value"] == "Scrutiny assessment notice"


def test_dashboard_real_data(v2):
    from datetime import date

    s = dashboard.summary(v2["ca"], today=date(2026, 11, 23))
    assert s["total_cases"] >= 1 and s["active_cases"] >= 1 and s["pending_notices"] >= 1
    ours = [u for u in s["upcoming_deadlines"] if u["case_id"] == v2["case"]["id"]]
    assert ours and ours[0]["deadline"] == "2026-11-25" and ours[0]["days_left"] == 2 and not ours[0]["verified"]
    assert any("NOT VERIFIED" in a["text"] for a in s["alerts"])
    late = dashboard.summary(v2["ca"], today=date(2026, 12, 1))
    assert any(o["case_id"] == v2["case"]["id"] for o in late["overdue"])
    assert any(a["level"] == "critical" for a in late["alerts"])
    assert dashboard.summary(v2["outsider"])["total_cases"] == 0


def test_local_structured_analysis(v2):
    a = analysis.build_local(v2["staff"], v2["case"]["id"])
    c = a["content_json"]
    for k, _ in analysis.SECTIONS:
        assert k in c
    assert c["deadline"][0]["basis"] == "UNRESOLVED"
    r1 = next(r for r in c["risk_assessment"] if r["seq"] == 1)
    assert r1["level"] in ("MEDIUM", "HIGH") and r1["reasons"]
    assert all(x["basis"] in analysis.BASIS for x in c["summary"])
    with pytest.raises(PermissionDenied):
        analysis.review_decision(v2["staff"], a["id"], "ACCEPTED", "")
    e = analysis.edit(v2["staff"], a["id"], {"summary": [{"text": "Edited summary", "basis": "DOCUMENT_AVAILABLE"}]})
    assert e["version"] == a["version"] + 1 and e["content_json"]["summary"][0]["text"] == "Edited summary"
    acc = analysis.review_decision(v2["ca"], e["id"], "ACCEPTED", "ok")
    assert acc["status"] == "ACCEPTED"
    assert "NOT A PROFESSIONAL OPINION" in analysis.render_text(acc["content_json"])
    assert analysis.render_docx(acc["content_json"])[:2] == b"PK"


def test_ai_structured_analysis_roundtrip(v2):
    from noticemate.core.config import get_settings

    sub = analysis.prepare_ai(v2["staff"], v2["case"]["id"])
    payload = json.dumps(sub["exact_payload_preview"])
    assert sub["status"] == "PENDING_APPROVAL" and "AAAFP1234Z" not in payload and "Amit Verma" not in payload
    canned = {k: [{"text": f"AI {k}", "basis": "ASSUMPTION"}] for k, _ in analysis.SECTIONS}
    canned["summary"] = [{"text": "Summary", "basis": "WRONG_TAG"}]
    s = get_settings()
    s.offline_echo_response = "Here you go:\n```json\n" + json.dumps(canned) + "\n```"
    try:
        sent = ai_gateway.approve_and_send(v2["staff"], sub["id"], sub["payload_hash"], confirm=True)
    finally:
        s.offline_echo_response = None
    a = analysis.ingest_ai(v2["staff"], sent["id"])
    assert a["source"] == "AI" and a["content_json"]["summary"][0]["basis"] == "UNRESOLVED"  # bad tag downgraded
    assert a["content_json"]["evidence_gaps"][0]["text"] == "AI evidence_gaps"
    rej = analysis.review_decision(v2["ca"], a["id"], "REJECTED", "Too generic")
    assert rej["status"] == "REJECTED"


def test_extended_reconciliations(v2):
    st, d, cid = v2["staff"], v2["docs"], v2["case"]["id"]
    sb = recon_extended.run_sales_vs_bank(st, cid, d["sales_ledger_PQR.xlsx"]["id"], d["bank_statement_PQR.xlsx"]["id"],
                                          date_window_days=0, filter_sales="customer")
    assert sb["matched_count"] == 2           # P and R match exactly; Q is 1.5L vs 2L
    assert any(u["amount"] == 150000 for u in sb["unmatched_in_sales"])
    assert sb["status"] == "UNRECONCILED" and "does not prove" in sb["interpretation"]
    bb = recon_extended.run_match(st, cid, doc_a=d["bank_statement_PQR.xlsx"]["id"], doc_b=d["bank_book_PQR.xlsx"]["id"],
                                  perspective_a="bank_statement", perspective_b="books", label_a="statement", label_b="book")
    assert bb["duplicate_total"] == 200000 and bb["difference_after_duplicates"] == 0
    ais = recon_extended.run_ais_vs_books(st, cid, d["ais_PQR.xlsx"]["id"], d["sales_ledger_PQR.xlsx"]["id"])
    q = next(r for r in ais["rows"] if "Customer Q" in r["party"])
    assert q["ais_amount"] == 200000 and q["books_amount"] == 150000 and q["difference"] == 50000
    p = next(r for r in ais["rows"] if "Customer P" in r["party"])
    assert p["status"] == "MATCHED"         # 'Pvt Ltd' normalised
    dr = recon_extended.run_debtors_vs_receipts(st, cid, d["debtor_ledger_PQR.xlsx"]["id"], d["cash_book_PQR.xlsx"]["id"])
    w = next(c for c in dr["customers"] if c["customer"] == "Customer W")
    assert w["status"] == "REVIEW" and any("exceed" in f for f in w["flags"])
    x = next(c for c in dr["customers"] if c["customer"] == "Customer X")
    assert x["receipts_per_cash_bank"] == 120000


def test_party_register(v2):
    st, cid = v2["staff"], v2["case"]["id"]
    r = parties.upsert(st, cid, record_type="LENDER", party_name="Amit Verma", amount=150000, txn_date="2025-12-20", mode="BANK",
                       evidence={"confirmation": "AVAILABLE", "pan": "AVAILABLE", "itr": "AVAILABLE", "lender_bank_statement": "AVAILABLE",
                                 "lender_cash_deposit_before": {"amount": 140000, "date": "2025-12-19", "explained": False}})
    an = r["analysis"]
    assert an["aspects"]["identity"]["status"] == "SUPPORTED_BY_DOCUMENTS"
    assert an["aspects"]["source_of_source"]["status"] == "PARTLY_SUPPORTED"
    assert any("1 day(s) before" in f and "NOT explained" in f for f in an["flags"])
    assert "Loan agreement / terms" in an["evidence_gaps"]
    p = parties.upsert(st, cid, record_type="PARTNER_CAPITAL", party_name="Rahul Sharma", amount=150000, txn_date="2025-06-10", mode="CASH")
    assert any("269SS" in f for f in p["analysis"]["flags"])
    with pytest.raises(ValidationError):
        parties.upsert(st, cid, record_type="LENDER", party_name="X", amount=1, evidence={"bogus": "AVAILABLE"})
    assert parties.summary(st, cid)["totals"]["LENDER"]["amount"] == 150000


def test_research_workflow(v2):
    from noticemate.core.config import get_settings

    st, ca, cid = v2["staff"], v2["ca"], v2["case"]["id"]
    note = research.create(st, cid, "Is the cash deposit explanation sufficient and which Act applies?", v2["issues"][0]["id"])
    c = note["content_json"]
    assert any(s["ref_key"] == "IT1961_S68" for s in c["statutory"])
    assert c["applicable_law"]["substantive_law"] == "Income-tax Act, 1961"
    assert "LIVE LEGAL RESEARCH NOT USED" in c["disclosures"][0] and c["judicial"] == []
    sub = research.prepare_ai(st, note["id"], live=True)
    assert "warning" in sub  # live search not enabled
    s = get_settings()
    s.offline_echo_response = json.dumps({"statutory": [{"proposition": "Credits need explanation", "act": "Income-tax Act, 1961",
                                                         "provision": "Section 68", "effective_from": "UNKNOWN", "source_url": "NONE"}],
                                          "judicial": [{"proposition": "x", "case_name": "Some Case", "citation": "UNKNOWN"}],
                                          "practical": [{"suggestion": "Get confirmations"}], "caveats": ["may be outdated"]})
    try:
        sent = ai_gateway.approve_and_send(st, sub["id"], sub["payload_hash"], confirm=True)
    finally:
        s.offline_echo_response = None
    n2 = research.ingest_ai(st, sent["id"])
    props = n2["content_json"]["ai_propositions"]
    assert len(props) == 3 and all(p["status"] == "UNVERIFIED" for p in props)
    with pytest.raises(ValidationError):
        research.set_proposition_status(ca, n2["id"], 0, "VERIFIED")  # no source
    n3 = research.set_proposition_status(ca, n2["id"], 0, "VERIFIED", "https://incometaxindia.gov.in")
    assert n3["status"] == "PARTLY_VERIFIED"
    ref = research.promote_to_registry(st, n2["id"], 1, "CASE_SOME_CASE")
    assert ref["status"] == "REQUIRES_VERIFICATION" and ref["ref_type"] == "JUDGMENT"
    assert "REQUIRES CA VERIFICATION" in taxlaw.render_ref("CASE_SOME_CASE")


def test_review_workflow_comments_reject_pdf(v2):
    st, ca, cid, n = v2["staff"], v2["ca"], v2["case"]["id"], v2["notice"]
    for i in v2["issues"]:
        issues.update_analysis(ca, i["id"], {"concern_position": "NEED_CLIENT_INFO"})
        issues.set_strategy(st, i["id"], "DISPUTE_FACTUAL", "Respond factually; subject to CA review.")
    issues.update_analysis(st, v2["issues"][0]["id"], {"client_explanation": "Deposits are out of recorded cash sales and collections."})
    d1 = drafting.build(st, cid, n["id"])
    blk = d1["content_json"]["issues"][0]
    assert any("[TO BE CONFIRMED BY CLIENT:" in p for p in blk["paragraphs"])
    assert any(b["basis"] == "AWAITING_CLIENT_CONFIRMATION" for b in blk["basis_map"])
    assert "filed" not in d1["content_json"]["background"].lower()  # no presumed filing history
    review.add_comment(ca, d1["id"], "Q1", "Please attach the cash book.")
    st1 = review.reject(ca, d1["id"], "Explanations not yet confirmed by client.", "CHANGES_REQUESTED")
    assert not st1["approved"] and "changes requested" in st1["reason"].lower()
    with pytest.raises(PermissionDenied):
        review.reject(st, d1["id"], "nope nope")
    # resolve, fix and approve
    edits = {"background": "Partnership firm engaged in trading (fictional).",
             "issues": {str(b["issue_id"]): ["Response settled by CA (fictional)."] for b in d1["content_json"]["issues"]},
             "to_from": {"to": "National Faceless Assessment Centre"},
             "reference": "DIN ITBA/AST/S/143(2)/2026-27/1000000001(1) dated 10-11-2026",
             "subject": "Submission u/s 143(2) for AY 2026-27 – ₹ amounts as per records",
             "signature": {"name": "Partner", "designation": "Partner", "date": "24-11-2026", "place": "Test City"}}
    d2 = drafting.edit(v2["admin"], d1["id"], edits)
    for k, _ in review.CHECKLIST:
        review.tick(ca, d2["id"], k, True)
    notices.verify_deadline(ca, n["id"], "2026-11-25", "portal (fictional)")
    with pytest.raises(ValidationError) as e:
        review.approve(ca, d2["id"], declaration_accepted=True)
    assert "open reviewer comments" in e.value.message
    cm = review.list_comments(ca, cid)[0]
    review.resolve_comment(st, cm["id"], "Cash book attached as annexure.")
    assert review.approve(ca, d2["id"], declaration_accepted=True)["approved"]
    name, pdf = review.export(ca, cid, "pdf")
    assert name.endswith(".pdf") and pdf[:4] == b"%PDF"
    name2, dx = review.export(ca, cid, "docx")
    assert dx[:2] == b"PK"
    h = review.history(ca, cid)
    assert h["versions"][0]["latest_decision"] == "APPROVED" and h["versions"][1]["latest_decision"] == "CHANGES_REQUESTED"
    df = drafting.diff_versions(ca, d1["id"], d2["id"])
    assert df["changed"] and df["added"] > 0
    memo = review.review_memo(ca, cid)
    assert "APPROVED — version" in memo and "Cash book attached" in memo
    assert isinstance(drafting.annexure_index(ca, cid), list)


# ---------------- providers ----------------
class _H(BaseHTTPRequestHandler):
    code, body, headers_extra = 200, b"{}", {}

    def do_POST(self):
        self.rfile.read(int(self.headers.get("content-length", 0)))
        self.send_response(self.code)
        for k, v in self.headers_extra.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *a):
        pass


def _server(code, body, headers=None):
    h = type("H", (_H,), {"code": code, "body": body, "headers_extra": headers or {}})
    srv = HTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_provider_error_mapping_and_gemini(monkeypatch):
    import urllib.request

    from noticemate.core.config import get_settings
    from noticemate.services import ai_providers as P

    # route plain http for the local test server (production uses https with default SSL context)
    real_urlopen = urllib.request.urlopen
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None, context=None: real_urlopen(req, timeout=timeout))
    s = get_settings()
    monkeypatch.setattr(s, "gemini_api_key", "test-key-not-real")
    monkeypatch.setattr(s, "anthropic_api_key", "test-key-not-real")
    srv = _server(429, b'{"error":{"message":"slow down"}}', {"retry-after": "30"})
    monkeypatch.setattr(s, "anthropic_base_url", f"http://127.0.0.1:{srv.server_port}")
    with pytest.raises(Exception) as e:
        P.AnthropicProvider().send({"model": "m", "messages": [{"role": "user", "content": "x"}]})
    assert e.value.kind == "RATE_LIMIT" and "30" in e.value.message
    srv.shutdown()
    srv = _server(401, b'{"error":{"message":"invalid x-api-key"}}')
    monkeypatch.setattr(s, "anthropic_base_url", f"http://127.0.0.1:{srv.server_port}")
    with pytest.raises(Exception) as e:
        P.AnthropicProvider().send({"model": "m", "messages": []})
    assert e.value.kind == "AUTH" and "Claude Pro" in e.value.message
    srv.shutdown()
    ok = json.dumps({"candidates": [{"content": {"parts": [{"text": "OK"}]},
                                     "groundingMetadata": {"groundingChunks": [{"web": {"uri": "https://example.gov.in/x", "title": "X"}}]}}],
                     "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 1}}).encode()
    srv = _server(200, ok)
    monkeypatch.setattr(s, "gemini_base_url", f"http://127.0.0.1:{srv.server_port}")
    g = P.GeminiProvider()
    body = g.build_body("sys", "hello", web_search=False)
    assert "tools" not in body and body["contents"][0]["parts"][0]["text"] == "hello"
    res = g.send(body)
    assert res.text == "OK" and res.citations[0]["url"] == "https://example.gov.in/x" and res.input_tokens == 3
    srv.shutdown()
    assert "sys" in P.outgoing_text(body) and "hello" in P.outgoing_text(body)


def test_status_and_connection_test_gating(users, monkeypatch):
    from noticemate.core.config import get_settings

    st = ai_gateway.status()
    assert "anthropic" in st["providers"] and "gemini" in st["providers"] and "does NOT include" in st["disclosure"]
    s = get_settings()
    monkeypatch.setattr(s, "ai_enabled", False)
    with pytest.raises(PermissionDenied):
        ai_gateway.test_connection(users["ca"], "gemini")
    r = ai_gateway.test_connection(users["ca"], "offline-echo")
    assert r["ok"]
